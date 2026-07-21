"""
Recipient selection handler.
Supports 4 methods: Gift Link, User ID, Forward message, Contact share.
"""

import logging
import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.keyboards.gift_selection import gift_link_sent_keyboard

router = Router()
logger = logging.getLogger(__name__)


class RecipientStates(StatesGroup):
    WAITING_ID = State()
    WAITING_FORWARD = State()
    WAITING_CONTACT = State()


# ─── Gift Link Method (Recommended) ─────────────────────────────────────────


@router.callback_query(F.data == "recipient_link")
async def cb_recipient_link(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Handle gift link method - show preview first, then generate link on confirm."""
    state_data = await state.get_data()
    gift = state_data.get("selected_gift", {})
    custom_message = state_data.get("custom_message")

    if not gift:
        await callback.answer("No gift selected. Please start over.", show_alert=True)
        return

    # Show preview
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    preview_text = (
        f"🎁 <b>Gift Link Preview</b>\n\n"
        f"Here's what your recipient will see:\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 <b>{gift.get('name', 'Gift')}</b>\n"
        f"{gift.get('icon', '🎁')} {gift.get('description', '')}\n\n"
        f"💰 <b>Price:</b> {gift.get('final_stars') or gift.get('stars', '?')} ⭐\n"
    )

    if custom_message:
        preview_text += f"\n📝 <b>Your Message:</b>\n<i>{custom_message}</i>\n"
    else:
        preview_text += "\n📝 <b>Message:</b> <i>No custom message</i>\n"

    preview_text += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"When they open the link, the gift will be delivered\n"
        f"automatically after payment verification.\n\n"
        f"⏰ Link expires in <b>72 hours</b>."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Generate Link", callback_data="recipient_link_confirm")],
        [InlineKeyboardButton(text="🔄 Change Method", callback_data="recipient_method")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])

    await callback.message.edit_text(preview_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "recipient_method")
async def cb_recipient_method(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Go back to recipient method selection."""
    from bot.keyboards.gift_selection import recipient_method_keyboard

    text = (
        "👤 <b>How would you like to send this gift?</b>\n\n"
        "Choose a method to identify the recipient:"
    )
    keyboard = recipient_method_keyboard()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "recipient_link_confirm")
