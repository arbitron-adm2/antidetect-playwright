"""Main application entry point."""

import asyncio
import signal
from pathlib import Path

import click

from .config import load_config
from .logging import setup_logging, get_logger
from .infrastructure import (
    BrowserPool,
    FingerprintGenerator,
    ProxyManager,
    RedisClient,
    RedisTaskQueue,
    FileProfileStorage,
)
from .application import TaskRunner


class Application:
    """Main application container."""

    def __init__(self, config_dir: str) -> None:
        self._config = load_config(config_dir)
        self._logger = get_logger(__name__)

        self._redis: RedisClient | None = None
        self._browser_pool: BrowserPool | None = None
        self._task_runner: TaskRunner | None = None
        self._running = False

    async def start(self) -> None:
        """Initialize and start all services."""
        setup_logging(self._config.logging, self._config.storage.logs_dir)
        self._logger.info(f"Starting {self._config.name} v{self._config.version}")

        self._redis = RedisClient(
            host=self._config.redis.host,
            port=self._config.redis.port,
            password=self._config.redis.password,
            db=self._config.redis.db,
            pool_size=self._config.redis.pool_size,
            key_prefix=self._config.redis.key_prefix,
            default_ttl=self._config.redis.default_ttl,
            connection_timeout=self._config.redis.connection_timeout,
        )
        await self._redis.connect()
        self._logger.info("Redis connected")

        fingerprint_generator = FingerprintGenerator(
            screen_resolutions=list(self._config.fingerprint.screen_resolutions),
            languages=list(self._config.fingerprint.languages),
            timezones=list(self._config.fingerprint.timezones),
            platforms=list(self._config.fingerprint.platforms),
        )

        proxy_manager = ProxyManager(
            rotation_strategy=self._config.proxy.rotation_strategy,
            validation_timeout=self._config.proxy.validation_timeout,
            max_retries=self._config.proxy.max_retries,
            retry_delay=self._config.proxy.retry_delay,
        )

        proxy_file = Path(self._config.proxy.list_file)
        if proxy_file.exists():
            count = await proxy_manager.load_proxies(str(proxy_file))
            self._logger.info(f"Loaded {count} proxies")

        self._browser_pool = BrowserPool(
            browser_type=self._config.browser.type,
            max_contexts=self._config.browser.max_contexts,
            context_timeout=self._config.browser.context_timeout,
            page_timeout=self._config.browser.page_timeout,
            headless=self._config.browser.headless,
            executable_path=self._config.browser.executable_path,
            stealth_enabled=self._config.stealth.enabled,
        )
        await self._browser_pool.initialize()
        self._logger.info("Browser pool initialized")

        task_queue = RedisTaskQueue(self._redis)
        profile_storage = FileProfileStorage(self._config.browser.user_data_dir)

        self._task_runner = TaskRunner(
            browser_pool=self._browser_pool,
            task_queue=task_queue,
            profile_storage=profile_storage,
            fingerprint_generator=fingerprint_generator,
            proxy_manager=proxy_manager,
            max_concurrent_tasks=self._config.task_runner.max_concurrent_tasks,
            task_timeout=self._config.task_runner.task_timeout,
            retry_on_failure=self._config.task_runner.retry_on_failure,
            scripts_dir=self._config.storage.scripts_dir,
            results_dir=self._config.storage.results_dir,
            screenshots_dir=self._config.storage.screenshots_dir,
        )
        await self._task_runner.start()
        self._logger.info(
            f"Task runner started with {self._config.task_runner.max_concurrent_tasks} workers"
        )

        self._running = True
        self._logger.info("Application started successfully")

    async def stop(self) -> None:
        """Shutdown all services."""
        self._logger.info("Shutting down...")
        self._running = False

        if self._task_runner:
            await self._task_runner.stop()
            self._logger.info("Task runner stopped")

        if self._browser_pool:
            await self._browser_pool.shutdown()
            self._logger.info("Browser pool closed")

        if self._redis:
            await self._redis.disconnect()
            self._logger.info("Redis disconnected")

        self._logger.info("Shutdown complete")

    async def run_forever(self) -> None:
        """Run until shutdown signal."""
        loop = asyncio.get_event_loop()
        stop_event = asyncio.Event()

        def signal_handler() -> None:
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        await stop_event.wait()

    @property
    def task_runner(self) -> TaskRunner:
        """Get task runner instance."""
        if not self._task_runner:
            raise RuntimeError("Application not started")
        return self._task_runner


@click.group()
@click.option(
    "--config",
    "-c",
    default=".config",
    help="Configuration directory path",
)
@click.pass_context
def cli(ctx: click.Context, config: str) -> None:
    """Antidetect Playwright - Stealth browser automation."""
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = config


@cli.command()
@click.pass_context
def run(ctx: click.Context) -> None:
    """Start the application."""

    async def main() -> None:
        app = Application(ctx.obj["config_dir"])
        try:
            await app.start()
            await app.run_forever()
        finally:
            await app.stop()

    asyncio.run(main())


@cli.command()
@click.argument("script")
@click.option("--profile", "-p", help="Profile ID to use")
@click.option("--count", "-n", default=1, help="Number of parallel executions")
@click.pass_context
def execute(ctx: click.Context, script: str, profile: str | None, count: int) -> None:
    """Execute a script."""

    async def main() -> None:
        app = Application(ctx.obj["config_dir"])
        try:
            await app.start()

            tasks = []
            for i in range(count):
                task_id = await app.task_runner.submit_task(
                    script_path=script,
                    profile_id=f"{profile}_{i}" if profile else None,
                )
                tasks.append(task_id)
                click.echo(f"Submitted task: {task_id}")

            while True:
                pending = await app.task_runner._task_queue.get_pending_count()
                running = await app.task_runner._task_queue.get_running_count()

                if pending == 0 and running == 0:
                    break

                click.echo(f"Pending: {pending}, Running: {running}")
                await asyncio.sleep(2)

            for task_id in tasks:
                result = await app.task_runner.get_task_result(task_id)
                if result:
                    status = "✓" if result.success else "✗"
                    click.echo(
                        f"{status} Task {task_id}: {result.duration_seconds:.2f}s"
                    )
                    if result.error:
                        click.echo(f"  Error: {result.error[:100]}")
        finally:
            await app.stop()

    asyncio.run(main())


@cli.command()
@click.pass_context
def validate_proxies(ctx: click.Context) -> None:
    """Validate all proxies."""
    from .config import load_config

    async def main() -> None:
        config = load_config(ctx.obj["config_dir"])

        proxy_manager = ProxyManager(
            rotation_strategy=config.proxy.rotation_strategy,
            validation_timeout=config.proxy.validation_timeout,
            max_retries=config.proxy.max_retries,
            retry_delay=config.proxy.retry_delay,
        )

        proxy_file = Path(config.proxy.list_file)
        if not proxy_file.exists():
            click.echo(f"Proxy file not found: {proxy_file}")
            return

        count = await proxy_manager.load_proxies(str(proxy_file))
        click.echo(f"Loaded {count} proxies")

        click.echo("Validating proxies...")
        stats = await proxy_manager.validate_all()

        click.echo("\nResults:")
        for status, count in stats.items():
            click.echo(f"  {status.value}: {count}")

    asyncio.run(main())


def main() -> None:
    """CLI entry point."""
    cli()
