"""
Admin panel main entry point.
"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery, **kwargs):
    """Show admin panel main menu."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    text = (
        "🛡️ <b>Admin Panel</b>\n\n"
        "Select an option below:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_pricing")
async def cb_admin_pricing(callback: CallbackQuery, **kwargs):
    """Admin panel - pricing management."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    from sqlalchemy import select
    from models import GiftPricing

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        result = await session.execute(select(GiftPricing).order_by(GiftPricing.gift_id))
        pricings = list(result.scalars().all())

    if not pricings:
        text = (
            "💰 <b>Gift Pricing</b>\n\n"
            "No custom pricing set. All gifts at official Telegram price.\n\n"
            "Use <code>/pricing set &lt;gift_id&gt; &lt;amount&gt;</code> to set fees/discounts."
        )
    else:
        text = "💰 <b>Gift Pricing Adjustments</b>\n\n"
        for p in pricings:
            adj = f"+{p.adjustment}⭐" if p.adjustment >= 0 else f"{p.adjustment}⭐"
            text += f"• {p.gift_name}: {p.base_stars}⭐ → {p.final_price}⭐ ({adj})\n"
        text += "\n<i>Use /pricing set/clear to modify.</i>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "admin_gifts")
async def cb_admin_gifts(callback: CallbackQuery, **kwargs):
    """Admin panel - gift visibility management."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    from services import GiftCatalogService
    from admin.gifts import _get_hidden_gifts

    session_factory = kwargs.get("session")
    bot = callback.bot

    async with session_factory() as session:
        hidden = await _get_hidden_gifts(session)

    catalog = GiftCatalogService(bot)
    gifts = await catalog.get_gifts()
    visible = [g for g in gifts if g["id"] not in hidden]
    hidden_gifts = [g for g in gifts if g["id"] in hidden]

    text = f"🎁 <b>Gift Catalog ({len(gifts)} total)</b>\n\n"
    text += f"✅ Visible: {len(visible)}\n"
    text += f"🚫 Hidden: {len(hidden_gifts)}\n\n"

    if hidden_gifts:
        text += "<b>Hidden Gifts:</b>\n"
        for g in hidden_gifts[:10]:
            text += f"  • {g.get('icon', '🎁')} {g['name']} (ID: {g['id']})\n"
        if len(hidden_gifts) > 10:
            text += f"  ...and {len(hidden_gifts) - 10} more\n"
    else:
        text += "<i>All gifts are visible to users.</i>"

    text += "\n<i>Use /gifts hide/show to manage visibility.</i>"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()
