"""
/broadcast - Admin broadcast messaging.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select, func

from models import User, UserStatus
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard
from core.events import dispatcher, Event, EventType

router = Router()
logger = logging.getLogger(__name__)


class BroadcastStates(StatesGroup):
    WAITING_MESSAGE = State()
    CONFIRMING = State()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext, **kwargs):
    """Start broadcast process."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    await state.set_state(BroadcastStates.WAITING_MESSAGE)

    text = (
        "📡 <b>Broadcast Message</b>\n\n"
        "Send me the message you want to broadcast to all users.\n"
        "Supports HTML formatting.\n\n"
        "Send /cancel to abort."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("cancel"), BroadcastStates.WAITING_MESSAGE)
async def cmd_cancel_broadcast(message: Message, state: FSMContext, **kwargs):
    """Cancel broadcast."""
    await state.clear()
    await message.answer("❌ Broadcast cancelled.")


@router.message(BroadcastStates.WAITING_MESSAGE)
async def msg_broadcast_content(message: Message, state: FSMContext, **kwargs):
    """Receive broadcast message content."""
    text = message.text or message.caption or ""

    if not text or len(text.strip()) == 0:
        await message.answer("⚠️ Please send a non-empty message.")
        return

    await state.update_data(broadcast_text=text)
    await state.set_state(BroadcastStates.CONFIRMING)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Send Broadcast", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="broadcast_cancel")],
    ])

    await message.answer(
        f"📡 <b>Broadcast Preview:</b>\n\n{text}\n\n"
        f"Confirm to send to all users?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "broadcast_confirm")
async def cb_broadcast_confirm(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Execute the broadcast."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    state_data = await state.get_data()
    broadcast_text = state_data.get("broadcast_text", "")

    session_factory = kwargs.get("session")
    bot = callback.bot

    async with session_factory() as session:
        result = await session.execute(
            select(User.telegram_id).where(User.status == UserStatus.ACTIVE)
        )
        user_ids = [row[0] for row in result.fetchall()]

    if not user_ids:
        await callback.message.edit_text("📡 No active users to broadcast to.")
        await callback.answer()
        await state.clear()
        return

    success_count = 0
    fail_count = 0

    await callback.message.edit_text(
        f"📡 <b>Broadcasting to {len(user_ids)} users...</b>",
        parse_mode="HTML",
    )

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, broadcast_text, parse_mode="HTML")
            success_count += 1
        except Exception:
            fail_count += 1

    await callback.message.edit_text(
        f"📡 <b>Broadcast Complete!</b>\n\n"
        f"✅ Sent: {success_count}\n"
        f"❌ Failed: {fail_count}\n"
        f"📊 Total: {len(user_ids)}",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )

    await dispatcher.emit(Event(
        type=EventType.BROADCAST_SENT,
        data={
            "bot": bot,
            "sent": success_count,
            "failed": fail_count,
            "total": len(user_ids),
        }
    ))

    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "broadcast_cancel")
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Cancel broadcast."""
    await state.clear()
    await callback.message.edit_text("❌ Broadcast cancelled.", reply_markup=admin_main_keyboard())
    await callback.answer()
