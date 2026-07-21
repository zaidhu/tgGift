"""
Register all event listeners for the application.
"""

import logging
from aiogram import Bot
from core.events import dispatcher, Event, EventType
from core.notifications import (
    register_notification_listeners,
    send_admin_log,
)
from bot.config import config

logger = logging.getLogger(__name__)


async def on_payment_success_admin_log(event: Event) -> None:
    """Log payment success to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return
    order_id = event.data.get("order_id", "?")
    amount = event.data.get("amount_stars", 0)
    buyer = event.data.get("telegram_id", 0)
    text = (
        f"💰 <b>Payment Success</b>\n"
        f"Order: #{order_id}\n"
        f"Amount: {amount} ⭐\n"
        f"Buyer: {buyer}"
    )
    await send_admin_log(bot, config.logging.admin_channel_id, text, parse_mode="HTML")


async def on_gift_delivered_admin_log(event: Event) -> None:
    """Log gift delivery to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return
    order_id = event.data.get("order_id", "?")
    recipient = event.data.get("recipient", "Unknown")
    text = (
        f"🎁 <b>Gift Delivered</b>\n"
        f"Order: #{order_id}\n"
        f"Recipient: {recipient}"
    )
    await send_admin_log(bot, config.logging.admin_channel_id, text, parse_mode="HTML")


async def on_gift_failed_admin_log(event: Event) -> None:
    """Log gift failure to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return
    order_id = event.data.get("order_id", "?")
    error = event.data.get("error", "Unknown")
    text = (
        f"❌ <b>Gift Failed</b>\n"
        f"Order: #{order_id}\n"
        f"Error: {error}"
    )
    await send_admin_log(bot, config.logging.admin_channel_id, text, parse_mode="HTML")


async def on_refund_admin_log(event: Event) -> None:
    """Log refund events to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return
    refund_id = event.data.get("refund_id", "?")
    status = event.data.get("refund_status", "?")
    amount = event.data.get("amount_stars", 0)
    text = (
        f"💸 <b>Refund {status.title()}</b>\n"
        f"Refund: #{refund_id}\n"
        f"Amount: {amount} ⭐"
    )
    await send_admin_log(bot, config.logging.admin_channel_id, text, parse_mode="HTML")


async def on_gift_link_opened_admin_log(event: Event) -> None:
    """Log gift link opened to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return
    order_id = event.data.get("order_id", "?")
    buyer = event.data.get("buyer_telegram_id", 0)
    text = (
        f"🔗 <b>Gift Link Opened</b>\n"
        f"Order: #{order_id}\n"
        f"Buyer: {buyer}"
    )
    await send_admin_log(bot, config.logging.admin_channel_id, text, parse_mode="HTML")


async def on_user_registered_admin_log(event: Event) -> None:
    """Log new user to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return
    telegram_id = event.data.get("telegram_id", 0)
    username = event.data.get("username", "Unknown")
    text = (
        f"👤 <b>New User</b>\n"
        f"ID: {telegram_id}\n"
        f"Username: @{username}"
    )
    await send_admin_log(bot, config.logging.admin_channel_id, text, parse_mode="HTML")


def register_all_listeners(bot: Bot):
    """Register all event listeners."""
    # Notification listeners
    register_notification_listeners()

    # Admin channel log listeners
    dispatcher.register(EventType.PAYMENT_SUCCESS, on_payment_success_admin_log)
    dispatcher.register(EventType.ORDER_DELIVERED, on_gift_delivered_admin_log)
    dispatcher.register(EventType.ORDER_FAILED, on_gift_failed_admin_log)
    dispatcher.register(EventType.REFUND_COMPLETED, on_refund_admin_log)
    dispatcher.register(EventType.REFUND_REQUESTED, on_refund_admin_log)
    dispatcher.register(EventType.GIFT_LINK_OPENED, on_gift_link_opened_admin_log)
    dispatcher.register(EventType.USER_REGISTERED, on_user_registered_admin_log)

    logger.info("All event listeners registered")
