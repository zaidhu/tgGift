"""Gift Link model."""

import enum
from sqlalchemy import BigInteger, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class GiftLinkStatus(str, enum.Enum):
    PENDING = "pending"
    OPENED = "opened"
    DELIVERED = "delivered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class GiftLink(TimestampMixin, Base):
    __tablename__ = "gift_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    buyer_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recipient_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[GiftLinkStatus] = mapped_column(
        Enum(GiftLinkStatus), default=GiftLinkStatus.PENDING, nullable=False
    )
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="gift_link", lazy="selectin")

    def __repr__(self):
        return f"<GiftLink(token={self.token}, status={self.status})>"
