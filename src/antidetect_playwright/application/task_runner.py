"""Task runner for executing user scenarios."""

import asyncio
import importlib.util
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Awaitable
from uuid import uuid4

from playwright.async_api import Page

from ..domain.interfaces import (
    BrowserPoolPort,
    TaskQueuePort,
    ProfileStoragePort,
    FingerprintGeneratorPort,
    ProxyManagerPort,
)
from ..domain.models import Task, TaskResult, TaskStatus, BrowserProfile


@dataclass
class TaskContext:
    """Context passed to user scripts."""

    task: Task
    page: Page
    profile: BrowserProfile
    log: Callable[[str], None]
    screenshot: Callable[[str], Awaitable[str]]
    store_data: Callable[[str, Any], None]


class TaskRunner:
    """Executes user scenarios in browser contexts."""

    def __init__(
        self,
        browser_pool: BrowserPoolPort,
        task_queue: TaskQueuePort,
        profile_storage: ProfileStoragePort,
        fingerprint_generator: FingerprintGeneratorPort,
        proxy_manager: ProxyManagerPort,
        max_concurrent_tasks: int,
        task_timeout: int,
        retry_on_failure: bool,
        scripts_dir: str,
        results_dir: str,
        screenshots_dir: str,
    ) -> None:
        self._browser_pool = browser_pool
        self._task_queue = task_queue
        self._profile_storage = profile_storage
        self._fingerprint_generator = fingerprint_generator
        self._proxy_manager = proxy_manager
        self._max_concurrent = max_concurrent_tasks
        self._task_timeout = task_timeout
        self._retry_on_failure = retry_on_failure
        self._scripts_dir = Path(scripts_dir)
        self._results_dir = Path(results_dir)
        self._screenshots_dir = Path(screenshots_dir)

        self._running = False
        self._workers: list[asyncio.Task] = []
        self._semaphore: asyncio.Semaphore | None = None

    async def start(self) -> None:
        """Start task runner workers."""
        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

        self._results_dir.mkdir(parents=True, exist_ok=True)
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)

        for i in range(self._max_concurrent):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)

    async def stop(self) -> None:
        """Stop all workers."""
        self._running = False

        for worker in self._workers:
            worker.cancel()

        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()

    async def submit_task(
        self,
        script_path: str,
        profile_id: str | None = None,
        priority: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Submit a new task for execution."""
        task_id = str(uuid4())

        task = Task(
            id=task_id,
            script_path=script_path,
            profile_id=profile_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            priority=priority,
            timeout=self._task_timeout,
            metadata=metadata or {},
        )

        await self._task_queue.enqueue(task)
        return task_id

    async def get_task_status(self, task_id: str) -> TaskStatus | None:
        """Get task status."""
        task = await self._task_queue.get_task(task_id)
        return task.status if task else None

    async def get_task_result(self, task_id: str) -> TaskResult | None:
        """Get task result."""
        return await self._task_queue.get_result(task_id)

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop that processes tasks."""
        while self._running:
            try:
                task = await self._task_queue.dequeue()
                if not task:
                    await asyncio.sleep(0.5)
                    continue

                result = await self._execute_task(task)
                await self._task_queue.store_result(result)

                if not result.success and self._retry_on_failure and task.can_retry():
                    task.mark_retrying()
                    await self._task_queue.enqueue(task)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(1)

    async def _execute_task(self, task: Task) -> TaskResult:
        """Execute a single task."""
        start_time = time.time()
        logs: list[str] = []
        screenshots: list[str] = []
        data: dict[str, Any] = {}

        def log(message: str) -> None:
            timestamp = datetime.now().isoformat()
            logs.append(f"[{timestamp}] {message}")

        async def take_screenshot(name: str) -> str:
            path = self._screenshots_dir / f"{task.id}_{name}.png"
            return str(path)

        def store_data(key: str, value: Any) -> None:
            data[key] = value

        try:
            profile = await self._get_or_create_profile(task.profile_id)

            script_path = self._scripts_dir / task.script_path
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found: {task.script_path}")

            run_func = self._load_script(script_path)

            async with self._browser_pool.acquire_page(profile) as page:
                context = TaskContext(
                    task=task,
                    page=page,
                    profile=profile,
                    log=log,
                    screenshot=take_screenshot,
                    store_data=store_data,
                )

                async def screenshot_wrapper(name: str) -> str:
                    path = await take_screenshot(name)
                    await page.screenshot(path=path)
                    screenshots.append(path)
                    return path

                context.screenshot = screenshot_wrapper

                try:
                    await asyncio.wait_for(
                        run_func(context),
                        timeout=task.timeout,
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(f"Task timed out after {task.timeout}s")

            task.mark_completed()
            await self._task_queue.update_task(task)

            if task.profile_id:
                await self._profile_storage.save(profile)

            return TaskResult(
                task_id=task.id,
                success=True,
                duration_seconds=time.time() - start_time,
                data=data,
                screenshots=tuple(screenshots),
                logs=tuple(logs),
            )

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            log(f"ERROR: {error_msg}")

            task.mark_failed(str(e))
            await self._task_queue.update_task(task)

            return TaskResult(
                task_id=task.id,
                success=False,
                duration_seconds=time.time() - start_time,
                data=data,
                error=error_msg,
                screenshots=tuple(screenshots),
                logs=tuple(logs),
            )

    async def _get_or_create_profile(self, profile_id: str | None) -> BrowserProfile:
        """Get existing profile or create new one."""
        if profile_id:
            profile = await self._profile_storage.load(profile_id)
            if profile:
                return profile

        fingerprint = self._fingerprint_generator.generate()
        proxy = await self._proxy_manager.get_proxy()

        profile = BrowserProfile(
            id=profile_id or str(uuid4()),
            fingerprint=fingerprint,
            proxy=proxy,
            storage_path=str(self._results_dir / (profile_id or fingerprint.id)),
            created_at=datetime.now(),
        )

        if profile_id:
            await self._profile_storage.save(profile)

        return profile

    def _load_script(
        self, script_path: Path
    ) -> Callable[[TaskContext], Awaitable[None]]:
        """Load and validate user script."""
        spec = importlib.util.spec_from_file_location("user_script", script_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot load script: {script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules["user_script"] = module
        spec.loader.exec_module(module)

        if not hasattr(module, "run"):
            raise AttributeError("Script must define async 'run(context)' function")

        run_func = getattr(module, "run")
        if not asyncio.iscoroutinefunction(run_func):
            raise TypeError("'run' function must be async")

        return run_func
