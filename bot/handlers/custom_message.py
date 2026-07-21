"""
Custom message handler.
Allows users to add a personal message to their gift.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.keyboards.gift_selection import recipient_method_keyboard

router = Router()
logger = logging.getLogger(__name__)


class CustomMessageStates(StatesGroup):
    WAITING_MESSAGE = State()


@router.callback_query(F.data == "msg_custom")
async def cb_msg_custom(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Ask user to write a custom message."""
    await state.set_state(CustomMessageStates.WAITING_MESSAGE)

    text = (
        "📝 <b>Write Your Message</b>\n\n"
        "Send me the message you'd like to attach to the gift.\n"
        "You can use basic formatting:\n\n"
        "• <b>bold</b> — use *text*\n"
        "• <i>italic</i> — use _text_\n"
        "• <code>code</code> — use `text`\n\n"
        "Or just send plain text!"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.message(CustomMessageStates.WAITING_MESSAGE)
async def msg_received(message: Message, state: FSMContext, **kwargs):
    """Receive and store the custom message."""
    text = message.text or message.caption or ""

    if not text or len(text.strip()) == 0:
        await message.answer("⚠️ Please send a non-empty message.")
        return

    if len(text) > 1000:
        await message.answer("⚠️ Message too long. Maximum 1000 characters.")
        return

    await state.update_data(custom_message=text)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Looks Good", callback_data="msg_confirm")],
        [InlineKeyboardButton(text="✏️ Change Message", callback_data="msg_custom")],
    ])

    await message.answer(
        f"📝 <b>Your Message:</b>\n\n{text}\n\n"
        "Is this message okay?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "msg_confirm")
async def cb_msg_confirm(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Confirm custom message - move to recipient selection."""
    keyboard = recipient_method_keyboard()
    await callback.message.edit_text(
        "📝 Message saved!\n\n<b>How would you like to send this gift?</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "msg_skip")
async def cb_msg_skip(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Skip custom message - move to recipient selection."""
    await state.update_data(custom_message=None)
    keyboard = recipient_method_keyboard()
    await callback.message.edit_text(
        "⏭️ No custom message.\n\n<b>How would you like to send this gift?</b>",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()
