"""Loyalty model (future stub)."""

from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class LoyaltyPoint(TimestampMixin, Base):
    __tablename__ = "loyalty_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<LoyaltyPoint(user={self.telegram_id}, points={self.points})>"
