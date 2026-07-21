"""Inline keyboards for admin actions."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_keyboard() -> InlineKeyboardMarkup:
    """Main admin panel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton(text="📋 Orders", callback_data="admin_orders"),
        ],
        [
            InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
            InlineKeyboardButton(text="💰 Payments", callback_data="admin_payments"),
        ],
        [
            InlineKeyboardButton(text="💸 Refunds", callback_data="admin_refunds"),
            InlineKeyboardButton(text="📡 Broadcast", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(text="⚙️ System", callback_data="admin_system"),
            InlineKeyboardButton(text="🔍 Search", callback_data="admin_search"),
        ],
        [InlineKeyboardButton(text="🔙 Back to Bot", callback_data="start")],
    ])


def admin_orders_page_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Pagination for admin orders list."""
    buttons = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_orders_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"Page {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_orders_page:{page + 1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Actions for a specific order."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Retry", callback_data=f"admin_retry:{order_id}"),
            InlineKeyboardButton(text="❌ Cancel", callback_data=f"admin_cancel_order:{order_id}"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_orders")],
    ])


def admin_refund_actions_keyboard(refund_id: int) -> InlineKeyboardMarkup:
    """Actions for a specific refund."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_refund_approve:{refund_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_refund_reject:{refund_id}"),
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_refunds")],
    ])


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Settings keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Settings List", callback_data="admin_settings_list")],
        [InlineKeyboardButton(text="✏️ Edit Setting", callback_data="admin_settings_edit")],
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")],
    ])
