"""Wishlist model (future stub)."""

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class Wishlist(TimestampMixin, Base):
    __tablename__ = "wishlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(default=True, nullable=False)

    def __repr__(self):
        return f"<Wishlist(id={self.id}, user={self.telegram_id})>"


class WishlistItem(TimestampMixin, Base):
    __tablename__ = "wishlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wishlist_id: Mapped[int] = mapped_column(Integer, nullable=False)
    gift_name: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_fulfilled: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self):
        return f"<WishlistItem(id={self.id}, gift={self.gift_name})>"
