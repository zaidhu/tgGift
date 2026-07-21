"""
Retry worker - retries failed gift deliveries.
"""

import logging
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Order, OrderStatus, QueueJob, JobType, JobStatus
from services import TelegramAPIService, RefundService, GiftLinkService
from core.events import dispatcher, Event, EventType

logger = logging.getLogger(__name__)


async def retry_failed_delivery(session: AsyncSession, bot: Bot, order_id: int) -> None:
    """Retry a failed gift delivery."""
    order = await session.get(Order, order_id)
    if not order:
        logger.warning(f"Order {order_id} not found for retry")
        return

    if order.status != OrderStatus.FAILED:
        logger.info(f"Order {order_id} is not in failed state, skipping retry")
        return

    order.status = OrderStatus.PROCESSING
    await session.commit()

    api = TelegramAPIService(bot)
    recipient_id = order.recipient_telegram_id

    if not recipient_id:
        # Gift link method - check if link is still pending
        link_service = GiftLinkService(session)
        if order.gift_link_token:
            gift_link = await link_service.get_gift_link_by_token(order.gift_link_token)
            if gift_link and gift_link.status.value == "opened":
                # Try delivery again
                success = await api.send_gift_to_user(
                    recipient_id=gift_link.recipient_telegram_id or 0,
                    gift_id=order.gift_id or 0,
                    custom_message=order.custom_message,
                )
                if success:
                    await link_service.mark_delivered(gift_link.id)
                    order.status = OrderStatus.DELIVERED
                    await session.commit()
                    await dispatcher.emit(Event(
                        type=EventType.ORDER_DELIVERED,
                        data={"bot": bot, "telegram_id": order.telegram_id, "order_id": order.id, "recipient": gift_link.recipient_telegram_id}
                    ))
                    return
        order.status = OrderStatus.FAILED
        await session.commit()
        return

    success = await api.send_gift_to_user(
        recipient_id=recipient_id,
        gift_id=order.gift_id or 0,
        custom_message=order.custom_message,
    )

    if success:
        order.status = OrderStatus.DELIVERED
        await session.commit()
        await dispatcher.emit(Event(
            type=EventType.ORDER_DELIVERED,
            data={"bot": bot, "telegram_id": order.telegram_id, "order_id": order.id, "recipient": recipient_id}
        ))
    else:
        order.status = OrderStatus.FAILED
        await session.commit()
        # Auto-create refund after final retry failure
        refund_service = RefundService(session)
        await refund_service.auto_create_refund(order_id=order.id, reason="Retry delivery failed")
        await session.commit()

    logger.info(f"Retry complete for order {order_id}: {order.status.value}")
