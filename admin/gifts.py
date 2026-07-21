"""
/gifts - Admin command to whitelist/hide gifts from the catalog.

Usage:
  /gifts list          — Show all available gifts and their visibility
  /gifts hide <id>     — Hide a gift from user catalog
  /gifts show <id>     — Show a gift back in the catalog
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy import select

from models import GiftPricing, BotSetting
from bot.config import config
from services import GiftCatalogService

router = Router()
logger = logging.getLogger(__name__)

HIDDEN_GIFTS_KEY = "hidden_gifts"


class GiftsStates(StatesGroup):
    HIDING = State()
    SHOWING = State()


@router.message(Command("gifts"))
async def cmd_gifts(message: Message, state: FSMContext, **kwargs):
    """Handle /gifts command."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    args = message.get_args() or ""
    parts = args.strip().split()

    if not args or parts[0] == "list":
        await _show_gifts_list(message, kwargs)
    elif parts[0] == "hide":
        if len(parts) < 2:
            await message.answer(
                "Usage: <b>/gifts hide &lt;gift_id&gt;</b>\n\n"
                "Hides a gift from the user catalog.\n"
                "The gift still exists in Telegram but won't show to users.\n\n"
                "Use <code>/gifts list</code> to see gift IDs.",
                parse_mode="HTML",
            )
        else:
            await _hide_gift(message, parts[1], kwargs)
    elif parts[0] == "show":
        if len(parts) < 2:
            await message.answer(
                "Usage: <b>/gifts show &lt;gift_id&gt;</b>\n\n"
                "Shows a previously hidden gift back in the catalog.",
                parse_mode="HTML",
            )
        else:
            await _show_gift(message, parts[1], kwargs)
    else:
        await message.answer(
            "⚙️ <b>Gift Management</b>\n\n"
            "<b>Commands:</b>\n"
            "• <code>/gifts list</code> — Show all gifts & visibility\n"
            "• <code>/gifts hide &lt;id&gt;</code> — Hide from catalog\n"
            "• <code>/gifts show &lt;id&gt;</code> — Show in catalog\n\n"
            "Hidden gifts won't appear for users but still exist in Telegram.",
            parse_mode="HTML",
        )


async def _get_hidden_gifts(session) -> set:
    """Get set of hidden gift IDs from settings."""
    result = await session.execute(
        select(BotSetting).where(BotSetting.key == HIDDEN_GIFTS_KEY)
    )
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        return set(int(x) for x in setting.value.split(",") if x.strip().isdigit())
    return set()


async def _set_hidden_gifts(session, hidden_ids: set):
    """Save hidden gift IDs to settings."""
    result = await session.execute(
        select(BotSetting).where(BotSetting.key == HIDDEN_GIFTS_KEY)
    )
    setting = result.scalar_one_or_none()

    value = ",".join(str(x) for x in sorted(hidden_ids)) if hidden_ids else ""

    if setting:
        setting.value = value
        setting.description = "Comma-separated list of hidden gift IDs"
    else:
        setting = BotSetting(
            key=HIDDEN_GIFTS_KEY,
            value=value,
            description="Comma-separated list of hidden gift IDs",
            is_public=False,
        )
        session.add(setting)

    await session.commit()


async def _show_gifts_list(message: Message, kwargs):
    """Show all gifts with visibility status."""
    session_factory = kwargs.get("session")
    bot = message.bot

    async with session_factory() as session:
        hidden = await _get_hidden_gifts(session)

    catalog = GiftCatalogService(bot)
    gifts = await catalog.get_gifts()

    visible = [g for g in gifts if g["id"] not in hidden]
    hidden_gifts = [g for g in gifts if g["id"] in hidden]

    text = "🎁 <b>Gift Catalog Management</b>\n\n"
    text += f"<b>Visible ({len(visible)}):</b>\n"
    for g in visible[:15]:
        text += f"  • <code>{g['id']}</code> — {g.get('icon', '🎁')} {g['name']} ({g['stars']}⭐)\n"
    if len(visible) > 15:
        text += f"  ...and {len(visible) - 15} more\n"

    if hidden_gifts:
        text += f"\n<b>Hidden ({len(hidden_gifts)}):</b>\n"
        for g in hidden_gifts:
            text += f"  • <code>{g['id']}</code> — {g.get('icon', '🎁')} {g['name']} (hidden)\n"

    text += "\n<i>Use /gifts hide &lt;id&gt; or /gifts show &lt;id&gt;</i>"

    await message.answer(text, parse_mode="HTML")


async def _hide_gift(message: Message, gift_id_str: str, kwargs):
    """Hide a gift from catalog."""
    if not gift_id_str.isdigit():
        await message.answer("⚠️ Gift ID must be a number.")
        return

    gift_id = int(gift_id_str)

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        hidden = await _get_hidden_gifts(session)

        if gift_id in hidden:
            await message.answer("⚠️ This gift is already hidden.")
            return

        hidden.add(gift_id)
        await _set_hidden_gifts(session, hidden)

        # Get gift name for response
        bot = message.bot
        catalog = GiftCatalogService(bot)
        gift = await catalog.get_gift_by_id(gift_id)
        gift_name = gift["name"] if gift else f"Gift #{gift_id}"

    await message.answer(
        f"🚫 <b>Gift Hidden</b>\n\n"
        f"{gift.get('icon', '🎁') if gift else '🎁'} <b>{gift_name}</b> "
        f"has been removed from the user catalog.\n\n"
        f"<i>Use /gifts show {gift_id} to restore it.</i>",
        parse_mode="HTML",
    )


async def _show_gift(message: Message, gift_id_str: str, kwargs):
    """Show a hidden gift back in catalog."""
    if not gift_id_str.isdigit():
        await message.answer("⚠️ Gift ID must be a number.")
        return

    gift_id = int(gift_id_str)

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        hidden = await _get_hidden_gifts(session)

        if gift_id not in hidden:
            await message.answer("⚠️ This gift is not hidden.")
            return

        hidden.discard(gift_id)
        await _set_hidden_gifts(session, hidden)

        # Get gift name
        bot = message.bot
        catalog = GiftCatalogService(bot)
        gift = await catalog.get_gift_by_id(gift_id)
        gift_name = gift["name"] if gift else f"Gift #{gift_id}"

    await message.answer(
        f"✅ <b>Gift Visible</b>\n\n"
        f"{gift.get('icon', '🎁') if gift else '🎁'} <b>{gift_name}</b> "
        f"is now visible to users again.",
        parse_mode="HTML",
    )


async def filter_hidden_gifts(session, gifts: list) -> list:
    """Filter out hidden gifts from the catalog."""
    hidden = await _get_hidden_gifts(session)
    return [g for g in gifts if g["id"] not in hidden]
