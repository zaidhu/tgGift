"""
Analytics chart generation service.
Creates matplotlib charts for weekly/daily revenue and order stats.
"""

import logging
import datetime
import io
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PIL import Image

logger = logging.getLogger(__name__)


class AnalyticsChartService:
    """Generates analytics charts as images for Telegram messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_daily_revenue_data(self, days: int = 7) -> list[dict]:
        """Get daily revenue data for the last N days."""
        result = await self.session.execute(text(f"""
            SELECT DATE(created_at) as day, COALESCE(SUM(amount_stars), 0) as revenue
            FROM payments
            WHERE status = 'successful'
            AND created_at >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY DATE(created_at)
            ORDER BY day
        """))
        rows = result.fetchall()

        # Fill in missing days with 0
        today = datetime.date.today()
        data = {}
        for i in range(days):
            day = today - datetime.timedelta(days=i)
            data[day] = 0

        for row in rows:
            data[row[0]] = row[1]

        return [{"date": k, "revenue": v} for k, v in sorted(data.items())]

    async def get_daily_order_data(self, days: int = 7) -> list[dict]:
        """Get daily order counts for the last N days."""
        result = await self.session.execute(text(f"""
            SELECT DATE(created_at) as day, COUNT(*) as orders
            FROM orders
            WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY DATE(created_at)
            ORDER BY day
        """))
        rows = result.fetchall()

        today = datetime.date.today()
        data = {}
        for i in range(days):
            day = today - datetime.timedelta(days=i)
            data[day] = 0

        for row in rows:
            data[row[0]] = row[1]

        return [{"date": k, "orders": v} for k, v in sorted(data.items())]

    async def generate_weekly_report_image(self) -> Optional[bytes]:
        """Generate a combined weekly report chart image."""
        try:
            revenue_data = await self.get_daily_revenue_data(7)
            order_data = await self.get_daily_order_data(7)

            dates = [d["date"] for d in revenue_data]
            revenue = [d["revenue"] for d in revenue_data]
            orders = [d["orders"] for d in order_data]

            # Create figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
            fig.suptitle("tgGift Weekly Report", fontsize=14, fontweight="bold")

            # Revenue chart
            ax1.bar(range(len(dates)), revenue, color="#2196F3", alpha=0.8, label="Revenue (⭐)")
            ax1.set_ylabel("Stars Earned", fontsize=10)
            ax1.set_title("Daily Revenue", fontsize=11)
            ax1.legend(loc="upper right")

            for i, v in enumerate(revenue):
                if v > 0:
                    ax1.text(i, v + 1, f"{int(v)}⭐", ha="center", fontsize=8)

            # Orders chart
            ax2.bar(range(len(dates)), orders, color="#4CAF50", alpha=0.8, label="Orders")
            ax2.set_ylabel("Orders", fontsize=10)
            ax2.set_title("Daily Orders", fontsize=11)

            for i, v in enumerate(orders):
                if v > 0:
                    ax2.text(i, v + 0.2, str(v), ha="center", fontsize=8)

            # Format x-axis
            date_labels = [d.strftime("%b %d") for d in dates]
            plt.xticks(range(len(dates)), date_labels, rotation=45, ha="right")

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                        facecolor="#1a1a2e", edgecolor="none")
            plt.close()
            buf.seek(0)
            return buf.read()

        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return None

    async def generate_profit_chart(self, days: int = 30) -> Optional[bytes]:
        """Generate a profit/revenue split chart."""
        try:
            result = await self.session.execute(text(f"""
                SELECT DATE(o.created_at) as day,
                       COALESCE(SUM(o.gift_stars_price), 0) as total,
                       COALESCE(SUM(o.gift_stars_price - COALESCE(g.base_stars, 0)), 0) as profit
                FROM orders o
                LEFT JOIN gift_pricings g ON o.gift_id = g.gift_id
                WHERE o.status = 'delivered'
                AND o.created_at >= CURRENT_DATE - INTERVAL '{days} days'
                GROUP BY DATE(o.created_at)
                ORDER BY day
            """))
            rows = result.fetchall()

            if not rows:
                return None

            dates = [row[0] for row in rows]
            totals = [row[1] for row in rows]
            profits = [row[2] for row in rows]
            base = [t - p for t, p in zip(totals, profits)]

            fig, ax = plt.subplots(figsize=(8, 5))

            x = range(len(dates))
            width = 0.6
            ax.bar(x, [b for b in base], width, label="Base (to Telegram)", color="#78909C", alpha=0.8)
            ax.bar(x, profits, width, bottom=base, label="Your Profit (fees)", color="#FF9800", alpha=0.8)

            date_labels = [d.strftime("%b %d") for d in dates]
            ax.set_xticks(x)
            ax.set_xticklabels(date_labels, rotation=45, ha="right", fontsize=8)
            ax.set_ylabel("Stars")
            ax.set_title(f"Revenue Breakdown (Last {days} Days)", fontsize=12, fontweight="bold")
            ax.legend()

            # Add totals
            total_revenue = sum(totals)
            total_profit = sum(profits)
            ax.text(0.02, 0.98, f"Total: {int(total_revenue)}⭐ | Profit: {int(total_profit)}⭐",
                    transform=ax.transAxes, fontsize=9, verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                        facecolor="#1a1a2e", edgecolor="none")
            plt.close()
            buf.seek(0)
            return buf.read()

        except Exception as e:
            logger.error(f"Profit chart generation failed: {e}")
            return None
