"""
Gift pricing service.
Applies admin-set fee/discount adjustments to gift prices.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import GiftPricing

logger = logging.getLogger(__name__)


class PricingService:
    """Service to manage and apply per-gift pricing adjustments."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_adjustment(self, gift_id: int) -> int:
        """Get the adjustment value for a gift. Returns 0 if no adjustment."""
        result = await self.session.execute(
            select(GiftPricing).where(GiftPricing.gift_id == gift_id)
        )
        pricing = result.scalar_one_or_none()
        if pricing:
            return pricing.adjustment
        return 0

    async def get_final_price(self, gift_id: int, base_stars: int) -> int:
        """Calculate the final price a user pays for a gift."""
        adjustment = await self.get_adjustment(gift_id)
        final = base_stars + adjustment
        return max(1, final)  # Minimum 1 star

    async def get_price_details(self, gift_id: int, base_stars: int, gift_name: str = "") -> dict:
        """Get full pricing details for a gift."""
        result = await self.session.execute(
            select(GiftPricing).where(GiftPricing.gift_id == gift_id)
        )
        pricing = result.scalar_one_or_none()

        if pricing:
            return {
                "gift_id": gift_id,
                "gift_name": gift_name or pricing.gift_name,
                "base_stars": pricing.base_stars,
                "adjustment": pricing.adjustment,
                "final_price": pricing.final_price,
                "has_adjustment": pricing.adjustment != 0,
            }

        return {
            "gift_id": gift_id,
            "gift_name": gift_name,
            "base_stars": base_stars,
            "adjustment": 0,
            "final_price": base_stars,
            "has_adjustment": False,
        }

    async def apply_to_gifts_list(self, gifts: list[dict]) -> list[dict]:
        """Apply pricing adjustments to a list of gifts. Returns updated list."""
        result = await self.session.execute(select(GiftPricing))
        all_pricing = {p.gift_id: p for p in result.scalars().all()}

        for gift in gifts:
            gid = gift.get("id", 0)
            pricing = all_pricing.get(gid)
            if pricing:
                gift["stars"] = pricing.final_price
                gift["original_stars"] = pricing.base_stars
                gift["adjustment"] = pricing.adjustment
            else:
                gift["original_stars"] = gift["stars"]
                gift["adjustment"] = 0

        return gifts
