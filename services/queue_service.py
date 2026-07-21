"""
Queue service.
Manages background job queue for async tasks.
"""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import QueueJob, JobStatus, JobType

logger = logging.getLogger(__name__)


class QueueService:
    """Manages background job queue."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def enqueue(
        self,
        job_type: JobType,
        reference_id: Optional[int] = None,
        telegram_id: Optional[int] = None,
        payload: Optional[str] = None,
        max_attempts: int = 3,
    ) -> QueueJob:
        """Add a job to the queue."""
        job = QueueJob(
            job_type=job_type,
            reference_id=reference_id,
            telegram_id=telegram_id,
            payload=payload,
            status=JobStatus.PENDING,
            max_attempts=max_attempts,
        )
        self.session.add(job)
        await self.session.commit()
        logger.info(f"Job enqueued: {job.id} ({job_type.value})")
        return job

    async def dequeue(self, job_type: JobType) -> Optional[QueueJob]:
        """Get the next pending job of a specific type."""
        result = await self.session.execute(
            select(QueueJob)
            .where(
                QueueJob.job_type == job_type,
                QueueJob.status == JobStatus.PENDING,
            )
            .order_by(QueueJob.created_at.asc())
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = JobStatus.PROCESSING
            await self.session.commit()
        return job

    async def complete_job(self, job_id: int) -> None:
        """Mark a job as completed."""
        job = await self.session.get(QueueJob, job_id)
        if job:
            job.status = JobStatus.COMPLETED
            await self.session.commit()

    async def fail_job(self, job_id: int, error: str) -> QueueJob:
        """Mark a job as failed or retry."""
        job = await self.session.get(QueueJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.attempts += 1
        job.error_message = error

        if job.attempts < job.max_attempts:
            job.status = JobStatus.RETRYING
            logger.info(f"Job {job_id} will retry (attempt {job.attempts}/{job.max_attempts})")
        else:
            job.status = JobStatus.FAILED
            logger.error(f"Job {job_id} failed permanently after {job.attempts} attempts")

        await self.session.commit()
        return job

    async def get_job_stats(self) -> dict:
        """Get queue job statistics."""
        result = await self.session.execute(text("""
            SELECT status, job_type, COUNT(*) as count
            FROM queue_jobs
            GROUP BY status, job_type
        """))
        stats = {}
        for row in result.fetchall():
            stats[f"{row[0]}_{row[1]}"] = row[2]
        return stats
