"""Batch executor for parallel task execution."""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4

from playwright.async_api import Page

from .session_manager import SessionManager, UniqueSession
from .result_handler import ResultHandler, RegistrationResult, RegistrationStatus
from ..domain.models import Task, TaskStatus
from ..infrastructure import BrowserPool


@dataclass
class BatchConfig:
    """Configuration for batch execution."""

    max_concurrent: int = 100
    task_timeout: int = 300
    retry_on_failure: bool = True
    max_retries: int = 2
    delay_between_starts: float = 0.5  # Stagger start to avoid detection
    screenshot_on_error: bool = True
    screenshot_on_success: bool = False


@dataclass
class BatchStats:
    """Statistics for batch execution."""

    total_tasks: int = 0
    completed: int = 0
    successful: int = 0
    failed: int = 0
    in_progress: int = 0
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        if self.completed == 0:
            return 0.0
        return (self.successful / self.completed) * 100

    @property
    def duration_seconds(self) -> float:
        if not self.start_time:
            return 0.0
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


ScriptFunction = Callable[
    [Page, UniqueSession, dict[str, Any]], Awaitable[RegistrationResult]
]


class BatchExecutor:
    """Executes registration tasks in parallel batches."""

    def __init__(
        self,
        browser_pool: BrowserPool,
        session_manager: SessionManager,
        result_handler: ResultHandler,
        config: BatchConfig | None = None,
    ) -> None:
        self._browser_pool = browser_pool
        self._session_manager = session_manager
        self._result_handler = result_handler
        self._config = config or BatchConfig()

        self._stats = BatchStats()
        self._running = False
        self._cancel_event: asyncio.Event | None = None

    async def execute_batch(
        self,
        script_func: ScriptFunction,
        task_count: int,
        task_data: list[dict[str, Any]] | None = None,
        platform: str | None = None,
    ) -> BatchStats:
        """Execute a batch of registration tasks.

        Args:
            script_func: Async function that performs registration.
            task_count: Number of tasks to execute.
            task_data: Per-task data (email, password, etc.). If None, generates.
            platform: Target platform for fingerprints.

        Returns:
            Batch execution statistics.
        """
        self._running = True
        self._cancel_event = asyncio.Event()
        self._stats = BatchStats(total_tasks=task_count)
        self._stats.start_time = datetime.now()

        self._session_manager.reset_uniqueness_tracking()

        if task_data is None:
            task_data = [{} for _ in range(task_count)]
        elif len(task_data) < task_count:
            task_data.extend([{} for _ in range(task_count - len(task_data))])

        semaphore = asyncio.Semaphore(self._config.max_concurrent)
        tasks = []

        for i, data in enumerate(task_data[:task_count]):
            if self._cancel_event.is_set():
                break

            task = asyncio.create_task(
                self._execute_single_task(
                    script_func=script_func,
                    task_index=i,
                    task_data=data,
                    platform=platform,
                    semaphore=semaphore,
                )
            )
            tasks.append(task)

            if self._config.delay_between_starts > 0:
                await asyncio.sleep(self._config.delay_between_starts)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._stats.end_time = datetime.now()
        self._running = False

        return self._stats

    async def _execute_single_task(
        self,
        script_func: ScriptFunction,
        task_index: int,
        task_data: dict[str, Any],
        platform: str | None,
        semaphore: asyncio.Semaphore,
    ) -> RegistrationResult:
        """Execute a single registration task."""
        task_id = str(uuid4())

        async with semaphore:
            if self._cancel_event and self._cancel_event.is_set():
                return self._create_cancelled_result(task_id)

            self._stats.in_progress += 1

            try:
                result = await self._run_with_retry(
                    script_func=script_func,
                    task_id=task_id,
                    task_data=task_data,
                    platform=platform,
                )
            finally:
                self._stats.in_progress -= 1
                self._stats.completed += 1

                if result.status == RegistrationStatus.SUCCESS:
                    self._stats.successful += 1
                else:
                    self._stats.failed += 1

            await self._result_handler.handle_result(result)

            return result

    async def _run_with_retry(
        self,
        script_func: ScriptFunction,
        task_id: str,
        task_data: dict[str, Any],
        platform: str | None,
    ) -> RegistrationResult:
        """Run task with retry logic."""
        last_error: str | None = None

        max_attempts = 1 + (
            self._config.max_retries if self._config.retry_on_failure else 0
        )

        for attempt in range(max_attempts):
            session = await self._session_manager.create_unique_session(
                task_id=task_id,
                platform=platform,
                metadata={"attempt": attempt + 1, **task_data},
            )

            try:
                result = await self._execute_in_browser(
                    script_func=script_func,
                    session=session,
                    task_data=task_data,
                )

                if result.status == RegistrationStatus.SUCCESS:
                    return result

                last_error = result.error_message

                if result.status in (
                    RegistrationStatus.BANNED,
                    RegistrationStatus.CAPTCHA_FAILED,
                ):
                    return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self._config.task_timeout}s"
                result = RegistrationResult(
                    task_id=task_id,
                    session_id=session.id,
                    status=RegistrationStatus.TIMEOUT,
                    error_message=last_error,
                )
            except Exception as e:
                last_error = str(e)
                result = RegistrationResult(
                    task_id=task_id,
                    session_id=session.id,
                    status=RegistrationStatus.FAILED,
                    error_message=last_error,
                )
            finally:
                await self._session_manager.release_session(session.id)

        return RegistrationResult(
            task_id=task_id,
            session_id=session.id if "session" in locals() else "unknown",
            status=RegistrationStatus.FAILED,
            error_message=f"All {max_attempts} attempts failed. Last error: {last_error}",
        )

    async def _execute_in_browser(
        self,
        script_func: ScriptFunction,
        session: UniqueSession,
        task_data: dict[str, Any],
    ) -> RegistrationResult:
        """Execute script in browser context."""
        start_time = time.time()
        screenshots: list[str] = []

        async with self._browser_pool.acquire_page(session.profile) as page:
            try:
                result = await asyncio.wait_for(
                    script_func(page, session, task_data),
                    timeout=self._config.task_timeout,
                )

                result.duration_seconds = time.time() - start_time
                result.session_id = session.id

                if result.status == RegistrationStatus.SUCCESS:
                    result.cookies = await page.context.cookies()

                    if self._config.screenshot_on_success:
                        path = f"/data/screenshots/{session.id}_success.png"
                        await page.screenshot(path=path)
                        result.screenshots.append(path)

                return result

            except Exception as e:
                if self._config.screenshot_on_error:
                    try:
                        path = f"/data/screenshots/{session.id}_error.png"
                        await page.screenshot(path=path)
                        screenshots.append(path)
                    except Exception:
                        pass

                return RegistrationResult(
                    task_id=task_data.get(
                        "task_id", session.metadata.get("task_id", "")
                    ),
                    session_id=session.id,
                    status=RegistrationStatus.FAILED,
                    error_message=str(e),
                    duration_seconds=time.time() - start_time,
                    screenshots=screenshots,
                )

    def _create_cancelled_result(self, task_id: str) -> RegistrationResult:
        """Create result for cancelled task."""
        return RegistrationResult(
            task_id=task_id,
            session_id="cancelled",
            status=RegistrationStatus.FAILED,
            error_message="Task cancelled",
        )

    async def cancel(self) -> None:
        """Cancel batch execution."""
        if self._cancel_event:
            self._cancel_event.set()

    @property
    def is_running(self) -> bool:
        """Check if batch is currently running."""
        return self._running

    @property
    def stats(self) -> BatchStats:
        """Get current statistics."""
        return self._stats

    def get_progress(self) -> dict[str, Any]:
        """Get current progress."""
        return {
            "total": self._stats.total_tasks,
            "completed": self._stats.completed,
            "in_progress": self._stats.in_progress,
            "successful": self._stats.successful,
            "failed": self._stats.failed,
            "success_rate": f"{self._stats.success_rate:.1f}%",
            "duration": f"{self._stats.duration_seconds:.0f}s",
            "remaining": self._stats.total_tasks - self._stats.completed,
        }
