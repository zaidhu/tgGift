"""
Notification service.
Dual notification system:
- DM to admin (owner) for critical alerts (errors, failures, system problems)
- Channel messages for activity logs (new users, purchases, deliveries, refunds)
"""

import logging
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from core.events import Event, EventType, dispatcher

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Dual notification system:
    - DM to admin for critical issues (errors, failures, system problems)
    - Channel messages for activity logs (new users, purchases, deliveries, refunds)
    """

    def __init__(self, bot: Bot, admin_channel_id: int = 0, admin_id: int = 0):
        self.bot = bot
        self.channel_id = admin_channel_id
        self.admin_id = admin_id

    # ─── Critical Alerts (DM to Admin) ───────────────────────────────────────

    async def send_critical_alert(self, title: str, message: str, details: dict | None = None):
        """Send critical alert to admin's DM."""
        if not self.admin_id:
            logger.warning("No ADMIN_ID set — cannot send critical alert")
            return

        text = f"🚨 <b>CRITICAL ALERT</b>\n\n"
        text += f"<b>{title}</b>\n\n"
        text += message

        if details:
            text += "\n\n<b>Details:</b>\n"
            for key, value in details.items():
                text += f"  • <b>{key}:</b> {value}\n"

        text += f"\n<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"

        try:
            await self.bot.send_message(self.admin_id, text, parse_mode="HTML")
            logger.info(f"Critical alert sent to admin DM: {title}")
        except TelegramAPIError as e:
            logger.error(f"Failed to send critical alert to DM: {e}")

    async def alert_system_failure(self, component: str, error: str):
        """System component failure alert."""
        await self.send_critical_alert(
            title=f"🔴 System Failure: {component}",
            message=f"Component <b>{component}</b> has encountered a critical error.",
            details={"Error": error[:500] if error else "Unknown"},
        )

    async def alert_delivery_failed(self, order_id: int, reason: str, telegram_id: int):
        """Gift delivery failed alert."""
        await self.send_critical_alert(
            title="❌ Delivery Failed",
            message=f"Order <b>#{order_id}</b> could not be delivered.",
            details={
                "Order ID": order_id,
                "Buyer Telegram ID": telegram_id,
                "Reason": reason[:200] if reason else "Unknown",
            },
        )

    async def alert_payment_error(self, order_id: int, error: str, telegram_id: int):
        """Payment processing error alert."""
        await self.send_critical_alert(
            title="💰 Payment Error",
            message=f"Payment error on order <b>#{order_id}</b>.",
            details={
                "Order ID": order_id,
                "Telegram ID": telegram_id,
                "Error": error[:500] if error else "Unknown",
            },
        )

    async def alert_refund_issue(self, refund_id: int, order_id: int, issue: str):
        """Refund problem alert."""
        await self.send_critical_alert(
            title="💸 Refund Issue",
            message=f"Refund <b>#{refund_id}</b> (Order #{order_id}) needs attention.",
            details={
                "Refund ID": refund_id,
                "Order ID": order_id,
                "Issue": issue[:500] if issue else "Unknown",
            },
        )

    async def alert_database_down(self, error: str):
        """Database connection lost alert."""
        await self.send_critical_alert(
            title="🗄️ Database Down",
            message="The bot has lost connection to the database.",
            details={"Error": error[:500] if error else "Unknown"},
        )

    async def alert_api_rate_limited(self, api_name: str, retry_after: str):
        """Rate limit warning."""
        await self.send_critical_alert(
            title="⚠️ Rate Limited",
            message=f"API <b>{api_name}</b> rate limit hit.",
            details={"Retry After": retry_after},
        )

    # ─── Activity Logs (Admin Channel) ──────────────────────────────────────

    async def send_channel_log(self, emoji: str, title: str, details: dict):
        """Send activity log to admin channel."""
        if not self.channel_id:
            return

        text = f"{emoji} <b>{title}</b>\n\n"
        for key, value in details.items():
            text += f"• <b>{key}:</b> {value}\n"

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text += f"\n<i>🕐 {timestamp}</i>"

        try:
            await self.bot.send_message(self.channel_id, text, parse_mode="HTML")
        except TelegramAPIError as e:
            logger.error(f"Failed to send channel log: {e}")

    async def log_new_user(self, telegram_id: int, username: str):
        """Log new user registration."""
        await self.send_channel_log(
            emoji="🆕",
            title="New User Registered",
            details={
                "Telegram ID": telegram_id,
                "Username": f"@{username}" if username else "Unknown",
            },
        )

    async def log_purchase(self, order_id: int, telegram_id: int, gift_name: str, stars: int):
        """Log a purchase."""
        await self.send_channel_log(
            emoji="🛒",
            title="New Purchase",
            details={
                "Order ID": f"#{order_id}",
                "Buyer": telegram_id,
                "Gift": gift_name,
                "Amount": f"{stars} ⭐",
            },
        )

    async def log_delivery_success(self, order_id: int, buyer_id: int, recipient_id: int):
        """Log successful gift delivery."""
        await self.send_channel_log(
            emoji="✅",
            title="Gift Delivered",
            details={
                "Order ID": f"#{order_id}",
                "Buyer": buyer_id,
                "Recipient": recipient_id,
            },
        )

    async def log_delivery_failed(self, order_id: int, reason: str):
        """Log failed delivery."""
        await self.send_channel_log(
            emoji="❌",
            title="Delivery Failed",
            details={
                "Order ID": f"#{order_id}",
                "Reason": reason[:200] if reason else "Unknown",
            },
        )

    async def log_refund_created(self, refund_id: int, order_id: int, amount: int, reason: str):
        """Log refund creation."""
        await self.send_channel_log(
            emoji="💸",
            title="Refund Created",
            details={
                "Refund ID": f"#{refund_id}",
                "Order ID": f"#{order_id}",
                "Amount": f"{amount} ⭐",
                "Reason": reason[:150] if reason else "N/A",
            },
        )

    async def log_refund_approved(self, refund_id: int, amount: int, admin_id: int):
        """Log refund approval."""
        await self.send_channel_log(
            emoji="✅",
            title="Refund Approved",
            details={
                "Refund ID": f"#{refund_id}",
                "Amount": f"{amount} ⭐",
                "Approved By": admin_id,
            },
        )

    async def log_refund_rejected(self, refund_id: int, admin_id: int):
        """Log refund rejection."""
        await self.send_channel_log(
            emoji="🚫",
            title="Refund Rejected",
            details={
                "Refund ID": f"#{refund_id}",
                "Rejected By": admin_id,
            },
        )

    async def log_broadcast_sent(self, sent: int, failed: int):
        """Log broadcast completion."""
        await self.send_channel_log(
            emoji="📡",
            title="Broadcast Sent",
            details={
                "Delivered": sent,
                "Failed": failed,
            },
        )

    async def log_retry_queued(self, order_id: int):
        """Log retry job queued."""
        await self.send_channel_log(
            emoji="🔄",
            title="Delivery Retry Queued",
            details={"Order ID": f"#{order_id}"},
        )

    async def log_gift_link_opened(self, order_id: int, recipient_id: int):
        """Log gift link opened by recipient."""
        await self.send_channel_log(
            emoji="🔗",
            title="Gift Link Opened",
            details={
                "Order ID": f"#{order_id}",
                "Recipient": recipient_id,
            },
        )

    async def log_gift_link_expired(self, order_id: int, buyer_id: int):
        """Log expired gift link."""
        await self.send_channel_log(
            emoji="⏰",
            title="Gift Link Expired",
            details={
                "Order ID": f"#{order_id}",
                "Buyer": buyer_id,
            },
        )

    async def log_order_cancelled(self, order_id: int, admin_id: int):
        """Log order cancellation by admin."""
        await self.send_channel_log(
            emoji="🚫",
            title="Order Cancelled",
            details={
                "Order ID": f"#{order_id}",
                "Cancelled By": admin_id,
            },
        )


