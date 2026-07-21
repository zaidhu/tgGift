"""
Refund service.
Handles automatic and manual refund processing.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Refund, RefundStatus, Order, OrderStatus, Payment
from core.finance import FinanceService

logger = logging.getLogger(__name__)


class RefundService:
    """Handles refund operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.finance = FinanceService(session)

    async def auto_create_refund(self, order_id: int, reason: str) -> Optional[Refund]:
        """
        Automatically create a refund when delivery fails.
        """
        order = await self.session.get(Order, order_id)
        if not order:
            logger.warning(f"Order {order_id} not found for auto refund")
            return None

        # Find the payment for this order
        result = await self.session.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(f"No payment found for order {order_id}")
            return None

        refund = await self.finance.create_refund(
            order_id=order_id,
            payment_id=payment.id,
            telegram_id=order.telegram_id,
            amount_stars=payment.amount_stars,
            reason=reason,
        )
        await self.session.commit()

        logger.info(f"Auto refund created: {refund.id} for order {order_id}")
        return refund

    async def get_pending_refunds(self) -> list[Refund]:
        """Get all pending refunds."""
        result = await self.session.execute(
            select(Refund).where(Refund.status == RefundStatus.PENDING)
        )
        return list(result.scalars().all())

    async def approve_refund(self, refund_id: int, admin_id: int) -> Refund:
        """Approve a refund request."""
        refund = await self.finance.approve_refund(refund_id, admin_id)
        await self.session.commit()

        # Auto-complete after approval (for Stars, Telegram handles the actual refund)
        refund = await self.finance.complete_refund(refund_id)
        await self.session.commit()

        logger.info(f"Refund approved and completed: {refund_id}")
        return refund

    async def reject_refund(self, refund_id: int, admin_id: int, note: Optional[str] = None) -> Refund:
        """Reject a refund request."""
        refund = await self.finance.reject_refund(refund_id, admin_id, note)
        await self.session.commit()
        logger.info(f"Refund rejected: {refund_id}")
        return refund

    async def get_all_refunds(self, limit: int = 50, offset: int = 0) -> list[Refund]:
        """Get all refunds with pagination."""
        result = await self.session.execute(
            select(Refund)
            .order_by(Refund.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_refund_by_id(self, refund_id: int) -> Optional[Refund]:
        """Get a refund by ID."""
        return await self.session.get(Refund, refund_id)
