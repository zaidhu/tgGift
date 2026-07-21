"""
Logging middleware.
Logs all bot interactions for debugging and analytics.
"""

import logging
import time
from typing import Any, Callable, Awaitable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Middleware that logs all incoming updates."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        start_time = time.time()

        # Determine update type
        update_type = "unknown"
        user_id = None
        if isinstance(event, Update):
            if event.message:
                update_type = "message"
                user_id = event.message.from_user.id
            elif event.callback_query:
                update_type = "callback_query"
                user_id = event.callback_query.from_user.id
            elif event.inline_query:
                update_type = "inline_query"
                user_id = event.inline_query.from_user.id
            elif event.pre_checkout_query:
                update_type = "pre_checkout_query"
                user_id = event.pre_checkout_query.from_user.id

        logger.debug(
            f"[{update_type}] User: {user_id} | "
            f"Update ID: {getattr(event, 'update_id', '?')}"
        )

        result = await handler(event, data)

        elapsed = time.time() - start_time
        logger.debug(f"[{update_type}] Completed in {elapsed:.3f}s")

        return result
