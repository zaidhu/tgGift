"""
/refunds - Admin refund management.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func

from models import Refund, RefundStatus
from services import RefundService
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard, admin_refund_actions_keyboard
from core.events import dispatcher, Event, EventType

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("refunds"))
async def cmd_refunds(message: Message, **kwargs):
    """Show refund statistics."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        pending = await session.execute(
            select(func.count(Refund.id)).where(Refund.status == RefundStatus.PENDING)
        )
        pending_count = pending.scalar() or 0

        completed = await session.execute(
            select(func.count(Refund.id)).where(Refund.status == RefundStatus.COMPLETED)
        )
        completed_count = completed.scalar() or 0

        total_amount = await session.execute(
            select(func.coalesce(func.sum(Refund.amount_stars), 0)).where(
                Refund.status == RefundStatus.COMPLETED
            )
        )
        total_refunded = total_amount.scalar() or 0

    text = (
        "💸 <b>Refund Statistics</b>\n\n"
        f"⏳ <b>Pending:</b> {pending_count}\n"
        f"✅ <b>Completed:</b> {completed_count}\n"
        f"💰 <b>Total Refunded:</b> {total_refunded} ⭐\n\n"
    )

    if pending_count > 0:
        text += f"🔔 <b>{pending_count} refund(s) need attention!</b>"
    else:
        text += "✅ <b>No pending refunds.</b>"

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_refunds")
async def cb_admin_refunds(callback: CallbackQuery, **kwargs):
    """Admin panel - refunds view with pending actions."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        pending = await session.execute(
            select(Refund).where(Refund.status == RefundStatus.PENDING)
            .order_by(Refund.created_at.desc()).limit(10)
        )
        pending_refunds = pending.scalars().all()

    text = "💸 <b>Pending Refunds</b>\n\n"

    if not pending_refunds:
        text += "✅ No pending refunds."
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
        await callback.answer()
        return

    for refund in pending_refunds:
        text += (
            f"📋 <b>#{refund.id}</b>\n"
            f"   Order: #{refund.order_id}\n"
            f"   Amount: {refund.amount_stars} ⭐\n"
            f"   Reason: {refund.reason or 'Auto'}\n"
            f"   Date: {refund.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = [InlineKeyboardButton(
            text=f"Action: #{refund.id}",
            callback_data=f"admin_refund_action:{refund.id}"
        )]
        if refund == pending_refunds[-1]:
            buttons.append(InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel"))
        # We'll use edit_text with last refund's actions

    if pending_refunds:
        keyboard = admin_refund_actions_keyboard(pending_refunds[0].id)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_refund_approve:"))
async def cb_refund_approve(callback: CallbackQuery, **kwargs):
    """Approve a refund."""
    refund_id = int(callback.data.split(":")[1])
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        refund_service = RefundService(session)
        refund = await refund_service.approve_refund(refund_id, callback.from_user.id)
        await session.commit()

        await dispatcher.emit(Event(
            type=EventType.REFUND_COMPLETED,
            data={
                "bot": callback.bot,
                "telegram_id": refund.telegram_id,
                "refund_id": refund_id,
                "refund_status": "approved",
                "amount_stars": refund.amount_stars,
            }
        ))

    await callback.message.edit_text(
        f"✅ <b>Refund #{refund_id} Approved & Completed</b>\n"
        f"Amount: {refund.amount_stars} ⭐",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_refund_reject:"))
async def cb_refund_reject(callback: CallbackQuery, **kwargs):
    """Reject a refund."""
    refund_id = int(callback.data.split(":")[1])
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        refund_service = RefundService(session)
        refund = await refund_service.reject_refund(
            refund_id, callback.from_user.id, "Rejected by admin"
        )
        await session.commit()

    await callback.message.edit_text(
        f"❌ <b>Refund #{refund_id} Rejected</b>",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()
