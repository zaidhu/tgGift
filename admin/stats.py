"""
/stats - Admin analytics and statistics.
"""

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from services import AnalyticsService
from bot.config import config
from bot.keyboards.order_actions import admin_main_keyboard

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("stats"))
async def cmd_stats(message: Message, **kwargs):
    """Show platform statistics."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    session_factory = kwargs.get("session")
    async with session_factory() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_summary()

    text = (
        "📊 <b>Platform Statistics</b>\n\n"
        f"💰 <b>Revenue</b>\n"
        f"   Today: {summary['daily_revenue_stars']} ⭐\n"
        f"   This Month: {summary['monthly_revenue_stars']} ⭐\n"
        f"   All Time: {summary['total_stars_spent']} ⭐\n\n"
        f"📋 <b>Orders</b>\n"
    )
    for status, count in summary.get("orders", {}).items():
        text += f"   {status}: {count}\n"

    text += (
        f"\n💸 <b>Refunds</b>\n"
    )
    for status, count in summary.get("refunds", {}).items():
        text += f"   {status}: {count}\n"

    text += (
        f"\n📈 <b>Success Rate:</b> {summary['success_rate']}%\n"
        f"👥 <b>Total Users:</b> {summary['total_users']}\n"
        f"📆 <b>New Users Today:</b> {summary['daily_new_users']}\n"
    )

    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery, **kwargs):
    """Admin panel - stats view (inline)."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    # Reuse the stats command logic
    session_factory = kwargs.get("session")
    async with session_factory() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_summary()

    text = (
        "📊 <b>Platform Statistics</b>\n\n"
        f"💰 <b>Revenue</b>\n"
        f"   Today: {summary['daily_revenue_stars']} ⭐\n"
        f"   This Month: {summary['monthly_revenue_stars']} ⭐\n"
        f"   All Time: {summary['total_stars_spent']} ⭐\n\n"
        f"📋 <b>Orders</b>\n"
    )
    for status, count in summary.get("orders", {}).items():
        text += f"   {status}: {count}\n"

    text += (
        f"\n💸 <b>Refunds</b>\n"
    )
    for status, count in summary.get("refunds", {}).items():
        text += f"   {status}: {count}\n"

    text += (
        f"\n📈 <b>Success Rate:</b> {summary['success_rate']}%\n"
        f"👥 <b>Total Users:</b> {summary['total_users']}\n"
        f"📆 <b>New Users Today:</b> {summary['daily_new_users']}\n"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_main_keyboard())
    await callback.answer()
