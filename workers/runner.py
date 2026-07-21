"""
Worker runner - main entry point for background workers.
Uses ARQ for async Redis queue processing.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Worker settings
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
POLL_INTERVAL = 10  # seconds


async def run_cleanup_worker(session_factory, bot):
    """Periodic cleanup worker."""
    from workers.cleanup_worker import cleanup_expired_gift_links

    while True:
        try:
            async with session_factory() as session:
                await cleanup_expired_gift_links(session, bot)
            logger.debug("Cleanup cycle complete")
        except Exception as e:
            logger.error(f"Cleanup worker error: {e}")
        await asyncio.sleep(POLL_INTERVAL)


async def run_retry_worker(session_factory, bot):
    """Periodic retry worker."""
    from models import QueueJob, JobType, JobStatus
    from sqlalchemy import select

    while True:
        try:
            async with session_factory() as session:
                # Get pending retry jobs
                result = await session.execute(
                    select(QueueJob)
                    .where(
                        QueueJob.job_type == JobType.RETRY_DELIVERY,
                        QueueJob.status == JobStatus.PENDING,
                    )
                    .limit(5)
                )
                jobs = list(result.scalars().all())

                for job in jobs:
                    if job.reference_id:
                        from workers.retry_worker import retry_failed_delivery
                        job.status = JobStatus.PROCESSING
                        await session.commit()
                        await retry_failed_delivery(session, bot, job.reference_id)
                        job.status = JobStatus.COMPLETED
                        await session.commit()
                        logger.info(f"Retry job {job.id} completed")

        except Exception as e:
            logger.error(f"Retry worker error: {e}")
        await asyncio.sleep(POLL_INTERVAL)


async def run_workers(session_factory, bot):
    """Run all background workers."""
    logger.info("Starting background workers...")
    from workers.weekly_report_worker import run_weekly_report_worker
    await asyncio.gather(
        run_cleanup_worker(session_factory, bot),
        run_retry_worker(session_factory, bot),
        run_weekly_report_worker(session_factory, bot),
    )


def main():
    """Entry point for worker process."""
    import structlog

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )

    asyncio.run(_start_workers())


async def _start_workers():
    """Start workers with proper setup."""
    # This will be called when Docker starts the worker container
    from bot.config import config
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from aiogram import Bot

    engine = create_async_engine(config.database.url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    bot = Bot(token=config.bot.token)

    try:
        await run_workers(session_factory, bot)
    finally:
        await bot.session.close()
        await engine.dispose()
