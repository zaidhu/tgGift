"""
Telegram API service wrapper.
Handles gift sending, gift fetching, and recipient resolution.
"""

import logging
from typing import Optional
from aiogram import Bot
from aiogram.types import ChatFullInfo

logger = logging.getLogger(__name__)


class TelegramAPIService:
    """Wrapper for Telegram Bot API operations."""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_user_info(self, chat_id: int) -> Optional[ChatFullInfo]:
        """Get user information by chat ID."""
        try:
            user = await self.bot.get_chat(chat_id)
            return user
        except Exception as e:
            logger.error(f"Failed to get user info for {chat_id}: {e}")
            return None

    async def send_gift_to_user(
        self,
        recipient_id: int,
        gift_id: int,
        custom_message: Optional[str] = None,
    ) -> bool:
        """
        Send an official Telegram Gift to a user.
        Uses Telegram's sendGift method.
        """
        try:
            # Use the bot's send_gift method (available in newer aiogram versions)
            # or fall back to raw API call
            result = await self.bot.send_gift(
                user_id=recipient_id,
                gift_id=gift_id,
                text=custom_message,
            )
            logger.info(f"Gift sent to {recipient_id}, gift_id={gift_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send gift to {recipient_id}: {e}")
            return False

    async def get_user_chat_info(self, chat_id: int) -> Optional[dict]:
        """Get basic user info from a forwarded message or contact share."""
        try:
            chat = await self.bot.get_chat(chat_id)
            return {
                "id": chat.id,
                "username": chat.username,
                "first_name": chat.first_name,
                "last_name": chat.last_name,
                "type": chat.type,
            }
        except Exception as e:
            logger.error(f"Failed to get chat info for {chat_id}: {e}")
            return None

    async def verify_user_exists(self, chat_id: int) -> bool:
        """Check if a Telegram user exists (for recipient validation)."""
        try:
            await self.bot.get_chat(chat_id)
            return True
        except Exception:
            return False

    async def get_bot_info(self) -> dict:
        """Get bot's own info."""
        try:
            me = await self.bot.get_me()
            return {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
            }
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return {}
