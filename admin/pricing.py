"""
/pricing - Admin command to set fee/discount on specific gifts.

Usage:
  /pricing list                    — Show all pricing adjustments
  /pricing set <gift_id> <amount>  — Set fee/discount on a gift
  /pricing clear <gift_id>         — Remove adjustment (back to official price)

Examples:
  /pricing set 5 +2                — Bear gets +2 stars fee (17 → 19⭐)
  /pricing set 5 -1                — Bear gets -1 stars discount (17 → 16⭐)
  /pricing clear 5                 — Bear back to official 17⭐
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from models import GiftPricing
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


class PricingStates(StatesGroup):
    SETTING_ADJUSTMENT = State()


@router.message(Command("pricing"))
async def cmd_pricing(message: Message, state: FSMContext, **kwargs):
    """Show pricing management help or handle subcommands."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    args = message.get_args() or ""
    parts = args.strip().split()

    if not args or parts[0] == "list":
        await _show_pricing_list(message, kwargs)
    elif parts[0] == "set":
        if len(parts) < 3:
            await message.answer(
                "Usage: <b>/pricing set &lt;gift_id&gt; &lt;amount&gt;</b>\n\n"
                "Examples:\n"
                "• <code>/pricing set 5 +2</code> — Add 2⭐ fee\n"
                "• <code>/pricing set 5 -1</code> — Give 1⭐ discount\n"
                "• <code>/pricing set 5 3</code> — Add 3⭐ fee\n\n"
                "Positive = fee (increases price)\n"
                "Negative = discount (decreases price)\n"
                "Use <code>/pricing clear &lt;gift_id&gt;</code> to remove adjustment",
                parse_mode="HTML",
            )
        else:
            await _set_pricing(message, parts[1], parts[2], kwargs)
    elif parts[0] == "clear":
        if len(parts) < 2:
            await message.answer("Usage: <b>/pricing clear &lt;gift_id&gt;</b>", parse_mode="HTML")
        else:
            await _clear_pricing(message, parts[1], kwargs)
    else:
        await message.answer(
            "⚙️ <b>Pricing Management</b>\n\n"
            "<b>Commands:</b>\n"
            "• <code>/pricing list</code> — Show all adjustments\n"
            "• <code>/pricing set &lt;gift_id&gt; &lt;amount&gt;</code> — Set fee/discount\n"
            "• <code>/pricing clear &lt;gift_id&gt;</code> — Remove adjustment\n\n"
            "<b>Examples:</b>\n"
            "• <code>/pricing set 5 +2</code> — Bear gets +2⭐ fee\n"
            "• <code>/pricing set 5 -1</code> — Bear gets 1⭐ discount\n\n"
            "<i>Official TG price stays the same. You only add/remove on top.</i>",
            parse_mode="HTML",
        )


async def _show_pricing_list(message: Message, kwargs):
    """Show all pricing adjustments."""
    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(select(GiftPricing).order_by(GiftPricing.gift_id))
        pricings = list(result.scalars().all())

    if not pricings:
        await message.answer(
            "💰 <b>Gift Pricing</b>\n\n"
            "No custom pricing set. All gifts are at official Telegram price.\n\n"
            "Use <code>/pricing set &lt;gift_id&gt; &lt;amount&gt;</code> to set a fee or discount.",
            parse_mode="HTML",
        )
        return

    text = "💰 <b>Gift Pricing Adjustments</b>\n\n"
    text += f"{'Gift':<20} | {'Official':<10} | {'Adj':<12} | {'Final':<10}\n"
    text += "─" * 56 + "\n"

    for p in pricings:
        adj = f"+{p.adjustment}⭐ fee" if p.adjustment > 0 else (f"{p.adjustment}⭐ disc" if p.adjustment < 0 else "none")
        text += f"{p.gift_name:<20} | {p.base_stars:<10} | {adj:<12} | {p.final_price}⭐\n"

    await message.answer(text, parse_mode="HTML")


async def _set_pricing(message: Message, gift_id_str: str, amount_str: str, kwargs):
    """Set a fee or discount on a gift."""
    # Parse gift ID
    if not gift_id_str.isdigit():
        await message.answer("⚠️ Gift ID must be a number.")
        return

    gift_id = int(gift_id_str)

    # Parse amount
    amount = amount_str.replace("+", "")
    if not amount.lstrip("-").isdigit():
        await message.answer("⚠️ Amount must be a number (e.g., +2, -1, 3)")
        return

    adjustment = int(amount)

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        # Fetch current gift price from catalog
        from services import GiftCatalogService
        catalog = GiftCatalogService(message.bot)
        gift = await catalog.get_gift_by_id(gift_id)

        base_price = gift["stars"] if gift else 0
        gift_name = gift["name"] if gift else f"Gift #{gift_id}"

        # Upsert pricing
        result = await session.execute(
            select(GiftPricing).where(GiftPricing.gift_id == gift_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.adjustment = adjustment
            existing.base_stars = base_price
            existing.updated_by = message.from_user.id
        else:
            pricing = GiftPricing(
                gift_id=gift_id,
                gift_name=gift_name,
                base_stars=base_price,
                adjustment=adjustment,
                updated_by=message.from_user.id,
            )
            session.add(pricing)

        await session.commit()

    # Format response
    if adjustment > 0:
        adj_text = f"+{adjustment} ⭐ fee"
    elif adjustment < 0:
        adj_text = f"{adjustment} ⭐ discount"
    else:
        adj_text = "no change"

    final_price = max(1, base_price + adjustment)

    await message.answer(
        f"✅ <b>Pricing Updated</b>\n\n"
        f"🎁 <b>{gift_name}</b>\n"
        f"📋 Official price: {base_price} ⭐\n"
        f"⚙️ Adjustment: {adj_text}\n"
        f"💰 Users pay: {final_price} ⭐",
        parse_mode="HTML",
    )


async def _clear_pricing(message: Message, gift_id_str: str, kwargs):
    """Remove pricing adjustment (back to official price)."""
    if not gift_id_str.isdigit():
        await message.answer("⚠️ Gift ID must be a number.")
        return

    gift_id = int(gift_id_str)

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(
            select(GiftPricing).where(GiftPricing.gift_id == gift_id)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            await message.answer(f"No custom pricing found for gift ID {gift_id}.")
            return

        gift_name = existing.gift_name
        await session.delete(existing)
        await session.commit()

    await message.answer(
        f"🔄 <b>Pricing Cleared</b>\n\n"
        f"🎁 <b>{gift_name}</b> is now at official Telegram price.\n\n"
        f"No fee or discount applied.",
        parse_mode="HTML",
    )
