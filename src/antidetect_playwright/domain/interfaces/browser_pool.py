"""Browser pool interface."""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import BrowserContext, Page

from ..models import BrowserProfile


class BrowserPoolPort(ABC):
    """Interface for browser context pool management."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the browser pool."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown and cleanup all browser contexts."""
        ...

    @abstractmethod
    @asynccontextmanager
    async def acquire_context(
        self,
        profile: BrowserProfile,
    ) -> AsyncIterator[BrowserContext]:
        """Acquire a browser context from pool.

        Args:
            profile: Browser profile to use for context.

        Yields:
            BrowserContext configured with profile settings.
        """
        ...

    @abstractmethod
    @asynccontextmanager
    async def acquire_page(
        self,
        profile: BrowserProfile,
    ) -> AsyncIterator[Page]:
        """Acquire a page with stealth patches applied.

        Args:
            profile: Browser profile to use.

        Yields:
            Page with stealth injections applied.
        """
        ...

    @abstractmethod
    async def get_active_contexts_count(self) -> int:
        """Get number of currently active contexts."""
        ...

    @abstractmethod
    async def get_max_contexts(self) -> int:
        """Get maximum allowed contexts."""
        ...
