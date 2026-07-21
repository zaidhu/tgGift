"""Analytics snapshot model for daily/monthly aggregation."""

import enum
from sqlalchemy import BigInteger, Integer, String, Date, Enum
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class AnalyticsPeriod(str, enum.Enum):
    DAILY = "daily"
    MONTHLY = "monthly"


class AnalyticsSnapshot(TimestampMixin, Base):
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period: Mapped[AnalyticsPeriod] = mapped_column(Enum(AnalyticsPeriod), nullable=False)
    period_date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)

    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_revenue_stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_refunds_stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unique_buyers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(default=0.0, nullable=False)

    def __repr__(self):
        return f"<AnalyticsSnapshot(period={self.period}, date={self.period_date})>"
