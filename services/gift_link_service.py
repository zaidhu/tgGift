"""
Gift Link service.
Generates and manages unique gift links for recipient delivery.
"""

import logging
import secrets
import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import GiftLink, GiftLinkStatus, Order, OrderStatus
from bot.config import config

logger = logging.getLogger(__name__)


class GiftLinkService:
    """Manages gift link generation, tracking, and delivery."""

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _generate_token(length: int = 32) -> str:
        """Generate a secure random token for gift links."""
        return secrets.token_urlsafe(length)[:32]

    async def create_gift_link(
        self,
        order_id: int,
        buyer_telegram_id: int,
        expiration_hours: int = 72,
    ) -> GiftLink:
        """Create a new gift link for an order."""
        token = self._generate_token()
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=expiration_hours)

        gift_link = GiftLink(
            order_id=order_id,
            token=token,
            buyer_telegram_id=buyer_telegram_id,
            status=GiftLinkStatus.PENDING,
            expires_at=expires_at,
        )
        self.session.add(gift_link)

        # Update order with gift link token
        order = await self.session.get(Order, order_id)
        if order:
            order.gift_link_token = token

        await self.session.commit()

        logger.info(f"Gift link created: {token} for order {order_id}")
        return gift_link

    def generate_link_url(self, token: str) -> str:
        """Generate the full gift link URL."""
        bot_username = config.bot.username or "YourGiftBot"
        return f"https://t.me/{bot_username}?start=gift_{token}"

    async def get_gift_link_by_token(self, token: str) -> Optional[GiftLink]:
        """Get a gift link by its token."""
        result = await self.session.execute(
            select(GiftLink).where(GiftLink.token == token)
        )
        return result.scalar_one_or_none()

    async def mark_opened(self, link_id: int, recipient_telegram_id: int) -> GiftLink:
        """Mark a gift link as opened by the recipient."""
        gift_link = await self.session.get(GiftLink, link_id)
        if not gift_link:
            raise ValueError(f"GiftLink {link_id} not found")

        gift_link.status = GiftLinkStatus.OPENED
        gift_link.recipient_telegram_id = recipient_telegram_id
        gift_link.opened_at = datetime.datetime.utcnow()
        await self.session.commit()

        logger.info(f"Gift link opened: {gift_link.token} by {recipient_telegram_id}")
        return gift_link

    async def mark_delivered(self, link_id: int) -> GiftLink:
        """Mark a gift link as delivered."""
        gift_link = await self.session.get(GiftLink, link_id)
        if not gift_link:
            raise ValueError(f"GiftLink {link_id} not found")

        gift_link.status = GiftLinkStatus.DELIVERED

        # Update order status
        order = await self.session.get(Order, gift_link.order_id)
        if order:
            order.status = OrderStatus.DELIVERED

        await self.session.commit()

        logger.info(f"Gift link delivered: {gift_link.token}")
        return gift_link

    async def mark_expired(self, link_id: int) -> GiftLink:
        """Mark a gift link as expired."""
        gift_link = await self.session.get(GiftLink, link_id)
        if not gift_link:
            raise ValueError(f"GiftLink {link_id} not found")

        gift_link.status = GiftLinkStatus.EXPIRED

        order = await self.session.get(Order, gift_link.order_id)
        if order:
            order.status = OrderStatus.EXPIRED

        await self.session.commit()
        return gift_link

    async def mark_cancelled(self, link_id: int) -> GiftLink:
        """Mark a gift link as cancelled."""
        gift_link = await self.session.get(GiftLink, link_id)
        if not gift_link:
            raise ValueError(f"GiftLink {link_id} not found")

        gift_link.status = GiftLinkStatus.CANCELLED

        order = await self.session.get(Order, gift_link.order_id)
        if order:
            order.status = OrderStatus.CANCELLED

        await self.session.commit()
        return gift_link

    async def get_pending_links(self) -> list[GiftLink]:
        """Get all pending (non-expired) gift links."""
        now = datetime.datetime.utcnow()
        result = await self.session.execute(
            select(GiftLink).where(
                GiftLink.status == GiftLinkStatus.PENDING,
                (GiftLink.expires_at > now) | (GiftLink.expires_at.is_(None)),
            )
        )
        return list(result.scalars().all())

    async def get_expired_links(self) -> list[GiftLink]:
        """Get all expired gift links that need cleanup."""
        now = datetime.datetime.utcnow()
        result = await self.session.execute(
            select(GiftLink).where(
                GiftLink.status == GiftLinkStatus.PENDING,
                GiftLink.expires_at < now,
            )
        )
        return list(result.scalars().all())
