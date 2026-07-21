"""
Analytics service.
Provides statistics, revenue tracking, and growth metrics.
"""

import logging
import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from models import (
    Order, OrderStatus, Payment, PaymentStatus,
    Refund, RefundStatus, User, Transaction,
    AnalyticsSnapshot, AnalyticsPeriod,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Provides analytics and statistics for the platform."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_daily_revenue(self) -> int:
        """Get today's revenue in stars."""
        result = await self.session.execute(text("""
            SELECT COALESCE(SUM(amount_stars), 0)
            FROM payments
            WHERE status = 'successful'
            AND created_at >= CURRENT_DATE
        """))
        return result.scalar() or 0

    async def get_monthly_revenue(self) -> int:
        """Get this month's revenue in stars."""
        result = await self.session.execute(text("""
            SELECT COALESCE(SUM(amount_stars), 0)
            FROM payments
            WHERE status = 'successful'
            AND created_at >= date_trunc('month', CURRENT_DATE)
        """))
        return result.scalar() or 0

    async def get_total_stars_spent(self) -> int:
        """Get total stars spent (all-time)."""
        result = await self.session.execute(text("""
            SELECT COALESCE(SUM(amount_stars), 0)
            FROM payments
            WHERE status = 'successful'
        """))
        return result.scalar() or 0

    async def get_order_count(self) -> dict:
        """Get order counts by status."""
        result = await self.session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM orders
            GROUP BY status
        """))
        return {row[0]: row[1] for row in result.fetchall()}

    async def get_refund_count(self) -> dict:
        """Get refund counts by status."""
        result = await self.session.execute(text("""
            SELECT status, COUNT(*) as count
            FROM refunds
            GROUP BY status
        """))
        return {row[0]: row[1] for row in result.fetchall()}

    async def get_success_rate(self) -> float:
        """Get delivery success rate."""
        total_result = await self.session.execute(text("""
            SELECT COUNT(*) FROM orders
            WHERE status IN ('delivered', 'failed', 'refunded')
        """))
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        success_result = await self.session.execute(text("""
            SELECT COUNT(*) FROM orders WHERE status = 'delivered'
        """))
        success = success_result.scalar() or 0

        return round(success / total * 100, 2)

    async def get_top_gifts(self, limit: int = 10) -> list[dict]:
        """Get top gifts by order count."""
        result = await self.session.execute(text(f"""
            SELECT gift_name, COUNT(*) as count, COALESCE(SUM(g.stars), 0) as total_stars
            FROM orders o
            LEFT JOIN (
                SELECT id, 'X' as stars FROM orders LIMIT 1
            ) g ON o.gift_id = g.id
            WHERE o.status = 'delivered'
            GROUP BY o.gift_name
            ORDER BY count DESC
            LIMIT {limit}
        """))
        return [{"name": row[0], "count": row[1], "stars": row[2]} for row in result.fetchall()]

    async def get_top_buyers(self, limit: int = 10) -> list[dict]:
        """Get top buyers by spending."""
        result = await self.session.execute(text(f"""
            SELECT telegram_id, COUNT(*) as orders, COALESCE(SUM(p.amount_stars), 0) as total_spent
            FROM orders o
            JOIN payments p ON o.id = p.order_id
            WHERE p.status = 'successful'
            GROUP BY o.telegram_id
            ORDER BY total_spent DESC
            LIMIT {limit}
        """))
        return [{"telegram_id": row[0], "orders": row[1], "spent": row[2]} for row in result.fetchall()]

    async def get_total_users(self) -> int:
        """Get total registered users."""
        result = await self.session.execute(
            select(func.count(User.id))
        )
        return result.scalar() or 0

    async def get_daily_users(self) -> int:
        """Get users who joined today."""
        result = await self.session.execute(text("""
            SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE
        """))
        return result.scalar() or 0

    async def create_daily_snapshot(self) -> None:
        """Create a daily analytics snapshot."""
        today = datetime.date.today()

        # Check if snapshot already exists
        existing = await self.session.execute(
            select(AnalyticsSnapshot).where(
                AnalyticsSnapshot.period == AnalyticsPeriod.DAILY,
                AnalyticsSnapshot.period_date == today,
            )
        )
        if existing.scalar_one_or_none():
            logger.debug("Daily snapshot already exists")
            return

        order_counts = await self.get_order_count()
        revenue = await self.get_daily_revenue()
        refund_counts = await self.get_refund_count()

        snapshot = AnalyticsSnapshot(
            period=AnalyticsPeriod.DAILY,
            period_date=today,
            total_orders=order_counts.get("delivered", 0) + order_counts.get("failed", 0),
            successful_orders=order_counts.get("delivered", 0),
            failed_orders=order_counts.get("failed", 0),
            total_revenue_stars=revenue,
            total_refunds_stars=refund_counts.get("completed", 0),
            unique_buyers=await self.get_daily_users(),
            success_rate=await self.get_success_rate(),
        )
        self.session.add(snapshot)
        await self.session.commit()
        logger.info(f"Daily analytics snapshot created for {today}")

    async def get_summary(self) -> dict:
        """Get a complete analytics summary."""
        return {
            "daily_revenue_stars": await self.get_daily_revenue(),
            "monthly_revenue_stars": await self.get_monthly_revenue(),
            "total_stars_spent": await self.get_total_stars_spent(),
            "orders": await self.get_order_count(),
            "refunds": await self.get_refund_count(),
            "success_rate": await self.get_success_rate(),
            "total_users": await self.get_total_users(),
            "daily_new_users": await self.get_daily_users(),
            "top_gifts": await self.get_top_gifts(),
            "top_buyers": await self.get_top_buyers(),
        }
