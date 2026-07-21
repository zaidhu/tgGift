"""
Cleanup worker - handles expired gift links and stale orders.
"""

import logging
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from services import GiftLinkService
from core.events import dispatcher, Event, EventType
from models import GiftLinkStatus

logger = logging.getLogger(__name__)


async def cleanup_expired_gift_links(session: AsyncSession, bot: Bot) -> int:
    """Expire all expired gift links and notify buyers."""
    link_service = GiftLinkService(session)
    expired_links = await link_service.get_expired_links()

    count = 0
    for link in expired_links:
        await link_service.mark_expired(link.id)

        # Notify buyer
        try:
            await bot.send_message(
                link.buyer_telegram_id,
                f"⏰ <b>Gift Link Expired</b>\n\n"
                f"Your gift link for order #{link.order_id} has expired.\n"
                f"The link was valid for 72 hours.\n\n"
                f"Please create a new gift if you still want to send it.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Failed to notify buyer {link.buyer_telegram_id}: {e}")

        count += 1

    logger.info(f"Cleaned up {count} expired gift links")
    return count
