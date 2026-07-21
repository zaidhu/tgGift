"""
Register all event listeners for the application.
Wires up:
- Buyer notifications (DM)
- Admin critical alerts (DM to owner)
- Activity logs (admin channel)
"""

import logging
from aiogram import Bot
from core.events import dispatcher, Event, EventType
from core.notifications import (
    NotificationService,
    register_notification_listeners,
)
from bot.config import config

logger = logging.getLogger(__name__)


async def on_payment_success_admin_log(event: Event) -> None:
    """Log purchase to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return

    notif = NotificationService(bot, config.logging.admin_channel_id, config.admin.owner_id)
    order_id = event.data.get("order_id", 0)
    amount = event.data.get("amount_stars", 0)
    buyer = event.data.get("telegram_id", 0)

    # Already handled in notifications.py, but log to channel here too
    # Channel log is sent from notifications.py on_payment_success


async def on_gift_delivered_admin_log(event: Event) -> None:
    """Log gift delivery to admin channel."""
    # Already handled in notifications.py on_gift_delivered
    pass


async def on_gift_failed_admin_log(event: Event) -> None:
    """Log gift failure to admin channel + alert admin DM."""
    bot = event.data.get("bot")
    if not bot:
        return

    order_id = event.data.get("order_id", 0)
    error = event.data.get("error", "Unknown")
    buyer = event.data.get("telegram_id", 0)

    notif = NotificationService(bot, config.logging.admin_channel_id, config.admin.owner_id)
    await notif.alert_delivery_failed(order_id=order_id, reason=error, telegram_id=buyer)
    await notif.log_delivery_failed(order_id=order_id, reason=error)


async def on_refund_admin_log(event: Event) -> None:
    """Log refund events to admin channel."""
    bot = event.data.get("bot")
    if not bot:
        return

    notif = NotificationService(bot, config.logging.admin_channel_id, config.admin.owner_id)
    refund_id = event.data.get("refund_id", 0)
    status = event.data.get("refund_status", "unknown")
    amount = event.data.get("amount_stars", 0)
    admin_id = event.data.get("admin_id", 0)

    if status == "approved":
        await notif.log_refund_approved(refund_id=refund_id, amount=amount, admin_id=admin_id)
    elif status == "rejected":
        await notif.log_refund_rejected(refund_id=refund_id, admin_id=admin_id)
    else:
        await notif.log_refund_created(
            refund_id=refund_id,
            order_id=event.data.get("order_id", 0),
            amount=amount,
            reason="Auto or manual",
        )


async def on_gift_link_opened_admin_log(event: Event) -> None:
    """Log gift link opened to admin channel."""
    # Already handled in notifications.py on_gift_link_opened
    pass


async def on_user_registered_admin_log(event: Event) -> None:
    """Log new user to admin channel."""
    # Already handled in notifications.py on_user_registered
    pass


async def on_broadcast_sent_admin_log(event: Event) -> None:
    """Log broadcast to admin channel."""
    # Already handled in notifications.py on_broadcast_sent
    pass


async def on_system_error(event: Event) -> None:
    """Handle system error events - critical alert to admin DM."""
    bot = event.data.get("bot")
    if not bot:
        return

    notif = NotificationService(bot, config.logging.admin_channel_id, config.admin.owner_id)
    component = event.data.get("component", "Unknown")
    error = event.data.get("error", "Unknown error")
    await notif.alert_system_failure(component=component, error=error)


def register_all_listeners(bot: Bot):
    """Register all event listeners."""
    # Notification listeners (buyer DM + channel logs)
    register_notification_listeners()

    # Admin channel log listeners (supplementary)
    dispatcher.register(EventType.PAYMENT_SUCCESS, on_payment_success_admin_log)
    dispatcher.register(EventType.ORDER_DELIVERED, on_gift_delivered_admin_log)
    dispatcher.register(EventType.ORDER_FAILED, on_gift_failed_admin_log)
    dispatcher.register(EventType.REFUND_COMPLETED, on_refund_admin_log)
    dispatcher.register(EventType.REFUND_REQUESTED, on_refund_admin_log)
    dispatcher.register(EventType.GIFT_LINK_OPENED, on_gift_link_opened_admin_log)
    dispatcher.register(EventType.USER_REGISTERED, on_user_registered_admin_log)
    dispatcher.register(EventType.BROADCAST_SENT, on_broadcast_sent_admin_log)
    dispatcher.register(EventType.SYSTEM_ERROR, on_system_error)

    logger.info("All event listeners registered")
