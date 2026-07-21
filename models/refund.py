"""Refund model."""

import enum
from sqlalchemy import BigInteger, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Refund(TimestampMixin, Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    payment_id: Mapped[int] = mapped_column(Integer, ForeignKey("payments.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[RefundStatus] = mapped_column(
        Enum(RefundStatus), default=RefundStatus.PENDING, nullable=False
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    def __repr__(self):
        return f"<Refund(id={self.id}, order={self.order_id}, status={self.status})>"