# ─── Standalone notification helpers (for direct calls) ─────────────────────


async def send_notification(bot: Bot, chat_id: int, text: str, **kwargs) -> bool:
    """Send a notification message to a user."""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Failed to send notification to {chat_id}: {e}")
        return False


# ─── Event Listeners for Buyer Notifications + Channel Logs ─────────────────


async def on_payment_success(event: Event) -> None:
    """Notify buyer when payment succeeds."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    amount = event.data.get("amount_stars", 0)

    # Notify buyer
    text = (
        f"✅ <b>Payment Successful!</b>\n\n"
        f"Order #{order_id} has been paid.\n"
        f"Amount: {amount} ⭐\n\n"
        f"Your gift is being processed..."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")

    # Log to channel
    notif = NotificationService(bot, config.logging.admin_channel_id)
    await notif.log_purchase(order_id=order_id, telegram_id=chat_id, gift_name="Gift", stars=amount)


async def on_gift_delivered(event: Event) -> None:
    """Notify buyer when gift is delivered."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    recipient = event.data.get("recipient", "Unknown")

    # Notify buyer
    text = (
        f"🎁 <b>Gift Delivered!</b>\n\n"
        f"Order #{order_id} has been successfully delivered.\n"
        f"Recipient: {recipient}\n\n"
        f"Thank you for using our service!"
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")

    # Log to channel
    notif = NotificationService(bot, config.logging.admin_channel_id)
    await notif.log_delivery_success(order_id=order_id, buyer_id=chat_id, recipient_id=recipient)


async def on_gift_failed(event: Event) -> None:
    """Notify buyer when gift delivery fails AND alert admin DM."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    error = event.data.get("error", "Unknown error")

    # Notify buyer
    text = (
        f"❌ <b>Gift Delivery Failed</b>\n\n"
        f"Order #{order_id} could not be delivered.\n"
        f"Reason: {error}\n\n"
        f"A refund has been automatically initiated."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")

    # Alert admin DM (critical)
    admin_notif = NotificationService(bot, config.logging.admin_channel_id, config.admin.owner_id)
    await admin_notif.alert_delivery_failed(order_id=order_id, reason=error, telegram_id=chat_id)

    # Log to channel
    await admin_notif.log_delivery_failed(order_id=order_id, reason=error)


async def on_refund_completed(event: Event) -> None:
    """Notify buyer when refund is processed."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    amount = event.data.get("amount_stars", 0)

    # Notify buyer
    text = (
        f"💰 <b>Refund Processed</b>\n\n"
        f"Order #{order_id} has been refunded.\n"
        f"Amount: {amount} ⭐\n\n"
        f"If you have any questions, please contact support."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")


async def on_gift_link_opened(event: Event) -> None:
    """Notify buyer when gift link is opened by recipient."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    chat_id = event.data.get("buyer_telegram_id", 0)
    order_id = event.data.get("order_id", "?")
    recipient = event.data.get("recipient_telegram_id", "Unknown")

    # Notify buyer
    text = (
        f"🔗 <b>Gift Link Opened!</b>\n\n"
        f"Order #{order_id} — your recipient has opened the gift link.\n"
        f"The gift will be delivered shortly."
    )
    await send_notification(bot, chat_id, text, parse_mode="HTML")

    # Log to channel
    notif = NotificationService(bot, config.logging.admin_channel_id)
    await notif.log_gift_link_opened(order_id=order_id, recipient_id=recipient)


async def on_user_registered(event: Event) -> None:
    """Log new user registration to channel."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    notif = NotificationService(bot, config.logging.admin_channel_id)
    await notif.log_new_user(
        telegram_id=event.data.get("telegram_id", 0),
        username=event.data.get("username", "Unknown"),
    )


async def on_broadcast_sent(event: Event) -> None:
    """Log broadcast to channel."""
    from bot.config import config

    bot = event.data.get("bot")
    if not bot:
        return

    notif = NotificationService(bot, config.logging.admin_channel_id)
    await notif.log_broadcast_sent(
        sent=event.data.get("sent", 0),
        failed=event.data.get("failed", 0),
    )


# ─── Register all notification listeners ─────────────────────────────────────


def register_notification_listeners():
    """Register all notification event listeners."""
    dispatcher.register(EventType.PAYMENT_SUCCESS, on_payment_success)
    dispatcher.register(EventType.ORDER_DELIVERED, on_gift_delivered)
    dispatcher.register(EventType.ORDER_FAILED, on_gift_failed)
    dispatcher.register(EventType.REFUND_COMPLETED, on_refund_completed)
    dispatcher.register(EventType.GIFT_LINK_OPENED, on_gift_link_opened)
    dispatcher.register(EventType.USER_REGISTERED, on_user_registered)
    dispatcher.register(EventType.BROADCAST_SENT, on_broadcast_sent)
