"""
Finance module — all money logic, auditable and separate.
Payments, refunds, ledger, transactions.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import Payment, PaymentStatus, Refund, RefundStatus, Transaction, TransactionType
from models import Order, OrderStatus

logger = logging.getLogger(__name__)


class FinanceService:
    """Handles all financial operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_payment(
        self,
        order_id: int,
        telegram_id: int,
        invoice_id: str,
        amount_stars: int,
        currency: str = "stars",
        telegram_payment_charge_id: Optional[str] = None,
    ) -> Payment:
        """Create a new payment record."""
        payment = Payment(
            order_id=order_id,
            telegram_id=telegram_id,
            invoice_id=invoice_id,
            amount_stars=amount_stars,
            currency=currency,
            status=PaymentStatus.PENDING,
            telegram_payment_charge_id=telegram_payment_charge_id,
        )
        self.session.add(payment)
        await self.session.flush()
        logger.info(f"Payment created: {payment.id} for order {order_id}")
        return payment

    async def confirm_payment(self, payment_id: int, charge_id: str) -> Payment:
        """Confirm a payment as successful."""
        payment = await self.session.get(Payment, payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        payment.status = PaymentStatus.SUCCESSFUL
        payment.telegram_payment_charge_id = charge_id
        await self.session.flush()

        # Update order status
        order = await self.session.get(Order, payment.order_id)
        if order:
            order.status = OrderStatus.PAID

        # Create ledger entry
        transaction = Transaction(
            telegram_id=payment.telegram_id,
            type=TransactionType.PAYMENT_IN,
            amount_stars=payment.amount_stars,
            order_id=payment.order_id,
            payment_id=payment.id,
            description=f"Payment for order #{payment.order_id}",
        )
        self.session.add(transaction)
        await self.session.flush()

        logger.info(f"Payment confirmed: {payment_id}, charge: {charge_id}")
        return payment

    async def create_refund(
        self,
        order_id: int,
        payment_id: int,
        telegram_id: int,
        amount_stars: int,
        reason: Optional[str] = None,
    ) -> Refund:
        """Create a refund request."""
        refund = Refund(
            order_id=order_id,
            payment_id=payment_id,
            telegram_id=telegram_id,
            amount_stars=amount_stars,
            reason=reason,
            status=RefundStatus.PENDING,
        )
        self.session.add(refund)

        # Update order status
        order = await self.session.get(Order, order_id)
        if order:
            order.status = OrderStatus.REFUND_PENDING

        await self.session.flush()
        logger.info(f"Refund created: {refund.id} for order {order_id}")
        return refund

    async def approve_refund(self, refund_id: int, admin_id: int) -> Refund:
        """Approve a refund (admin action)."""
        refund = await self.session.get(Refund, refund_id)
        if not refund:
            raise ValueError(f"Refund {refund_id} not found")

        refund.status = RefundStatus.APPROVED
        refund.processed_by = admin_id
        await self.session.flush()
        logger.info(f"Refund approved: {refund_id} by admin {admin_id}")
        return refund

    async def complete_refund(self, refund_id: int, bot=None) -> Refund:
        """Complete a refund (mark as done)."""
        refund = await self.session.get(Refund, refund_id)
        if not refund:
            raise ValueError(f"Refund {refund_id} not found")

        # Get payment info
        payment = await self.session.get(Payment, refund.payment_id)
        if not payment:
            raise ValueError(f"Payment {refund.payment_id} not found for refund {refund_id}")

        # If bot is provided, attempt to refund Stars via Telegram API
        if bot and payment.telegram_payment_charge_id:
            try:
                # Telegram Bot API method: refundStarPayment
                # We use __call__ with a custom method or raw API call
                from aiogram.methods import TelegramMethod
                from typing import Any

                class RefundStarPayment(TelegramMethod[bool]):
                    __returning__ = bool
                    __api_method__ = "refundStarPayment"
                    user_id: int
                    telegram_payment_charge_id: str

                await bot(RefundStarPayment(
                    user_id=refund.telegram_id,
                    telegram_payment_charge_id=payment.telegram_payment_charge_id
                ))
                logger.info(f"Stars successfully refunded via Telegram API for refund {refund_id}")
            except Exception as e:
                logger.error(f"Failed to refund Stars via Telegram API: {e}")
                # We continue anyway to mark it as completed in our DB if needed,
                # or we could raise an error to prevent DB update.
                # For now, let's raise so we don't lie about completion.
                raise e

        refund.status = RefundStatus.COMPLETED
        await self.session.flush()

        # Update payment status
        if payment:
            payment.status = PaymentStatus.REFUNDED

        # Update order status
        order = await self.session.get(Order, refund.order_id)
        if order:
            order.status = OrderStatus.REFUNDED

        # Create ledger entry (negative)
        transaction = Transaction(
            telegram_id=refund.telegram_id,
            type=TransactionType.REFUND_OUT,
            amount_stars=-refund.amount_stars,
            order_id=refund.order_id,
            payment_id=refund.payment_id,
            refund_id=refund.id,
            description=f"Refund for order #{refund.order_id}",
        )
        self.session.add(transaction)
        await self.session.flush()

        logger.info(f"Refund completed: {refund_id}")
        return refund

    async def reject_refund(self, refund_id: int, admin_id: int, note: Optional[str] = None) -> Refund:
        """Reject a refund request."""
        refund = await self.session.get(Refund, refund_id)
        if not refund:
            raise ValueError(f"Refund {refund_id} not found")

        refund.status = RefundStatus.REJECTED
        refund.processed_by = admin_id
        refund.admin_note = note
        await self.session.flush()
        logger.info(f"Refund rejected: {refund_id} by admin {admin_id}")
        return refund

    async def get_total_revenue(self) -> int:
        """Get total revenue in stars."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.amount_stars), 0)).where(
                Payment.status == PaymentStatus.SUCCESSFUL
            )
        )
        return result.scalar() or 0

    async def get_total_refunds(self) -> int:
        """Get total refunded stars."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(Refund.amount_stars), 0)).where(
                Refund.status == RefundStatus.COMPLETED
            )
        )
        return result.scalar() or 0

    async def get_daily_revenue(self) -> int:
        """Get today's revenue in stars."""
        from sqlalchemy import text
        result = await self.session.execute(text("""
            SELECT COALESCE(SUM(amount_stars), 0)
            FROM payments
            WHERE status = 'successful'
            AND created_at >= CURRENT_DATE
        """))
        return result.scalar() or 0

    async def get_monthly_revenue(self) -> int:
        """Get this month's revenue in stars."""
        from sqlalchemy import text
        result = await self.session.execute(text("""
            SELECT COALESCE(SUM(amount_stars), 0)
            FROM payments
            WHERE status = 'successful'
            AND created_at >= date_trunc('month', CURRENT_DATE)
        """))
        return result.scalar() or 0
