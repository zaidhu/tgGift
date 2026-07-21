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
        buyer_id: Optional[int] = None,
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
            # Check if this is an inline invoice payload (inline_GIFTID_RECIPIENTID)
            if invoice_payload.startswith("inline_"):
                return await self._handle_inline_payment(successful_payment_data, buyer_id)
            
            # Check if this is a custom star payment payload (custom_AMOUNT_RECIPIENTID)
            if invoice_payload.startswith("custom_"):
                return await self._handle_custom_star_payment(successful_payment_data, buyer_id)
            
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

    async def _handle_inline_payment(self, payment_data, buyer_id: Optional[int] = None) -> Optional[int]:
        """Create an order and payment for a direct inline payment."""
        payload = payment_data.invoice_payload
        parts = payload.split("_")
        if len(parts) < 3:
            return None
        
        gift_id = parts[1]
        recipient_id = int(parts[2])
        
        from services import GiftCatalogService
        catalog = GiftCatalogService(self.bot)
        gift = await catalog.get_gift_by_id(gift_id)
        
        if not gift:
            return None
            
        from models import Order, OrderStatus, RecipientMethod, User
        from sqlalchemy import select
        
        # Try to find buyer in database
        buyer_internal_id = None
        if buyer_id:
            result = await self.session.execute(select(User).where(User.telegram_id == buyer_id))
            buyer = result.scalar_one_or_none()
            if buyer:
                buyer_internal_id = buyer.id
        
        # Create the order
        # telegram_id = the one who pays (for notifications)
        # recipient_telegram_id = the one who requested (receives the gift)
        order = Order(
            telegram_id=buyer_id or recipient_id, 
            buyer_id=buyer_internal_id,
            status=OrderStatus.PAID,
            gift_id=gift_id,
            gift_name=gift.get("name"),
            gift_stars_price=gift.get("stars"),
            recipient_method=RecipientMethod.USER_ID,
            recipient_telegram_id=recipient_id,
        )
        self.session.add(order)
        await self.session.flush()
        
        # Create the payment record
        payment = await self.finance.create_payment(
            order_id=order.id,
            telegram_id=buyer_id or 0,
            invoice_id=payload,
            amount_stars=gift.get("stars"),
            telegram_payment_charge_id=payment_data.telegram_payment_charge_id
        )
        
        # Confirm it immediately
        await self.finance.confirm_payment(payment.id, payment_data.telegram_payment_charge_id)
        
        return order.id

    async def _handle_custom_star_payment(self, payment_data, buyer_id: Optional[int] = None) -> Optional[int]:
        """Handle a custom star payment from inline mode."""
        payload = payment_data.invoice_payload
        parts = payload.split("_")
        if len(parts) < 3:
            return None
        
        amount = int(parts[1])
        recipient_id = int(parts[2])
        
        from models import Order, OrderStatus, RecipientMethod, User
        from sqlalchemy import select
        
        # Try to find buyer in database
        buyer_internal_id = None
        if buyer_id:
            result = await self.session.execute(select(User).where(User.telegram_id == buyer_id))
            buyer = result.scalar_one_or_none()
            if buyer:
                buyer_internal_id = buyer.id
        
        # Create a "Custom Payment" order
        order = Order(
            telegram_id=buyer_id or recipient_id, 
            buyer_id=buyer_internal_id,
            status=OrderStatus.PAID,
            gift_id=None,
            gift_name=f"Custom Payment ({amount} Stars)",
            gift_stars_price=amount,
            recipient_method=RecipientMethod.USER_ID,
            recipient_telegram_id=recipient_id,
        )
        self.session.add(order)
        await self.session.flush()
        
        # Create the payment record
        payment = await self.finance.create_payment(
            order_id=order.id,
            telegram_id=buyer_id or 0,
            invoice_id=payload,
            amount_stars=amount,
            telegram_payment_charge_id=payment_data.telegram_payment_charge_id
        )
        
        # Confirm it immediately
        await self.finance.confirm_payment(payment.id, payment_data.telegram_payment_charge_id)
        
        return order.id
