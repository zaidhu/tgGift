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
            # For aiogram 3.x, use session.make_request or custom method
            # However, getAvailableGifts is a newer method, let's use the generic __call__
            from aiogram.methods import TelegramMethod
            from typing import Any

            class GetAvailableGifts(TelegramMethod[Any]):
                __returning__ = Any
                __api_method__ = "getAvailableGifts"

                def request(self, bot: Bot) -> Any:
                    return self.prepare_request()

            result = await self.bot(GetAvailableGifts())
            logger.info(f"Raw gift data from Telegram: {result}")
            if result and "gifts" in result:
                gifts = []
                for gift in result["gifts"]:
                    # Telegram API returns 'id', 'sticker' (with 'emoji'), and 'star_count'
                    sticker = gift.get("sticker", {})
                    emoji = sticker.get("emoji", "🎁")
                    star_count = gift.get("star_count", 0)
                    
                    # Map emoji to a friendly name if possible, or just use the emoji
                    name_map = {
                        "🎂": "Cake", "🎈": "Balloon", "⭐": "Star", "❤️": "Heart",
                        "🎁": "Gift Box", "🌹": "Rose", "🧁": "Cupcake", "🏆": "Trophy",
                        "💎": "Diamond", "🚀": "Rocket", "💍": "Ring", "🍾": "Champagne",
                        "💐": "Bouquet", "🍭": "Lollipop", "🧸": "Teddy Bear"
                    }
                    friendly_name = name_map.get(emoji, f"Gift {emoji}")
                    
                    gifts.append({
                        "id": gift.get("id", 0),
                        "name": friendly_name,
                        "stars": star_count,
                        "icon": emoji,
                        "description": f"Official Telegram Gift {emoji}",
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

    async def get_gift_by_id(self, gift_id: str | int) -> Optional[dict]:
        """Get a specific gift by ID."""
        gifts = await self.get_gifts()
        gift_id_str = str(gift_id)
        for gift in gifts:
            if str(gift["id"]) == gift_id_str:
                return gift
        return None

    def clear_cache(self):
        """Clear the gift cache."""
        self._cache = []
        logger.info("Gift cache cleared")
