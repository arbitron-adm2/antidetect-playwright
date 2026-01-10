"""Browser pool implementation with stealth patches."""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from ..domain.interfaces import BrowserPoolPort
from ..domain.models import BrowserProfile
from .stealth import generate_stealth_script


class BrowserPool(BrowserPoolPort):
    """Manages browser contexts with stealth patches."""

    def __init__(
        self,
        browser_type: str,
        max_contexts: int,
        context_timeout: int,
        page_timeout: int,
        headless: bool,
        executable_path: str,
        stealth_enabled: bool,
    ) -> None:
        self._browser_type = browser_type
        self._max_contexts = max_contexts
        self._context_timeout = context_timeout
        self._page_timeout = page_timeout
        self._headless = headless
        self._executable_path = executable_path or None
        self._stealth_enabled = stealth_enabled

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._active_contexts: int = 0
        self._semaphore: asyncio.Semaphore | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize browser instance."""
        self._playwright = await async_playwright().start()

        browser_launcher = getattr(self._playwright, self._browser_type)

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--disable-web-security",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--window-size=1920,1080",
        ]

        self._browser = await browser_launcher.launch(
            headless=self._headless,
            executable_path=self._executable_path,
            args=launch_args,
        )

        self._semaphore = asyncio.Semaphore(self._max_contexts)

    async def shutdown(self) -> None:
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @asynccontextmanager
    async def acquire_context(
        self,
        profile: BrowserProfile,
    ) -> AsyncIterator[BrowserContext]:
        """Acquire a browser context with profile settings."""
        if not self._browser or not self._semaphore:
            raise RuntimeError("Browser pool not initialized")

        async with self._semaphore:
            async with self._lock:
                self._active_contexts += 1

            try:
                options = profile.to_context_options()
                options["ignore_https_errors"] = True

                context = await self._browser.new_context(**options)
                context.set_default_timeout(self._page_timeout * 1000)

                if self._stealth_enabled:
                    stealth_script = generate_stealth_script(
                        profile.fingerprint.to_injection_data()
                    )
                    await context.add_init_script(stealth_script)

                try:
                    yield context
                finally:
                    cookies = await context.cookies()
                    profile.cookies = cookies
                    await context.close()
            finally:
                async with self._lock:
                    self._active_contexts -= 1

    @asynccontextmanager
    async def acquire_page(
        self,
        profile: BrowserProfile,
    ) -> AsyncIterator[Page]:
        """Acquire a page with stealth patches."""
        async with self.acquire_context(profile) as context:
            page = await context.new_page()

            await page.route("**/*", self._handle_route)

            try:
                yield page
            finally:
                await page.close()

    async def _handle_route(self, route) -> None:
        """Handle requests for additional filtering."""
        headers = dict(route.request.headers)

        headers.pop("sec-ch-ua-platform", None)
        headers.pop("sec-ch-ua-mobile", None)
        headers.pop("sec-ch-ua", None)

        await route.continue_(headers=headers)

    async def get_active_contexts_count(self) -> int:
        """Get number of active contexts."""
        async with self._lock:
            return self._active_contexts

    async def get_max_contexts(self) -> int:
        """Get maximum contexts limit."""
        return self._max_contexts
