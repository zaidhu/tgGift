"""
Confirmation handler.
Handles gift link opening by recipient and final confirmation.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from services import GiftLinkService
from core.events import dispatcher, Event, EventType
from models import GiftLinkStatus, OrderStatus

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart(deep_link=True))
async def cmd_deep_link(message: Message, state, **kwargs):
    """Handle deep link: /start gift_TOKEN"""
    from sqlalchemy.ext.asyncio import AsyncSession

    args = message.get_args()
    if not args or not args.startswith("gift_"):
        # Regular /start
        return

    token = args.replace("gift_", "")
    session_factory = kwargs.get("session")
    bot = message.bot

    async with session_factory() as session:
        link_service = GiftLinkService(session)
        gift_link = await link_service.get_gift_link_by_token(token)

        if not gift_link:
            await message.answer(
                "⚠️ <b>Invalid or Expired Gift Link</b>\n\n"
                "This gift link is no longer valid. "
                "Please ask the sender to create a new one.",
                parse_mode="HTML",
            )
            return

        if gift_link.status.value == "expired":
            await message.answer(
                "⏰ <b>This Gift Link Has Expired</b>\n\n"
                "Gift links expire after 72 hours. "
                "Please ask the sender to create a new one.",
                parse_mode="HTML",
            )
            return

        if gift_link.status.value == "delivered":
            await message.answer(
                "✅ <b>This Gift Has Already Been Delivered!</b>\n\n"
                "Check your Telegram gifts collection.",
                parse_mode="HTML",
            )
            return

        if gift_link.status.value == "cancelled":
            await message.answer(
                "🚫 <b>This Gift Has Been Cancelled</b>",
                parse_mode="HTML",
            )
            return

        # Mark as opened
        gift_link = await link_service.mark_opened(
            link_id=gift_link.id,
            recipient_telegram_id=message.from_user.id,
        )

        # Emit gift link opened event
        await dispatcher.emit(Event(
            type=EventType.GIFT_LINK_OPENED,
            data={
                "bot": bot,
                "buyer_telegram_id": gift_link.buyer_telegram_id,
                "order_id": gift_link.order_id,
            }
        ))

        # Get order details
        from models import Order
        order = await session.get(Order, gift_link.order_id)

        if order:
            # Try to deliver the gift now
            from services import TelegramAPIService
            api = TelegramAPIService(bot)

            success = await api.send_gift_to_user(
                recipient_id=message.from_user.id,
                gift_id=order.gift_id or 0,
                custom_message=order.custom_message,
            )

            if success:
                await link_service.mark_delivered(gift_link.id)
                order.status = OrderStatus.DELIVERED

                # Emit delivery event
                await dispatcher.emit(Event(
                    type=EventType.ORDER_DELIVERED,
                    data={
                        "bot": bot,
                        "telegram_id": order.telegram_id,
                        "order_id": order.id,
                        "recipient": message.from_user.id,
                    }
                ))

                await message.answer(
                    "🎁 <b>You've Received a Gift!</b>\n\n"
                    f"From: Order #{order.id}\n"
                    f"Gift: {order.gift_name}\n\n"
                    "Check your Telegram gifts collection to view it!"
                    + (f"\n\n📝 Message: {order.custom_message}" if order.custom_message else ""),
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    "⏳ <b>Almost there!</b>\n\n"
                    "Your gift is being processed. You'll receive it shortly.",
                    parse_mode="HTML",
                )

        await session.commit()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state, **kwargs):
    """Cancel the current operation."""
    await state.clear()

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Send a Gift", callback_data="gift_catalog")],
        [InlineKeyboardButton(text="📋 My Orders", callback_data="my_orders")],
    ])

    await callback.message.edit_text(
        "❌ <b>Operation Cancelled</b>\n\nWhat would you like to do?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    await callback.answer()
