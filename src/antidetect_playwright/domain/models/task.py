"""Task domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass(slots=True)
class Task:
    """User scenario/script task."""

    id: str
    script_path: str
    profile_id: str | None
    status: TaskStatus
    created_at: datetime
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 600
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.retry_count < self.max_retries

    def mark_started(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.now()

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error

    def mark_retrying(self) -> None:
        """Mark task for retry."""
        self.status = TaskStatus.RETRYING
        self.retry_count += 1
        self.error_message = None
        self.started_at = None
        self.completed_at = None


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Task execution result."""

    task_id: str
    success: bool
    duration_seconds: float
    data: dict[str, Any]
    error: str | None = None
    screenshots: tuple[str, ...] = ()
    logs: tuple[str, ...] = ()
