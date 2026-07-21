"""
Payment handler.
Handles Telegram Stars payment flow.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery
from aiogram.fsm.context import FSMContext

from services import PaymentService, TelegramAPIService
from core.events import dispatcher, Event, EventType
from models import Order, OrderStatus

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(callback: CallbackQuery, state: FSMContext, **kwargs):
    """Initiate payment for an order."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    order_id = int(callback.data.split(":")[1])
    session_factory = kwargs.get("session")
    user = kwargs.get("user")
    bot = callback.bot
    state_data = await state.get_data()

    async with session_factory() as session:
        order = await session.get(Order, order_id)
        if not order:
            await callback.answer("Order not found.", show_alert=True)
            return

        if order.telegram_id != callback.from_user.id:
            await callback.answer("This is not your order.", show_alert=True)
            return

        payment_service = PaymentService(bot, session)
        invoice_id = await payment_service.create_invoice(
            order_id=order_id,
            telegram_id=callback.from_user.id,
            gift_name=order.gift_name or "Gift",
            stars_amount=order.gift_stars_price or 0,
        )

        # Send invoice
        # We need to capture the message object to store its ID
        try:
            from aiogram.types import LabeledPrice
            invoice_msg = await bot.send_invoice(
                chat_id=callback.from_user.id,
                title=f"Telegram Gift: {order.gift_name or 'Gift'}",
                description=f"Purchase {order.gift_name or 'Gift'} as a gift\nCustom message included",
                payload=invoice_id,
                provider_token="",  # Empty for Stars
                currency="XTR",  # Stars currency
                prices=[LabeledPrice(label=order.gift_name or "Gift", amount=order.gift_stars_price or 0)],
            )
            await state.update_data(last_invoice_msg_id=invoice_msg.message_id)
            await callback.answer("Invoice sent! Please complete the payment.")
            
            # Optionally delete the "Review" message to keep chat clean
            try:
                await callback.message.delete()
            except:
                pass
        except Exception as e:
            logger.error(f"Failed to send invoice: {e}")
            await callback.answer("Failed to create payment. Please try again.", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout(pre_checkout: PreCheckoutQuery, **kwargs):
    """Handle pre-checkout query - validate payment."""
    # Approve the checkout (for Stars, we accept all)
    await pre_checkout.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext, **kwargs):
    """Handle successful payment."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.exceptions import TelegramBadRequest

    session_factory = kwargs.get("session")
    bot = message.bot
    state_data = await state.get_data()

    # Attempt to delete the original invoice message if we have its ID
    # Usually the successful_payment message is a separate message from the invoice
    # We can try to delete the message that preceded it or store invoice message ID in state
    invoice_msg_id = state_data.get("last_invoice_msg_id")
    if invoice_msg_id:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=invoice_msg_id)
        except TelegramBadRequest:
            pass # Message might already be deleted or too old

    async with session_factory() as session:
        payment_service = PaymentService(bot, session)
        order_id = await payment_service.verify_payment(message.successful_payment)

        if not order_id:
            await message.answer("⚠️ Payment verification failed. Please contact support.")
            return

        # Get order
        order = await session.get(Order, order_id)
        if not order:
            await message.answer("⚠️ Order not found after payment.")
            return

        # Emit payment success event
        await dispatcher.emit(Event(
            type=EventType.PAYMENT_SUCCESS,
            data={
                "bot": bot,
                "telegram_id": message.from_user.id,
                "order_id": order_id,
                "amount_stars": order.gift_stars_price,
            }
        ))

        # Process gift delivery
        await _deliver_gift(session, order, bot, state_data)

        await session.commit()

    # Notify user
    text = (
        f"🎉 <b>Payment Successful!</b>\n\n"
        f"Your gift is being delivered...\n\n"
        f"Order: #{order_id}\n"
        f"Amount: {order.gift_stars_price} ⭐"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="start")],
        [InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")],
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


async def _deliver_gift(session, order, bot, state_data):
    """Attempt to deliver the gift after payment."""
    from services import GiftLinkService

    api = TelegramAPIService(bot)

    try:
        if order.recipient_method.value == "gift_link":
            # Gift link method - wait for recipient to open
            order.status = OrderStatus.PROCESSING
            await session.commit()

            text = (
                "⏳ <b>Waiting for recipient...</b>\n\n"
                "Once they open the gift link you shared, "
                "the gift will be delivered automatically."
            )
            await bot.send_message(order.telegram_id, text, parse_mode="HTML")
            return

        # Direct delivery methods (ID, forward, contact)
        recipient_id = order.recipient_telegram_id
        if not recipient_id:
            raise ValueError("No recipient ID found")

        # Update status to processing
        order.status = OrderStatus.PROCESSING
        await session.commit()

        # Send the gift
        success = await api.send_gift_to_user(
            recipient_id=recipient_id,
            gift_id=order.gift_id or 0,
            custom_message=order.custom_message,
        )

        if success:
            order.status = OrderStatus.DELIVERED
            await session.commit()

            # Emit delivery event
            await dispatcher.emit(Event(
                type=EventType.ORDER_DELIVERED,
                data={
                    "bot": bot,
                    "telegram_id": order.telegram_id,
                    "order_id": order.id,
                    "recipient": recipient_id,
                }
            ))

            await bot.send_message(
                order.telegram_id,
                "🎁 <b>Gift Delivered Successfully!</b>\n\n"
                f"Order #{order.id}\n"
                f"Recipient: {recipient_id}",
                parse_mode="HTML",
            )
        else:
            order.status = OrderStatus.FAILED
            order.error_message = "Failed to send gift via Telegram API"
            await session.commit()

            # Auto-create refund
            from services import RefundService
            refund_service = RefundService(session)
            refund = await refund_service.auto_create_refund(
                order_id=order.id,
                reason="Gift delivery failed - Telegram API error",
            )
            await session.commit()

            # Emit failure event
            await dispatcher.emit(Event(
                type=EventType.ORDER_FAILED,
                data={
                    "bot": bot,
                    "telegram_id": order.telegram_id,
                    "order_id": order.id,
                    "error": "Telegram API delivery failed",
                }
            ))

            await bot.send_message(
                order.telegram_id,
                "❌ <b>Gift Delivery Failed</b>\n\n"
                f"Order #{order.id} could not be delivered.\n"
                f"A refund has been automatically initiated.\n\n"
                f"Refund ID: #{refund.id}" if refund else "Please contact support.",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Gift delivery error for order {order.id}: {e}")
        order.status = OrderStatus.FAILED
        order.error_message = str(e)
        await session.commit()

        # Auto-create refund
        from services import RefundService
        refund_service = RefundService(session)
        await refund_service.auto_create_refund(
            order_id=order.id,
            reason=f"Delivery error: {str(e)}",
        )
        await session.commit()

        await bot.send_message(
            order.telegram_id,
            "❌ <b>Something went wrong</b>\n\n"
            "An error occurred during delivery. A refund has been initiated.",
            parse_mode="HTML",
        )
