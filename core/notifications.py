"""
Notification dispatcher.
Handles sending notifications to buyers and recipients.
"""

import logging
from aiogram import Bot
from aiogram.types import Message
from core.events import Event, EventType, dispatcher

logger = logging.getLogger(__name__)


async def send_notification(bot: Bot, chat_id: int, text: str, **kwargs) -> bool:
    """Send a notification message to a user."""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {chat_id}: {e}")
        return False


async def send_admin_log(bot: Bot, admin_channel_id: int, text: str, **kwargs) -> bool:
    """Send a log message to the admin channel."""
    if not admin_channel_id:
        return False
    try:
        await bot.send_message(admin_channel_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Failed to send admin log to {admin_channel_id}: {e}")
        return False


# ─── Event Listeners for Notifications ───────────────────────────────────────


async def on_payment_success(event: Event) -> None:
    """Notify buyer when payment succeeds."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    amount = event.data.get("amount_stars", 0)

    text = (
        f"✅ <b>Payment Successful!</b>\n\n"
        f"Order #{order_id} has been paid.\n"
        f"Amount: {amount} ⭐\n\n"
        f"Your gift is being processed..."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")


async def on_gift_delivered(event: Event) -> None:
    """Notify buyer when gift is delivered."""
    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    recipient = event.data.get("recipient", "Unknown")

    text = (
        f"🎁 <b>Gift Delivered!</b>\n\n"
        f"Order #{order_id} has been successfully delivered.\n"
        f"Recipient: {recipient}\n\n"
        f"Thank you for using our service!"
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")


async def on_gift_failed(event: Event) -> None:
    """Notify buyer when gift delivery fails."""
    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    error = event.data.get("error", "Unknown error")

    text = (
        f"❌ <b>Gift Delivery Failed</b>\n\n"
        f"Order #{order_id} could not be delivered.\n"
        f"Reason: {error}\n\n"
        f"A refund has been automatically initiated."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")


async def on_refund_completed(event: Event) -> None:
    """Notify buyer when refund is processed."""
    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    amount = event.data.get("amount_stars", 0)

    text = (
        f"💰 <b>Refund Processed</b>\n\n"
        f"Order #{order_id} has been refunded.\n"
        f"Amount: {amount} ⭐\n\n"
        f"If you have any questions, please contact support."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")


async def on_gift_link_opened(event: Event) -> None:
    """Notify buyer when gift link is opened by recipient."""
    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("buyer_telegram_id", 0)
    order_id = event.data.get("order_id", "?")

    text = (
        f"🔗 <b>Gift Link Opened!</b>\n\n"
        f"Order #{order_id} — your recipient has opened the gift link.\n"
        f"The gift will be delivered shortly."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")


# ─── Register all notification listeners ─────────────────────────────────────


def register_notification_listeners():
    """Register all notification event listeners."""
    dispatcher.register(EventType.PAYMENT_SUCCESS, on_payment_success)
    dispatcher.register(EventType.ORDER_DELIVERED, on_gift_delivered)
    dispatcher.register(EventType.ORDER_FAILED, on_gift_failed)
    dispatcher.register(EventType.REFUND_COMPLETED, on_refund_completed)
    dispatcher.register(EventType.GIFT_LINK_OPENED, on_gift_link_opened)
