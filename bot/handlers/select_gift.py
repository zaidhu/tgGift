"""
Gift selection handler.
Handles browsing, selecting, and confirming a gift.
Applies admin-set pricing adjustments (fees/discounts) to displayed prices.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from services import GiftCatalogService, PricingService
from bot.keyboards.gift_selection import gift_catalog_keyboard, gift_preview_keyboard
from bot.keyboards.pricing import pricing_adjustment_keyboard

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

    # Filter hidden gifts and apply pricing
    session_factory = kwargs.get("session")
    if session_factory:
        async with session_factory() as session:
            from admin.gifts import filter_hidden_gifts
            gifts = await filter_hidden_gifts(session, gifts)
            pricing = PricingService(session)
            gifts = await pricing.apply_to_gifts_list(gifts)

    keyboard = gift_catalog_keyboard(gifts, page=page)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "gift_catalog")
async def cb_gift_catalog(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Show gift catalog."""
    bot = callback.bot
    catalog = GiftCatalogService(bot)
    gifts = await catalog.get_gifts()

    session_factory = kwargs.get("session")
    if session_factory:
        async with session_factory() as session:
            from admin.gifts import filter_hidden_gifts
            gifts = await filter_hidden_gifts(session, gifts)
            pricing = PricingService(session)
            gifts = await pricing.apply_to_gifts_list(gifts)

    keyboard = gift_catalog_keyboard(gifts, page=0)
    await callback.message.edit_text(
        "🎁 <b>Choose a Gift</b>\n\nSelect a gift you'd like to send:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
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

    # Apply pricing adjustment
    original_stars = gift["stars"]
    adjustment = gift.get("adjustment", 0)
    final_stars = gift.get("stars", original_stars)  # Already updated if adjustment applied

    # Store selection with final price
    gift_to_store = {**gift}
    gift_to_store["final_stars"] = final_stars
    gift_to_store["original_stars"] = original_stars
    gift_to_store["adjustment"] = adjustment

    await state.update_data(selected_gift=gift_to_store)
    await state.set_state(GiftSelectStates.SELECTING)

    # Build price display
    price_line = f"💰 <b>Price:</b> {final_stars} ⭐"
    if adjustment != 0:
        adj_label = f"+{adjustment} ⭐ fee" if adjustment > 0 else f"{adjustment} ⭐ discount"
        price_line += f"\n<i>Official price: {original_stars} ⭐ ({adj_label})</i>"

    text = (
        f"🎁 <b>{gift['name']}</b>\n\n"
        f"{gift.get('icon', '🎁')} {gift.get('description', '')}\n\n"
        f"{price_line}\n\n"
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

    # Get final price
    session_factory = kwargs.get("session")
    final_stars = gift["stars"]
    if session_factory:
        async with session_factory() as session:
            pricing = PricingService(session)
            final_stars = await pricing.get_final_price(gift_id, gift["stars"])

    gift["final_stars"] = final_stars
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
