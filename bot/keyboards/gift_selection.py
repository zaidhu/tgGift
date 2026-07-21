"""Inline keyboards for gift selection."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def gift_catalog_keyboard(gifts: list, page: int = 0, per_page: int = 6) -> InlineKeyboardMarkup:
    """Create keyboard for browsing gift catalog."""
    buttons = []
    start = page * per_page
    end = start + per_page
    page_gifts = gifts[start:end]

    for gift in page_gifts:
        icon = gift.get("icon", "🎁")
        name = gift.get("name", "Unknown")
        stars = gift.get("stars", 0)
        gift_id = gift.get("id", 0)
        buttons.append([
            InlineKeyboardButton(
                text=f"{icon} {name} ({stars} ⭐)",
                callback_data=f"gift_select:{gift_id}"
            )
        ])

    # Pagination
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"gift_page:{page - 1}"))
    if end < len(gifts):
        nav_buttons.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"gift_page:{page + 1}"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gift_preview_keyboard(gift: dict) -> InlineKeyboardMarkup:
    """Create keyboard for confirming gift selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Select This Gift", callback_data=f"gift_confirm:{gift['id']}")],
        [InlineKeyboardButton(text="🔙 Back to Catalog", callback_data="gift_catalog")],
    ])


def message_type_keyboard() -> InlineKeyboardMarkup:
    """Ask user for custom message type."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Write Custom Message", callback_data="msg_custom")],
        [InlineKeyboardButton(text="⏭️ Skip Message", callback_data="msg_skip")],
    ])


def recipient_method_keyboard() -> InlineKeyboardMarkup:
    """Ask user how they want to select the recipient."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Send Gift Link (Easiest)", callback_data="recipient_link")],
        [InlineKeyboardButton(text="🆔 Enter Telegram ID", callback_data="recipient_id")],
        [InlineKeyboardButton(text="📨 Forward Their Message", callback_data="recipient_forward")],
        [InlineKeyboardButton(text="👤 Share Contact", callback_data="recipient_contact")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])


def order_review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Keyboard for order review before payment."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pay Now", callback_data=f"pay:{order_id}")],
        [InlineKeyboardButton(text="✏️ Edit Order", callback_data=f"edit:{order_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")],
    ])


def gift_link_sent_keyboard(link_url: str) -> InlineKeyboardMarkup:
    """Keyboard shown after gift link is generated."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Copy & Send Link", url=link_url)],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="start")],
    ])
