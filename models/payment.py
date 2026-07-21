"""Payment model."""

import enum
from sqlalchemy import BigInteger, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    invoice_id: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="stars", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    provider_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_order_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped["Order"] = relationship("Order", back_populates="payment", lazy="selectin")

    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount_stars} stars, status={self.status})>"
