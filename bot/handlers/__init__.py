"""Handler routers package."""

from .start import router as start_router
from .select_gift import router as select_gift_router
from .custom_message import router as custom_message_router
from .recipient import router as recipient_router
from .payment import router as payment_router
from .confirmation import router as confirmation_router

__all__ = [
    "start_router",
    "select_gift_router",
    "custom_message_router",
    "recipient_router",
    "payment_router",
    "confirmation_router",
]
