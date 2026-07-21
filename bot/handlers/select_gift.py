"""
Gift selection handler.
Handles browsing, selecting, and confirming a gift.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services import GiftCatalogService
from bot.keyboards.gift_selection import gift_catalog_keyboard, gift_preview_keyboard

router = Router()
logger = logging.getLogger(__name__)


class GiftSelectStates(StatesGroup):
    SELECTING = State()
    CONFIRMED = State()


@router.callback_query(F.data.startswith("gift_page:"))
async def cb_gift_page(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Handle gift catalog pagination."""
    page = int(callback.data.split(":")[1])
    bot = callback.bot
    catalog = GiftCatalogService(bot)
    gifts = await catalog.get_gifts()

    keyboard = gift_catalog_keyboard(gifts, page=page)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("gift_select:"))
async def cb_gift_select(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Handle gift selection - show preview."""
    gift_id = int(callback.data.split(":")[1])
    bot = callback.bot
    catalog = GiftCatalogService(bot)
    gift = await catalog.get_gift_by_id(gift_id)

    if not gift:
        await callback.answer("Gift not found.", show_alert=True)
        return

    # Store selection in state
    await state.update_data(selected_gift=gift)
    await state.set_state(GiftSelectStates.SELECTING)

    text = (
        f"🎁 <b>{gift['name']}</b>\n\n"
        f"{gift.get('icon', '🎁')} {gift.get('description', '')}\n\n"
        f"💰 <b>Price:</b> {gift['stars']} ⭐\n\n"
        "Would you like to send this gift?"
    )

    keyboard = gift_preview_keyboard(gift)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("gift_confirm:"))
async def cb_gift_confirm(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Handle gift confirmation - move to custom message."""
    gift_id = int(callback.data.split(":")[1])
    bot = callback.bot
    catalog = GiftCatalogService(bot)
    gift = await catalog.get_gift_by_id(gift_id)

    if not gift:
        await callback.answer("Gift not found.", show_alert=True)
        return

    await state.update_data(selected_gift=gift)
    await state.set_state(GiftSelectStates.CONFIRMED)

    from bot.keyboards.gift_selection import message_type_keyboard

    text = (
        f"✅ <b>{gift['name']}</b> selected!\n\n"
        "Would you like to add a custom message?\n"
        "The message will be attached to the gift."
    )
    keyboard = message_type_keyboard()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
