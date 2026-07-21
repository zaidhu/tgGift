"""
Weekly auto-report worker.
Sends weekly analytics report to admin channel every Monday at 9 AM.
"""

import logging
import datetime
from aiogram import Bot

logger = logging.getLogger(__name__)


async def send_weekly_report(session_factory, bot: Bot):
    """Generate and send weekly report to admin channel."""
    from bot.config import config
    from services.analytics_chart import AnalyticsChartService

    if not config.admin.channel_id:
        logger.debug("No admin channel configured, skipping weekly report")
        return

    try:
        async with session_factory() as session:
            from services import AnalyticsService
            analytics = AnalyticsService(session)
            summary = await analytics.get_summary()

            chart_service = AnalyticsChartService(session)
            chart_bytes = await chart_service.generate_weekly_report_image()
            profit_chart_bytes = await chart_service.generate_profit_chart(30)

        channel_id = int(config.admin.channel_id)

        # Send revenue chart
        if chart_bytes:
            await bot.send_photo(
                chat_id=channel_id,
                photo=chart_bytes,
                caption="📈 <b>Weekly Report</b>",
                parse_mode="HTML",
            )

        # Send profit chart
        if profit_chart_bytes:
            await bot.send_photo(
                chat_id=channel_id,
                photo=profit_chart_bytes,
                caption="💰 <b>Revenue Breakdown (Last 30 Days)</b>\n\n"
                        "<i>Grey = Base price | Orange = Your profit (fees)</i>",
                parse_mode="HTML",
            )

        # Send text summary
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

        await bot.send_message(channel_id, text, parse_mode="HTML")
        logger.info("Weekly report sent to admin channel")

    except Exception as e:
        logger.error(f"Failed to send weekly report: {e}")

        # Alert admin DM
        from core.notifications import NotificationService
        notif = NotificationService(bot, config.logging.admin_channel_id, config.admin.owner_id)
        await notif.alert_system_failure(
            component="Weekly Report",
            error=str(e),
        )


async def run_weekly_report_worker(session_factory, bot: Bot):
    """Periodic weekly report worker."""
    import asyncio

    last_report_date = None

    while True:
        now = datetime.datetime.now()

        # Send on Monday at 9 AM (or any day > last report)
        if now.weekday() == 0 and now.hour == 9:  # Monday 9 AM
            report_date = now.date()
            if report_date != last_report_date:
                await send_weekly_report(session_factory, bot)
                last_report_date = report_date

        await asyncio.sleep(600)  # Check every 10 minutes
