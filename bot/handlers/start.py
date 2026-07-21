"""
/start handler and gift browsing entry point.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext

from services import GiftCatalogService
from bot.keyboards.gift_selection import gift_catalog_keyboard
from core.events import dispatcher, Event, EventType

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, command: CommandObject, **kwargs):
    """Handle /start command."""
    user = kwargs.get("user")
    bot = message.bot

    # Emit user registered event (only for new users)
    if user and user.created_at == user.updated_at:
        await dispatcher.emit(Event(
            type=EventType.USER_REGISTERED,
            data={
                "bot": bot,
                "telegram_id": user.telegram_id,
                "username": user.username or "Unknown",
            }
        ))

    await state.clear()

    # Handle inline deep links
    args = command.args
    if args:
        if args.startswith("select_"):
            gift_id = args.replace("select_", "")
            from bot.handlers.select_gift import cb_gift_select
            # We simulate a callback query context or just call the selection logic
            # For simplicity, we'll redirect to the gift selection handler
            # But we need a CallbackQuery object, so let's implement a direct handler for this
            return await handle_gift_deep_link(message, state, gift_id, **kwargs)
        elif args == "inline_browse":
            from bot.handlers.start import cb_gift_catalog
            # Simulate callback
            return await cb_gift_catalog(None, state, message=message, **kwargs)

    welcome_text = (
        "🎁 <b>Welcome to Gift Marketplace!</b>\n\n"
        "Send official Telegram Gifts to anyone!\n\n"
        "✨ <b>Features:</b>\n"
        "• Browse & select gifts\n"
        "• Add custom messages\n"
        "• Multiple recipient methods\n"
        "• Gift links for easy sharing\n\n"
        "Tap <b>🎁 Send a Gift</b> to get started!"
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Send a Gift", callback_data="gift_catalog")],
        [InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="ℹ️ How It Works", callback_data="how_it_works")],
    ])

    if user and user.is_admin:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🛡️ Admin Panel", callback_data="admin_panel")
        ])

    await message.answer(welcome_text, parse_mode="HTML", reply_markup=keyboard)


async def handle_gift_deep_link(message: Message, state: FSMContext, gift_id: str, **kwargs):
    """Handle deep link for gift selection."""
    bot = message.bot
    catalog = GiftCatalogService(bot)
    gift = await catalog.get_gift_by_id(gift_id)

    if not gift:
        await message.answer("⚠️ Gift not found.")
        return

    # Store selection
    await state.update_data(selected_gift=gift)
    
    from bot.keyboards.gift_selection import gift_preview_keyboard
    text = (
        f"🎁 <b>{gift['name']}</b>\n\n"
        f"{gift.get('icon', '🎁')} {gift.get('description', '')}\n\n"
        f"💰 <b>Price:</b> {gift['stars']} ⭐\n\n"
        "Would you like to send this gift?"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=gift_preview_keyboard(gift))


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, **kwargs):
    """Handle /menu command - show main menu."""
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Send a Gift", callback_data="gift_catalog")],
        [InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")],
        [InlineKeyboardButton(text="ℹ️ How It Works", callback_data="how_it_works")],
    ])

    await message.answer(
        "🏠 <b>Main Menu</b>\n\nChoose an option:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "gift_catalog")
async def cb_gift_catalog(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Show gift catalog."""
    message = callback.message if callback else kwargs.get("message")
    bot = message.bot
    catalog = GiftCatalogService(bot)
    gifts = await catalog.get_gifts()

    if not gifts:
        if callback:
            await callback.answer("No gifts available right now.", show_alert=True)
        else:
            await message.answer("No gifts available right now.")
        return

    keyboard = gift_catalog_keyboard(gifts, page=0)
    text = (
        "🎁 <b>Select a Gift</b>\n\n"
        "Choose a gift you'd like to send:\n\n"
        f"📦 Available gifts: {len(gifts)}"
    )
    
    if callback:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "my_orders")
async def cb_my_orders(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Show user's orders."""
    from sqlalchemy import select
    from models import Order, OrderStatus

    session_factory = kwargs.get("session")
    if not session_factory:
        await callback.answer("Error", show_alert=True)
        return

    async with session_factory() as session:
        result = await session.execute(
            select(Order)
            .where(Order.telegram_id == callback.from_user.id)
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        orders = result.scalars().all()

        if not orders:
            await callback.answer("You have no orders yet.", show_alert=True)
            return

        text = "📋 <b>Your Recent Orders</b>\n\n"
        for order in orders:
            status_emoji = {
                "delivered": "✅", "paid": "💰", "processing": "⏳",
                "failed": "❌", "refunded": "💸", "cancelled": "🚫",
                "waiting_payment": "⏳", "expired": "⏰",
            }.get(order.status.value, "📦")
            text += f"{status_emoji} <b>#{order.id}</b> — {order.gift_name or 'Unknown'} ({order.status.value})\n"
            text += f"   {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="start")],
        ])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data == "how_it_works")
async def cb_how_it_works(callback: CallbackQuery, **kwargs):
    """Show how the bot works."""
    text = (
        "ℹ️ <b>How It Works</b>\n\n"
        "<b>1.</b> Browse & select a gift\n"
        "<b>2.</b> Write a custom message (optional)\n"
        "<b>3.</b> Choose how to send it:\n"
        "   • 🎁 Share a gift link\n"
        "   • 🆔 Enter their Telegram ID\n"
        "   • 📨 Forward their message\n"
        "   • 👤 Share their contact\n"
        "<b>4.</b> Review & pay with Telegram Stars\n"
        "<b>5.</b> Gift is delivered! 🎉\n\n"
        "Payments are processed securely via Telegram.\n"
        "If delivery fails, a refund is automatically initiated."
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Start Sending", callback_data="gift_catalog")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="start")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
