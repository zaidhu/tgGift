"""Admin pricing keyboards."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def pricing_list_keyboard(pricings: list) -> InlineKeyboardMarkup:
    """Inline keyboard for pricing management."""
    buttons = []
    for p in pricings:
        adj_label = f"+{p.adjustment}⭐" if p.adjustment >= 0 else f"{p.adjustment}⭐"
        buttons.append([
            InlineKeyboardButton(
                text=f"{p.gift_name} ({p.base_stars}⭐ → {p.final_price}⭐) [{adj_label}]",
                callback_data=f"pricing_edit:{p.gift_id}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Close", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pricing_adjustment_keyboard(gift_id: int) -> InlineKeyboardMarkup:
    """Keyboard for setting a pricing adjustment on a specific gift."""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Add 1⭐ fee", callback_data=f"pricing_set:{gift_id}:1"),
            InlineKeyboardButton(text="➕ Add 2⭐ fee", callback_data=f"pricing_set:{gift_id}:2"),
        ],
        [
            InlineKeyboardButton(text="➕ Add 5⭐ fee", callback_data=f"pricing_set:{gift_id}:5"),
            InlineKeyboardButton(text="➖ Remove 1⭐", callback_data=f"pricing_set:{gift_id}:-1"),
        ],
        [
            InlineKeyboardButton(text="➖ Remove 2⭐", callback_data=f"pricing_set:{gift_id}:-2"),
            InlineKeyboardButton(text="🔄 Clear (official price)", callback_data=f"pricing_clear:{gift_id}"),
        ],
        [InlineKeyboardButton(text="🔙 Back to Pricing", callback_data="pricing_list")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
