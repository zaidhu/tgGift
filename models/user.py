"""User model."""

import enum
from sqlalchemy import BigInteger, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[UserStatus] = mapped_column(String(20), default=UserStatus.ACTIVE, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent_stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    orders: Mapped[list] = relationship("Order", back_populates="buyer", lazy="selectin")

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
