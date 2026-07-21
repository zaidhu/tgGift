"""
Authentication middleware.
Handles user registration, admin checks, and session management.
"""

import logging
from typing import Any, Callable, Awaitable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, UserStatus
from bot.config import config

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware that ensures users are registered and checks admin status."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Get user info from the update
        user_from_update = None
        if isinstance(event, Update):
            if event.message:
                user_from_update = event.message.from_user
            elif event.callback_query:
                user_from_update = event.callback_query.from_user
            elif event.inline_query:
                user_from_update = event.inline_query.from_user
            elif event.pre_checkout_query:
                user_from_update = event.pre_checkout_query.from_user

        if user_from_update:
            async with self.session_factory() as session:
                # Find or create user
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.telegram_id == user_from_update.id)
                )
                user = result.scalar_one_or_none()

                if user:
                    # Update username if changed
                    if user.username != user_from_update.username:
                        user.username = user_from_update.username
                        user.first_name = user_from_update.first_name
                        user.last_name = user_from_update.last_name
                        user.language_code = user_from_update.language_code
                        await session.commit()

                    # Check if blocked
                    if user.status == UserStatus.BLOCKED:
                        if event.message:
                            await event.message.answer("You are blocked from using this bot.")
                        return None

                    data["user"] = user
                else:
                    # Register new user
                    user = User(
                        telegram_id=user_from_update.id,
                        username=user_from_update.username,
                        first_name=user_from_update.first_name,
                        last_name=user_from_update.last_name,
                        language_code=user_from_update.language_code,
                        is_admin=config.admin.is_admin(user_from_update.id),
                    )
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    data["user"] = user

                    logger.info(f"New user registered: {user.telegram_id} (@{user.username})")

        data["session"] = self.session_factory
        data["is_admin"] = user_from_update and config.admin.is_admin(user_from_update.id)

        return await handler(event, data)
