"""Inline keyboards package."""

from .gift_selection import (
    gift_catalog_keyboard,
    gift_preview_keyboard,
    message_type_keyboard,
    recipient_method_keyboard,
    order_review_keyboard,
    gift_link_sent_keyboard,
)
from .order_actions import (
    admin_main_keyboard,
    order_detail_keyboard,
    refund_action_keyboard,
)
from .pricing import (
    pricing_list_keyboard,
    pricing_adjustment_keyboard,
)

__all__ = [
    "gift_catalog_keyboard",
    "gift_preview_keyboard",
    "message_type_keyboard",
    "recipient_method_keyboard",
    "order_review_keyboard",
    "gift_link_sent_keyboard",
    "admin_main_keyboard",
    "order_detail_keyboard",
    "refund_action_keyboard",
    "pricing_list_keyboard",
    "pricing_adjustment_keyboard",
]
