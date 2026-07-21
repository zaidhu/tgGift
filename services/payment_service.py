"""
Payment service for Telegram Stars.
"""

import logging
import uuid
from typing import Optional
from aiogram import Bot
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from models import Order, OrderStatus
from core.finance import FinanceService
from bot.config import config

logger = logging.getLogger(__name__)


class PaymentService:
    """Handles Telegram Stars payment operations."""

    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session
        self.finance = FinanceService(session)

    def _generate_invoice_id(self) -> str:
        """Generate a unique invoice ID."""
        return f"inv_{uuid.uuid4().hex[:16]}"

    async def create_invoice(
        self,
        order_id: int,
        telegram_id: int,
        gift_name: str,
        stars_amount: int,
    ) -> str:
        """
        Create a Telegram Stars invoice for an order.
        Returns the invoice ID (payload).
        """
        invoice_id = self._generate_invoice_id()

        # Create payment record
        payment = await self.finance.create_payment(
            order_id=order_id,
            telegram_id=telegram_id,
            invoice_id=invoice_id,
            amount_stars=stars_amount,
            currency=config.payment.currency,
        )

        # Update order status
        order = await self.session.get(Order, order_id)
        if order:
            order.status = OrderStatus.WAITING_PAYMENT
            order.payment_invoice_id = invoice_id

        await self.session.commit()

        logger.info(f"Invoice created: {invoice_id} for order {order_id}")
        return invoice_id

    async def send_invoice_message(
        self,
        chat_id: int,
        gift_name: str,
        stars_amount: int,
        invoice_payload: str,
        order_id: int,
    ) -> bool:
        """Send an invoice message to the user."""
        try:
            await self.bot.send_invoice(
                chat_id=chat_id,
                title=f"Telegram Gift: {gift_name}",
                description=f"Purchase {gift_name} as a gift\nCustom message included",
                payload=invoice_payload,
                provider_token="",  # Empty for Stars
                currency="XTR",  # Stars currency
                prices=[LabeledPrice(label=gift_name, amount=stars_amount)],
            )
            logger.info(f"Invoice sent to {chat_id}, payload={invoice_payload}")
            return True
        except Exception as e:
            logger.error(f"Failed to send invoice to {chat_id}: {e}")
            return False

    async def verify_payment(
        self,
        successful_payment_data,
    ) -> Optional[int]:
        """
        Verify a successful payment and return the order ID.
        successful_payment_data is from aiogram.types.SuccessfulPayment.
        """
        if not successful_payment_data:
            return None

        invoice_payload = successful_payment_data.invoice_payload
        charge_id = successful_payment_data.telegram_payment_charge_id
        provider_charge_id = successful_payment_data.provider_payment_charge_id

        if not invoice_payload:
            logger.warning("No invoice payload in successful payment")
            return None

        # Find payment by invoice_id (which is our payload)
        from sqlalchemy import select
        from models import Payment

        result = await self.session.execute(
            select(Payment).where(Payment.invoice_id == invoice_payload)
        )
        payment = result.scalar_one_or_none()

        if not payment:
            logger.warning(f"Payment not found for payload: {invoice_payload}")
            return None

        if payment.status.value != "pending":
            logger.warning(f"Payment already processed: {payment.id}")
            return payment.order_id

        # Confirm payment
        await self.finance.confirm_payment(payment.id, charge_id)
        await self.session.commit()

        logger.info(f"Payment verified: order {payment.order_id}")
        return payment.order_id
