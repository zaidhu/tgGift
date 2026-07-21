"""
/weekly - Admin weekly analytics report with chart image.
Automatically sends a chart + text summary to admin channel.
"""

import logging
import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputFile
from aiogram.filters import Command

from services import AnalyticsService
from services.analytics_chart import AnalyticsChartService
from bot.config import config
from core.notifications import NotificationService

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("weekly"))
async def cmd_weekly(message: Message, **kwargs):
    """Generate and send weekly analytics report."""
    if not config.admin.is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    await message.answer("📊 Generating weekly report...")

    session_factory = kwargs.get("session")
    bot = message.bot

    async with session_factory() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_summary()

        chart_service = AnalyticsChartService(session)
        chart_bytes = await chart_service.generate_weekly_report_image()
        profit_chart_bytes = await chart_service.generate_profit_chart(30)

    # Build text summary
    text = (
        f"📊 <b>Weekly Report — {datetime.date.today().strftime('%B %d, %Y')}</b>\n\n"
        f"💰 <b>Revenue</b>\n"
        f"   Today: {summary['daily_revenue_stars']} ⭐\n"
        f"   This Month: {summary['monthly_revenue_stars']} ⭐\n"
        f"   All Time: {summary['total_stars_spent']} ⭐\n\n"
        f"📋 <b>Orders</b>\n"
    )
    for status, count in summary.get("orders", {}).items():
        text += f"   {status}: {count}\n"

    text += (
        f"\n📈 <b>Success Rate:</b> {summary['success_rate']}%\n"
        f"👥 <b>Total Users:</b> {summary['total_users']}\n\n"
        f"🔝 <b>Top Gifts:</b>\n"
    )
    for g in summary.get("top_gifts", [])[:5]:
        text += f"   • {g['name']}: {g['count']} orders\n"

    # Send chart first if available
    if chart_bytes:
        from io import BytesIO
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=chart_bytes,
            caption="📈 <b>Weekly Performance</b>",
            parse_mode="HTML",
        )

    # Send profit chart if available
    if profit_chart_bytes:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=profit_chart_bytes,
            caption="💰 <b>Revenue Breakdown (Last 30 Days)</b>\n\n"
                    "<i>Grey = Base price (to Telegram) | Orange = Your profit (fees)</i>",
            parse_mode="HTML",
        )

    # Send text summary
    await message.answer(text, parse_mode="HTML")

    # Also send to admin channel if configured
    if config.admin.channel_id:
        try:
            notification = NotificationService(bot)
            await notification.log_channel(
                message=f"📊 <b>Weekly Report</b>\n{text}",
                parse_mode="HTML",
            )
            if chart_bytes:
                await bot.send_photo(
                    chat_id=int(config.admin.channel_id),
                    photo=chart_bytes,
                    caption="📈 Weekly Performance",
                )
        except Exception as e:
            logger.warning(f"Failed to send weekly report to channel: {e}")


@router.callback_query(F.data == "admin_weekly")
async def cb_admin_weekly(callback: CallbackQuery, **kwargs):
    """Admin panel - weekly report (inline)."""
    if not config.admin.is_admin(callback.from_user.id):
        await callback.answer("⛔ Access denied.", show_alert=True)
        return

    await callback.answer("Generating report...")
    session_factory = kwargs.get("session")
    bot = callback.bot

    async with session_factory() as session:
        analytics = AnalyticsService(session)
        summary = await analytics.get_summary()
        chart_service = AnalyticsChartService(session)
        chart_bytes = await chart_service.generate_weekly_report_image()

    # Send chart
    if chart_bytes:
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=chart_bytes,
            caption="📈 <b>Weekly Performance</b>",
            parse_mode="HTML",
        )

    # Send text
    text = (
        f"📊 <b>Weekly Report — {datetime.date.today().strftime('%B %d, %Y')}</b>\n\n"
        f"💰 Today: {summary['daily_revenue_stars']}⭐ | Month: {summary['monthly_revenue_stars']}⭐\n"
        f"📋 Orders: {summary.get('orders', {})}\n"
        f"📈 Success: {summary['success_rate']}% | 👥 Users: {summary['total_users']}"
    )
    await callback.message.answer(text, parse_mode="HTML")
