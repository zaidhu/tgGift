"""Order model."""

import enum
from sqlalchemy import BigInteger, Integer, String, Text, Enum, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    WAITING_PAYMENT = "waiting_payment"
    PAID = "paid"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    REFUND_PENDING = "refund_pending"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class RecipientMethod(str, enum.Enum):
    USER_ID = "user_id"
    FORWARD = "forward"
    CONTACT = "contact"
    GIFT_LINK = "gift_link"


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    # Gift details
    gift_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gift_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gift_stars_price: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Recipient
    recipient_method: Mapped[RecipientMethod | None] = mapped_column(
        Enum(RecipientMethod), nullable=True
    )
    recipient_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    recipient_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Custom message
    custom_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Payment
    payment_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payment_telegram_payment_charge_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Gift link (for gift_link method)
    gift_link_token: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    # Refund reference
    refund_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("refunds.id"), nullable=True)

    # Error info
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    buyer: Mapped["User"] = relationship("User", back_populates="orders", lazy="selectin")
    payment: Mapped["Payment | None"] = relationship("Payment", back_populates="order", lazy="selectin")
    gift_link: Mapped["GiftLink | None"] = relationship("GiftLink", back_populates="order", lazy="selectin")

    def __repr__(self):
        return f"<Order(id={self.id}, status={self.status}, buyer={self.telegram_id})>"
