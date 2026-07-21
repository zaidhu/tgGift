"""
Application configuration loaded from environment variables.
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class BotConfig:
    """Telegram bot configuration."""

    token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    username: str = field(default_factory=lambda: os.getenv("BOT_USERNAME", ""))
    api_id: int = field(default_factory=lambda: int(os.getenv("API_ID", "0") or "0"))
    api_hash: str = field(default_factory=lambda: os.getenv("API_HASH", ""))


@dataclass(frozen=True)
class AdminConfig:
    """Admin configuration."""

    admin_ids: list[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_ID", "").split(",") if x.strip().isdigit()
    ])
    owner_id: int = field(default_factory=lambda: int(os.getenv("OWNER_ID", "0") or "0"))

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids or user_id == self.owner_id


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration."""

    url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/tggift"
    ))


@dataclass(frozen=True)
class RedisConfig:
    """Redis configuration."""

    url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""

    admin_channel_id: int = field(default_factory=lambda: int(
        os.getenv("ADMIN_CHANNEL_ID", "0") or "0"
    ))


@dataclass(frozen=True)
class PaymentConfig:
    """Payment configuration."""

    currency: str = field(default_factory=lambda: os.getenv("PAYMENT_CURRENCY", "stars"))


@dataclass(frozen=True)
class AppConfig:
    """Root application configuration."""

    bot: BotConfig = field(default_factory=BotConfig)
    admin: AdminConfig = field(default_factory=AdminConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    payment: PaymentConfig = field(default_factory=PaymentConfig)
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))


# Singleton config instance
config = AppConfig()