async def cb_recipient_link_confirm(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Confirm and generate the actual gift link."""
    from services import GiftLinkService
    from models import Order, OrderStatus, RecipientMethod

    session_factory = kwargs.get("session")
    user = kwargs.get("user")
    bot = callback.bot

    state_data = await state.get_data()
    gift = state_data.get("selected_gift", {})
    custom_message = state_data.get("custom_message")

    if not gift:
        await callback.answer("No gift selected. Please start over.", show_alert=True)
        return

    async with session_factory() as session:
        # Create order
        order = Order(
            telegram_id=callback.from_user.id,
            buyer_id=user.id,
            status=OrderStatus.PENDING,
            gift_id=gift.get("id"),
            gift_name=gift.get("name"),
            gift_stars_price=gift.get("final_stars") or gift.get("stars"),
            recipient_method=RecipientMethod.GIFT_LINK,
            custom_message=custom_message,
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        # Create gift link
        link_service = GiftLinkService(session)
        gift_link = await link_service.create_gift_link(
            order_id=order.id,
            buyer_telegram_id=callback.from_user.id,
        )

        link_url = link_service.generate_link_url(gift_link.token)

        # Store order data
        await state.update_data(order_id=order.id, gift_link_token=gift_link.token)

        text = (
            f"🔗 <b>Gift Link Generated!</b>\n\n"
            f"Share this link with your recipient:\n\n"
            f"{link_url}\n\n"
            f"🎁 <b>Gift:</b> {gift['name']}\n"
            f"💰 <b>Price:</b> {gift.get('final_stars') or gift.get('stars')} ⭐\n\n"
            f"When they open the link, they'll receive the gift "
            f"automatically after payment verification.\n\n"
            f"<b>⚠️ Note:</b> You'll still need to complete payment "
            f"before the gift is delivered."
        )

        keyboard = gift_link_sent_keyboard(link_url)
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()


# ─── User ID Method ──────────────────────────────────────────────────────────


@router.callback_query(F.data == "recipient_id")
async def cb_recipient_id(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Ask for recipient's Telegram User ID."""
    await state.set_state(RecipientStates.WAITING_ID)

    text = (
        "🆔 <b>Enter Recipient's Telegram ID</b>\n\n"
        "Send me the recipient's Telegram User ID.\n\n"
        "💡 <i>Tip: You can find a user's ID by forwarding "
        "their message to @userinfobot</i>"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.message(RecipientStates.WAITING_ID)
async def msg_recipient_id(message: Message, state: FSMContext, **kwargs):
    """Validate and store recipient Telegram ID."""
    from services import TelegramAPIService

    text = (message.text or "").strip()

    # Validate it's a number
    if not text.isdigit():
        await message.answer("⚠️ Please enter a valid Telegram User ID (numbers only).")
        return

    recipient_id = int(text)

    # Verify user exists
    api = TelegramAPIService(message.bot)
    exists = await api.verify_user_exists(recipient_id)

    if not exists:
        await message.answer(
            "⚠️ This Telegram ID doesn't seem to exist or the user has blocked the bot.\n"
            "Please check the ID and try again."
        )
        return

    await state.update_data(recipient_telegram_id=recipient_id)
    await _proceed_to_review(message, state, message.bot, recipient_id, kwargs)


# ─── Forward Method ──────────────────────────────────────────────────────────


@router.callback_query(F.data == "recipient_forward")
async def cb_recipient_forward(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Ask user to forward a message from the recipient."""
    await state.set_state(RecipientStates.WAITING_FORWARD)

    text = (
        "📨 <b>Forward a Message</b>\n\n"
        "Forward any message from the person you want to send the gift to.\n\n"
        "💡 <i>The bot will automatically detect their User ID "
        "from the forwarded message.</i>"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.message(RecipientStates.WAITING_FORWARD, F.forward_from)
async def msg_forwarded(message: Message, state: FSMContext, **kwargs):
    """Process forwarded message to extract recipient info."""
    from services import TelegramAPIService
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    forwarded_user = message.forward_from
    if not forwarded_user:
        await message.answer("⚠️ Could not detect the sender of this message.")
        return

    recipient_id = forwarded_user.id
    username = forwarded_user.username or "Unknown"
    first_name = forwarded_user.first_name or ""

    await state.update_data(recipient_telegram_id=recipient_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Correct", callback_data="recipient_confirmed")],
        [InlineKeyboardButton(text="🔄 Try Again", callback_data="recipient_forward")],
    ])

    await message.answer(
        f"📨 <b>Recipient Detected:</b>\n\n"
        f"Name: {first_name}\n"
        f"Username: @{username}\n"
        f"ID: {recipient_id}\n\n"
        f"Is this the correct person?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─── Contact Share Method ────────────────────────────────────────────────────


@router.callback_query(F.data == "recipient_contact")
async def cb_recipient_contact(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Ask user to share a contact."""
    await state.set_state(RecipientStates.WAITING_CONTACT)

    text = (
        "👤 <b>Share Contact</b>\n\n"
        "Use the 📎 attachment button and select <b>Share Contact</b> "
        "to share the recipient's contact.\n\n"
        "The bot will extract their Telegram ID automatically."
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.message(RecipientStates.WAITING_CONTACT, F.contact)
async def msg_contact(message: Message, state: FSMContext, **kwargs):
    """Process shared contact."""
    contact = message.contact
    if not contact:
        await message.answer("⚠️ Could not process this contact.")
        return

    recipient_id = contact.user_id
    first_name = contact.first_name or ""
    last_name = contact.last_name or ""

    await state.update_data(recipient_telegram_id=recipient_id)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Correct", callback_data="recipient_confirmed")],
        [InlineKeyboardButton(text="🔄 Try Again", callback_data="recipient_contact")],
    ])

    await message.answer(
        f"👤 <b>Recipient:</b>\n\n"
        f"Name: {first_name} {last_name}\n"
        f"ID: {recipient_id}\n\n"
        f"Is this the correct person?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─── Confirmation ────────────────────────────────────────────────────────────


@router.callback_query(F.data == "recipient_confirmed")
async def cb_recipient_confirmed(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Recipient confirmed - proceed to order review."""
    session_factory = kwargs.get("session")
    user = kwargs.get("user")
    state_data = await state.get_data()

    from models import Order, OrderStatus, RecipientMethod

    async with session_factory() as session:
        order = Order(
            telegram_id=callback.from_user.id,
            buyer_id=user.id,
            status=OrderStatus.PENDING,
            gift_id=state_data.get("selected_gift", {}).get("id"),
            gift_name=state_data.get("selected_gift", {}).get("name"),
            gift_stars_price=state_data.get("selected_gift", {}).get("final_stars") or state_data.get("selected_gift", {}).get("stars"),
            recipient_method=RecipientMethod.USER_ID,
            recipient_telegram_id=state_data.get("recipient_telegram_id"),
            custom_message=state_data.get("custom_message"),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        await state.update_data(order_id=order.id)
        await _show_order_review(callback, state, order)


async def _proceed_to_review(message_or_callback, state, bot, recipient_id, kwargs):
    """Common logic to create order and show review."""
    session_factory = kwargs.get("session")
    user = kwargs.get("user")
    state_data = await state.get_data()

    from models import Order, OrderStatus, RecipientMethod

    async with session_factory() as session:
        order = Order(
            telegram_id=message_or_callback.from_user.id,
            buyer_id=user.id,
            status=OrderStatus.PENDING,
            gift_id=state_data.get("selected_gift", {}).get("id"),
            gift_name=state_data.get("selected_gift", {}).get("name"),
            gift_stars_price=state_data.get("selected_gift", {}).get("final_stars") or state_data.get("selected_gift", {}).get("stars"),
            recipient_method=RecipientMethod.USER_ID,
            recipient_telegram_id=recipient_id,
            custom_message=state_data.get("custom_message"),
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

        await state.update_data(order_id=order.id)

        await _show_order_review(message_or_callback, state, order)


async def _show_order_review(message_or_callback, state, order):
    """Show order review before payment."""
    from bot.keyboards.gift_selection import order_review_keyboard

    state_data = await state.get_data()
    recipient = state_data.get("recipient_telegram_id", "Unknown")
    custom_msg = state_data.get("custom_message", "None")

    text = (
        f"📋 <b>Order Review</b>\n\n"
        f"🎁 <b>Gift:</b> {order.gift_name}\n"
        f"💰 <b>Price:</b> {order.gift_stars_price} ⭐\n"
        f"👤 <b>Recipient ID:</b> {recipient}\n"
        f"📝 <b>Message:</b> {custom_msg if custom_msg else 'None'}\n\n"
        f"<i>Please review your order before paying.</i>"
    )

    keyboard = order_review_keyboard(order.id)
    
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=keyboard)
