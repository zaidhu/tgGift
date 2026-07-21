"""
/orders - Admin order management.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func

from models import Order, OrderStatus
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard, admin_orders_page_keyboard, admin_order_actions_keyboard

router = Router()
logger = logging.getLogger(__name__)

ORDERS_PER_PAGE = 10


@router.message(Command("orders"))
async def cmd_orders(message: Message, **kwargs):
    """Show recent orders."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(
            select(func.count(Order.id))
        )
        total = result.scalar() or 0

        result = await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(ORDERS_PER_PAGE)
        )
        orders = result.scalars().all()

    if not orders:
        await message.answer("📋 <b>No orders found.</b>", parse_mode="HTML")
        return

    total_pages = max(1, (total + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    text = _format_orders_list(orders, page=0)

    keyboard = admin_orders_page_keyboard(page=0, total_pages=total_pages)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "admin_orders")
async def cb_admin_orders(callback: CallbackQuery, **kwargs):
    """Admin panel - orders view."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(select(func.count(Order.id)))
        total = result.scalar() or 0

        result = await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(ORDERS_PER_PAGE)
        )
        orders = result.scalars().all()

    total_pages = max(1, (total + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    text = _format_orders_list(orders, page=0)
    keyboard = admin_orders_page_keyboard(page=0, total_pages=total_pages)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_orders_page:"))
async def cb_orders_page(callback: CallbackQuery, **kwargs):
    """Paginate through orders."""
    page = int(callback.data.split(":")[1])
    session_factory = kwargs.get("session")

    async with session_factory() as session:
        result = await session.execute(select(func.count(Order.id)))
        total = result.scalar() or 0

        result = await session.execute(
            select(Order)
            .order_by(Order.created_at.desc())
            .offset(page * ORDERS_PER_PAGE)
            .limit(ORDERS_PER_PAGE)
        )
        orders = result.scalars().all()

    total_pages = max(1, (total + ORDERS_PER_PAGE - 1) // ORDERS_PER_PAGE)
    text = _format_orders_list(orders, page=page)
    keyboard = admin_orders_page_keyboard(page=page, total_pages=total_pages)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order:"))
async def cb_admin_order(callback: CallbackQuery, **kwargs):
    """Show details of a specific order."""
    order_id = int(callback.data.split(":")[1])
    session_factory = kwargs.get("session")

    async with session_factory() as session:
        order = await session.get(Order, order_id)

    if not order:
        await callback.answer("Order not found.", show_alert=True)
        return

    text = (
        f"📋 <b>Order #{order.id}</b>\n\n"
        f"👤 <b>Buyer:</b> {order.telegram_id}\n"
        f"🎁 <b>Gift:</b> {order.gift_name or 'N/A'}\n"
        f"💰 <b>Price:</b> {order.gift_stars_price or 0} ⭐\n"
        f"📊 <b>Status:</b> {order.status.value}\n"
        f"👤 <b>Recipient:</b> {order.recipient_telegram_id or 'N/A'}\n"
        f"📨 <b>Method:</b> {order.recipient_method.value if order.recipient_method else 'N/A'}\n"
        f"📝 <b>Message:</b> {order.custom_message or 'None'}\n"
        f"🔗 <b>Gift Link:</b> {order.gift_link_token or 'N/A'}\n"
        f"📅 <b>Created:</b> {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    if order.error_message:
        text += f"❌ <b>Error:</b> {order.error_message}\n"

    keyboard = admin_order_actions_keyboard(order.id)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_retry:"))
async def cb_admin_retry(callback: CallbackQuery, **kwargs):
    """Retry a failed order."""
    order_id = int(callback.data.split(":")[1])
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    # Enqueue retry job
    from services import QueueService
    from models import JobType
    session_factory = kwargs.get("session")

    async with session_factory() as session:
        queue = QueueService(session)
        await queue.enqueue(
            job_type=JobType.RETRY_DELIVERY,
            reference_id=order_id,
        )

    await callback.answer(f"Retry queued for order #{order_id}")


@router.callback_query(F.data.startswith("admin_cancel_order:"))
async def cb_admin_cancel(callback: CallbackQuery, **kwargs):
    """Cancel an order."""
    order_id = int(callback.data.split(":")[1])
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        order = await session.get(Order, order_id)
        if order:
            order.status = OrderStatus.CANCELLED
            await session.commit()

    await callback.answer(f"Order #{order_id} cancelled.")
    await callback.message.edit_text(
        f"🚫 <b>Order #{order_id} Cancelled</b>",
        parse_mode="HTML",
        reply_markup=admin_main_keyboard(),
    )


def _format_orders_list(orders: list, page: int) -> str:
    """Format orders into a readable list."""
    text = f"📋 <b>Orders</b> (Page {page + 1})\n\n"
    status_emoji = {
        "delivered": "✅", "paid": "💰", "processing": "⏳",
        "failed": "❌", "refunded": "💸", "cancelled": "🚫",
        "waiting_payment": "⏳", "expired": "⏰", "pending": "📦",
        "refund_pending": "💸",
    }
    for order in orders:
        emoji = status_emoji.get(order.status.value, "📦")
        text += f"{emoji} <b>#{order.id}</b> — {order.telegram_id} | "
        text += f"{order.gift_name or '?'} | "
        text += f"{order.gift_stars_price or 0}⭐ | "
        text += f"{order.status.value}\n"
        text += f"   {order.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    return text
