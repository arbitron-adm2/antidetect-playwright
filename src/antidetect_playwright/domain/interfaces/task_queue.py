"""Task queue interface."""

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import Task, TaskResult, TaskStatus


class TaskQueuePort(ABC):
    """Interface for task queue management."""

    @abstractmethod
    async def enqueue(self, task: Task) -> None:
        """Add task to queue.

        Args:
            task: Task to enqueue.
        """
        ...

    @abstractmethod
    async def enqueue_batch(self, tasks: Sequence[Task]) -> int:
        """Add multiple tasks to queue.

        Args:
            tasks: Tasks to enqueue.

        Returns:
            Number of tasks enqueued.
        """
        ...

    @abstractmethod
    async def dequeue(self) -> Task | None:
        """Get next task from queue.

        Returns:
            Next task or None if queue is empty.
        """
        ...

    @abstractmethod
    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID.

        Args:
            task_id: Task identifier.

        Returns:
            Task or None if not found.
        """
        ...

    @abstractmethod
    async def update_task(self, task: Task) -> None:
        """Update task state.

        Args:
            task: Task with updated state.
        """
        ...

    @abstractmethod
    async def store_result(self, result: TaskResult) -> None:
        """Store task execution result.

        Args:
            result: Task result to store.
        """
        ...

    @abstractmethod
    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result.

        Args:
            task_id: Task identifier.

        Returns:
            Task result or None if not found.
        """
        ...

    @abstractmethod
    async def get_pending_count(self) -> int:
        """Get number of pending tasks."""
        ...

    @abstractmethod
    async def get_running_count(self) -> int:
        """Get number of running tasks."""
        ...

    @abstractmethod
    async def get_tasks_by_status(
        self,
        status: TaskStatus,
        limit: int = 100,
    ) -> Sequence[Task]:
        """Get tasks by status.

        Args:
            status: Status to filter by.
            limit: Maximum number of tasks to return.

        Returns:
            Tasks matching status.
        """
        ...

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task.

        Args:
            task_id: Task identifier.

        Returns:
            True if task was cancelled.
        """
        ...

    @abstractmethod
    async def retry_failed(self) -> int:
        """Requeue all failed tasks that can be retried.

        Returns:
            Number of tasks requeued.
        """
        ...
