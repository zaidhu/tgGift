"""
Main bot entry point.
Initializes the bot, registers handlers, and starts polling.
"""

import asyncio
import logging
import sys

import structlog
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from bot.config import config
from bot.middleware.auth import AuthMiddleware
from bot.middleware.logging import LoggingMiddleware
from bot.handlers import (
    start_router,
    select_gift_router,
    custom_message_router,
    recipient_router,
    payment_router,
    confirmation_router,
)
from admin import (
    stats_router,
    orders_router,
    users_router,
    payments_router,
    refunds_router,
    broadcast_router,
    system_router,
    settings_router,
    search_router,
    pricing_router,
    gifts_router,
    weekly_report_router,
)
from admin.panel import router as admin_panel_router
from core.listeners import register_all_listeners
from models.base import Base

logger = logging.getLogger(__name__)


async def setup_database():
    """Create database tables."""
    engine = create_async_engine(config.database.url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    logger.info("Database tables created")


def setup_logging():
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def main():
    """Main entry point."""
    setup_logging()
    logger.info("Starting tgGift bot...")

    # Validate config
    if not config.bot.token:
        logger.error("BOT_TOKEN is not set in environment variables")
        sys.exit(1)

    if not config.bot.username:
        logger.warning("BOT_USERNAME is not set - some features may not work correctly")

    # Setup database
    await setup_database()

    # Initialize bot and dispatcher
    bot = Bot(token=config.bot.token)
    storage = MemoryStorage()

    # Use Redis storage if available
    if config.redis.url:
        try:
            storage = RedisStorage.from_url(config.redis.url)
            logger.info("Redis storage connected")
        except Exception as e:
            logger.warning(f"Redis not available, using memory storage: {e}")

    dp = Dispatcher(storage=storage)

    # Create session factory
    engine = create_async_engine(config.database.url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Register middleware
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(AuthMiddleware(session_factory))

    # Register all routers
    dp.include_router(start_router)
    dp.include_router(select_gift_router)
    dp.include_router(custom_message_router)
    dp.include_router(recipient_router)
    dp.include_router(payment_router)
    dp.include_router(confirmation_router)

    # Admin routers
    dp.include_router(admin_panel_router)
    dp.include_router(stats_router)
    dp.include_router(orders_router)
    dp.include_router(users_router)
    dp.include_router(payments_router)
    dp.include_router(refunds_router)
    dp.include_router(broadcast_router)
    dp.include_router(system_router)
    dp.include_router(settings_router)
    dp.include_router(search_router)
    dp.include_router(pricing_router)
    dp.include_router(gifts_router)
    dp.include_router(weekly_report_router)

    # Register event listeners
    register_all_listeners(bot)

    # Set bot commands
    from aiogram.types import BotCommand, BotCommandScopeDefault
    commands = [
        BotCommand(command="start", description="🎁 Start the bot"),
        BotCommand(command="menu", description="🏠 Show main menu"),
        BotCommand(command="stats", description="📊 View statistics (admin)"),
        BotCommand(command="orders", description="📋 View orders (admin)"),
        BotCommand(command="users", description="👥 View users (admin)"),
        BotCommand(command="payments", description="💰 View payments (admin)"),
        BotCommand(command="refunds", description="💸 Manage refunds (admin)"),
        BotCommand(command="broadcast", description="📡 Send broadcast (admin)"),
        BotCommand(command="system", description="⚙️ System status (admin)"),
        BotCommand(command="settings", description="⚙️ Bot settings (admin)"),
        BotCommand(command="search", description="🔍 Search orders (admin)"),
        BotCommand(command="retry", description="🔄 Retry failed order (admin)"),
        BotCommand(command="pricing", description="💰 Set gift fees/discounts (admin)"),
        BotCommand(command="gifts", description="🎁 Manage gift catalog visibility (admin)"),
        BotCommand(command="weekly", description="📈 Weekly analytics report (admin)"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

    # Start polling
    logger.info(f"Bot started as @{config.bot.username or 'Unknown'}")
    try:
        await dp.start_polling(bot, session_factory=session_factory)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
