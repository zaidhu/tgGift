"""
/payments - Admin payment logs.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func

from models import Payment, PaymentStatus
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("payments"))
async def cmd_payments(message: Message, **kwargs):
    """Show recent payments."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        total_result = await session.execute(
            select(func.coalesce(func.sum(Payment.amount_stars), 0)).where(
                Payment.status == PaymentStatus.SUCCESSFUL
            )
        )
        total_revenue = total_result.scalar() or 0

        total_count = await session.execute(
            select(func.count(Payment.id)).where(
                Payment.status == PaymentStatus.SUCCESSFUL
            )
        )
        total_payments = total_count.scalar() or 0

        pending = await session.execute(
            select(func.count(Payment.id)).where(
                Payment.status == PaymentStatus.PENDING
            )
        )
        pending_count = pending.scalar() or 0

    text = (
        "💰 <b>Payment Statistics</b>\n\n"
        f"📊 <b>Total Payments:</b> {total_payments}\n"
        f"💰 <b>Total Revenue:</b> {total_revenue} ⭐\n"
        f"⏳ <b>Pending:</b> {pending_count}\n"
    )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_payments")
async def cb_admin_payments(callback: CallbackQuery, **kwargs):
    """Admin panel - payments view."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        total_result = await session.execute(
            select(func.coalesce(func.sum(Payment.amount_stars), 0)).where(
                Payment.status == PaymentStatus.SUCCESSFUL
            )
        )
        total_revenue = total_result.scalar() or 0

        total_count = await session.execute(
            select(func.count(Payment.id)).where(
                Payment.status == PaymentStatus.SUCCESSFUL
            )
        )
        total_payments = total_count.scalar() or 0

    text = (
        "💰 <b>Payment Logs</b>\n\n"
        f"📊 <b>Total Payments:</b> {total_payments}\n"
        f"💰 <b>Total Revenue:</b> {total_revenue} ⭐\n\n"
        f"Use /payments for detailed logs."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
    await callback.answer()
