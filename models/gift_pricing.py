"""Gift pricing model - per-gift fee/discount adjustments."""

from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .base import Base


class GiftPricing(Base):
    __tablename__ = "gift_pricing"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    gift_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    gift_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_stars: Mapped[int] = mapped_column(Integer, nullable=False)  # Official TG price
    adjustment: Mapped[int] = mapped_column(Integer, default=0)  # +fee or -discount in stars
    updated_by: Mapped[int] = mapped_column(Integer, nullable=False)  # Admin Telegram ID
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def final_price(self) -> int:
        """Calculate the final price users pay."""
        return max(1, self.base_stars + self.adjustment)

    @property
    def adjustment_label(self) -> str:
        """Human-readable adjustment label."""
        if self.adjustment > 0:
            return f"+{self.adjustment} ⭐ fee"
        elif self.adjustment < 0:
            return f"{self.adjustment} ⭐ discount"
        else:
            return "No adjustment"

    def __repr__(self):
        return f"<GiftPricing(gift_id={self.gift_id}, final={self.final_price}⭐)>"
