"""Referral model (future stub)."""

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class Referral(TimestampMixin, Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    referred_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    referral_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    reward_stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_claimed: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self):
        return f"<Referral(code={self.referral_code})>"
