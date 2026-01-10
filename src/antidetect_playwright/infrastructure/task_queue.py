"""Redis-based task queue implementation."""

import json
from datetime import datetime
from typing import Sequence

from ..domain.interfaces import TaskQueuePort
from ..domain.models import Task, TaskResult, TaskStatus
from .redis_client import RedisClient


class RedisTaskQueue(TaskQueuePort):
    """Task queue backed by Redis."""

    PENDING_KEY = "tasks:pending"
    RUNNING_KEY = "tasks:running"
    TASK_PREFIX = "task:"
    RESULT_PREFIX = "result:"

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    def _task_to_dict(self, task: Task) -> dict:
        """Serialize task to dict."""
        return {
            "id": task.id,
            "script_path": task.script_path,
            "profile_id": task.profile_id or "",
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "priority": str(task.priority),
            "retry_count": str(task.retry_count),
            "max_retries": str(task.max_retries),
            "timeout": str(task.timeout),
            "metadata": json.dumps(task.metadata),
            "started_at": task.started_at.isoformat() if task.started_at else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
            "error_message": task.error_message or "",
        }

    def _dict_to_task(self, data: dict) -> Task:
        """Deserialize task from dict."""
        return Task(
            id=data["id"],
            script_path=data["script_path"],
            profile_id=data["profile_id"] or None,
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            priority=int(data["priority"]),
            retry_count=int(data["retry_count"]),
            max_retries=int(data["max_retries"]),
            timeout=int(data["timeout"]),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else {},
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"])
                if data.get("completed_at")
                else None
            ),
            error_message=data.get("error_message") or None,
        )

    def _result_to_dict(self, result: TaskResult) -> dict:
        """Serialize result to dict."""
        return {
            "task_id": result.task_id,
            "success": str(result.success),
            "duration_seconds": str(result.duration_seconds),
            "data": json.dumps(result.data),
            "error": result.error or "",
            "screenshots": json.dumps(result.screenshots),
            "logs": json.dumps(result.logs),
        }

    def _dict_to_result(self, data: dict) -> TaskResult:
        """Deserialize result from dict."""
        return TaskResult(
            task_id=data["task_id"],
            success=data["success"] == "True",
            duration_seconds=float(data["duration_seconds"]),
            data=json.loads(data["data"]) if data.get("data") else {},
            error=data.get("error") or None,
            screenshots=(
                tuple(json.loads(data["screenshots"]))
                if data.get("screenshots")
                else ()
            ),
            logs=tuple(json.loads(data["logs"])) if data.get("logs") else (),
        )

    async def enqueue(self, task: Task) -> None:
        """Add task to queue."""
        task.status = TaskStatus.QUEUED
        task_data = self._task_to_dict(task)

        await self._redis.hset(f"{self.TASK_PREFIX}{task.id}", task_data)
        await self._redis.lpush(self.PENDING_KEY, task.id)

    async def enqueue_batch(self, tasks: Sequence[Task]) -> int:
        """Add multiple tasks to queue."""
        count = 0
        for task in tasks:
            await self.enqueue(task)
            count += 1
        return count

    async def dequeue(self) -> Task | None:
        """Get next task from queue."""
        task_id = await self._redis.client.rpoplpush(
            self._redis._make_key(self.PENDING_KEY),
            self._redis._make_key(self.RUNNING_KEY),
        )

        if not task_id:
            return None

        task_data = await self._redis.hgetall(f"{self.TASK_PREFIX}{task_id}")
        if not task_data:
            return None

        task = self._dict_to_task(task_data)
        task.mark_started()

        await self._redis.hset(
            f"{self.TASK_PREFIX}{task.id}",
            self._task_to_dict(task),
        )

        return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        task_data = await self._redis.hgetall(f"{self.TASK_PREFIX}{task_id}")
        if not task_data:
            return None
        return self._dict_to_task(task_data)

    async def update_task(self, task: Task) -> None:
        """Update task state."""
        task_data = self._task_to_dict(task)
        await self._redis.hset(f"{self.TASK_PREFIX}{task.id}", task_data)

    async def store_result(self, result: TaskResult) -> None:
        """Store task result."""
        result_data = self._result_to_dict(result)
        await self._redis.hset(f"{self.RESULT_PREFIX}{result.task_id}", result_data)

        await self._redis.client.lrem(
            self._redis._make_key(self.RUNNING_KEY),
            0,
            result.task_id,
        )

    async def get_result(self, task_id: str) -> TaskResult | None:
        """Get task result."""
        result_data = await self._redis.hgetall(f"{self.RESULT_PREFIX}{task_id}")
        if not result_data:
            return None
        return self._dict_to_result(result_data)

    async def get_pending_count(self) -> int:
        """Get number of pending tasks."""
        return await self._redis.llen(self.PENDING_KEY)

    async def get_running_count(self) -> int:
        """Get number of running tasks."""
        return await self._redis.llen(self.RUNNING_KEY)

    async def get_tasks_by_status(
        self,
        status: TaskStatus,
        limit: int = 100,
    ) -> Sequence[Task]:
        """Get tasks by status."""
        tasks = []

        if status == TaskStatus.QUEUED:
            task_ids = await self._redis.lrange(self.PENDING_KEY, 0, limit - 1)
        elif status == TaskStatus.RUNNING:
            task_ids = await self._redis.lrange(self.RUNNING_KEY, 0, limit - 1)
        else:
            return tasks

        for task_id in task_ids:
            task = await self.get_task(task_id)
            if task:
                tasks.append(task)

        return tasks

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        task = await self.get_task(task_id)
        if not task:
            return False

        if task.status not in (
            TaskStatus.PENDING,
            TaskStatus.QUEUED,
            TaskStatus.RUNNING,
        ):
            return False

        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        await self.update_task(task)

        await self._redis.client.lrem(
            self._redis._make_key(self.PENDING_KEY),
            0,
            task_id,
        )
        await self._redis.client.lrem(
            self._redis._make_key(self.RUNNING_KEY),
            0,
            task_id,
        )

        return True

    async def retry_failed(self) -> int:
        """Requeue failed tasks that can be retried."""
        count = 0
        return count
