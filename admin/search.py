"""
/search - Admin order search.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from models import Order
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard, admin_order_actions_keyboard

router = Router()
logger = logging.getLogger(__name__)


class SearchStates(StatesGroup):
    WAITING_QUERY = State()


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext, **kwargs):
    """Start order search."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    await state.set_state(SearchStates.WAITING_QUERY)

    text = (
        "🔍 <b>Search Orders</b>\n\n"
        "Send me a search query. You can search by:\n"
        "• Order ID (e.g., #123)\n"
        "• Telegram User ID\n"
        "• Gift name\n\n"
        "Send /cancel to abort."
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("retry"))
async def cmd_retry(message: Message, **kwargs):
    """Quick retry command for admins."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    args = message.get_args()
    if not args or not args.isdigit():
        await message.answer("Usage: /retry <order_id>\n\nExample: /retry 123")
        return

    order_id = int(args)
    session_factory = kwargs.get("session")

    from services import QueueService
    from models import JobType

    async with session_factory() as session:
        queue = QueueService(session)
        await queue.enqueue(job_type=JobType.RETRY_DELIVERY, reference_id=order_id)

    await message.answer(f"🔄 Retry queued for order #{order_id}")


@router.message(SearchStates.WAITING_QUERY)
async def msg_search_query(message: Message, state: FSMContext, **kwargs):
    """Execute search."""
    query = (message.text or "").strip()
    if not query:
        await message.answer("⚠️ Please enter a search query.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        results = []

        # Try order ID
        if query.startswith("#"):
            try:
                order_id = int(query.replace("#", ""))
                order = await session.get(Order, order_id)
                if order:
                    results.append(order)
            except ValueError:
                pass

        # Try user ID
        if not results and query.isdigit():
            user_id = int(query)
            result = await session.execute(
                select(Order).where(Order.telegram_id == user_id)
                .order_by(Order.created_at.desc()).limit(10)
            )
            results = list(result.scalars().all())

        # Try gift name
        if not results:
            result = await session.execute(
                select(Order).where(Order.gift_name.ilike(f"%{query}%"))
                .order_by(Order.created_at.desc()).limit(10)
            )
            results = list(result.scalars().all())

    if not results:
        await message.answer("🔍 No results found for your query.")
        await state.clear()
        return

    text = f"🔍 <b>Search Results ({len(results)})</b>\n\n"
    for order in results:
        text += (
            f"📋 <b>#{order.id}</b> — {order.telegram_id} | "
            f"{order.gift_name or '?'} | "
            f"{order.gift_stars_price or 0}⭐ | "
            f"{order.status.value}\n"
            f"   {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Search Again", callback_data="search_again")],
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")],
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await state.clear()


@router.callback_query(F.data == "search_again")
async def cb_search_again(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Search again."""
    await state.set_state(SearchStates.WAITING_QUERY)
    await callback.message.edit_text(
        "🔍 <b>Search Orders</b>\n\n"
        "Send me a search query.\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_search")
async def cb_admin_search(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Admin panel - search."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    await state.set_state(SearchStates.WAITING_QUERY)
    await callback.message.edit_text(
        "🔍 <b>Search Orders</b>\n\n"
        "Send me a search query (order ID, user ID, or gift name).\n"
        "Send /cancel to abort.",
        parse_mode="HTML",
    )
    await callback.answer()
