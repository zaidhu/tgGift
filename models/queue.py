"""Queue job tracking model."""

import enum
from sqlalchemy import BigInteger, Integer, String, Text, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class JobType(str, enum.Enum):
    RETRY_DELIVERY = "retry_delivery"
    REFUND_PROCESS = "refund_process"
    GIFT_EXPIRATION = "gift_expiration"
    SCHEDULED_GIFT = "scheduled_gift"
    NOTIFICATION = "notification"
    CLEANUP = "cleanup"


class QueueJob(TimestampMixin, Base):
    __tablename__ = "queue_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.PENDING, nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    next_retry_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self):
        return f"<QueueJob(id={self.id}, type={self.job_type}, status={self.status})>"
