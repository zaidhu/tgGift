"""Transaction (ledger) model for auditable finance tracking."""

import enum
from sqlalchemy import BigInteger, Integer, String, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class TransactionType(str, enum.Enum):
    PAYMENT_IN = "payment_in"
    REFUND_OUT = "refund_out"
    SYSTEM_ADJUSTMENT = "system_adjustment"


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("orders.id"), nullable=True)
    payment_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payments.id"), nullable=True)
    refund_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("refunds.id"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<Transaction(id={self.id}, type={self.type}, amount={self.amount_stars})>"
