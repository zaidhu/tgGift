"""Admin commands router package."""

from .stats import router as stats_router
from .orders import router as orders_router
from .users import router as users_router
from .payments import router as payments_router
from .refunds import router as refunds_router
from .broadcast import router as broadcast_router
from .system import router as system_router
from .settings import router as settings_router
from .search import router as search_router

__all__ = [
    "stats_router",
    "orders_router",
    "users_router",
    "payments_router",
    "refunds_router",
    "broadcast_router",
    "system_router",
    "settings_router",
    "search_router",
]
