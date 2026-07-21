"""
Gift catalog service.
Fetches available Telegram Gifts from the Telegram API.
"""

import logging
from typing import Optional
from aiogram import Bot

logger = logging.getLogger(__name__)


class GiftCatalogService:
    """Service for browsing and managing available Telegram Gifts."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self._cache: list[dict] = []
        self._cache_ttl: int = 300  # 5 minutes

    async def get_gifts(self) -> list[dict]:
        """
        Get available Telegram Gifts.
        Uses Telegram's getAvailableGifts method.
        Returns cached results if available.
        """
        if self._cache:
            return self._cache

        try:
            # Telegram Bot API method: getAvailableGifts
            # This returns a list of available gifts with their IDs and prices
            result = await self.bot.call_api_method(
                "getAvailableGifts",
                {}
            )
            if result and "gifts" in result:
                gifts = []
                for gift in result["gifts"]:
                    gifts.append({
                        "id": gift.get("id", 0),
                        "name": gift.get("name", "Unknown Gift"),
                        "stars": gift.get("stars", 0),
                        "icon": gift.get("icon", ""),
                        "description": gift.get("description", ""),
                    })
                self._cache = gifts
                logger.info(f"Loaded {len(gifts)} gifts from Telegram")
                return gifts
        except Exception as e:
            logger.error(f"Failed to fetch gifts from Telegram API: {e}")

        # Fallback: default gifts if API fails
        return self._get_default_gifts()

    def _get_default_gifts(self) -> list[dict]:
        """Default gift catalog (fallback if API unavailable)."""
        return [
            {"id": 1, "name": "Cake", "stars": 50, "icon": "🎂", "description": "Birthday Cake"},
            {"id": 2, "name": "Balloon", "stars": 30, "icon": "🎈", "description": "Colorful Balloon"},
            {"id": 3, "name": "Star", "stars": 40, "icon": "⭐", "description": "Golden Star"},
            {"id": 4, "name": "Heart", "stars": 35, "icon": "❤️", "description": "Red Heart"},
            {"id": 5, "name": "Gift Box", "stars": 60, "icon": "🎁", "description": "Mystery Gift Box"},
            {"id": 6, "name": "Rose", "stars": 25, "icon": "🌹", "description": "Red Rose"},
            {"id": 7, "name": "Cupcake", "stars": 45, "icon": "🧁", "description": "Sweet Cupcake"},
            {"id": 8, "name": "Trophy", "stars": 80, "icon": "🏆", "description": "Victory Trophy"},
            {"id": 9, "name": "Diamond", "stars": 100, "icon": "💎", "description": "Diamond Ring"},
            {"id": 10, "name": "Rocket", "stars": 70, "icon": "🚀", "description": "Space Rocket"},
        ]

    async def get_gift_by_id(self, gift_id: int) -> Optional[dict]:
        """Get a specific gift by ID."""
        gifts = await self.get_gifts()
        for gift in gifts:
            if gift["id"] == gift_id:
                return gift
        return None

    def clear_cache(self):
        """Clear the gift cache."""
        self._cache = []
        logger.info("Gift cache cleared")
