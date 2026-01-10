"""Proxy manager interface."""

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import ProxyConfig, ProxyStatus


class ProxyManagerPort(ABC):
    """Interface for proxy pool management."""

    @abstractmethod
    async def load_proxies(self, source: str) -> int:
        """Load proxies from source.

        Args:
            source: Path to proxy list file or URL.

        Returns:
            Number of proxies loaded.
        """
        ...

    @abstractmethod
    async def get_proxy(self) -> ProxyConfig | None:
        """Get next available proxy based on rotation strategy.

        Returns:
            Proxy configuration or None if no proxies available.
        """
        ...

    @abstractmethod
    async def release_proxy(self, proxy: ProxyConfig) -> None:
        """Release proxy back to pool.

        Args:
            proxy: Proxy to release.
        """
        ...

    @abstractmethod
    async def mark_proxy_status(
        self,
        proxy: ProxyConfig,
        status: ProxyStatus,
    ) -> None:
        """Update proxy health status.

        Args:
            proxy: Proxy to update.
            status: New status.
        """
        ...

    @abstractmethod
    async def validate_proxy(self, proxy: ProxyConfig) -> ProxyStatus:
        """Validate proxy connectivity.

        Args:
            proxy: Proxy to validate.

        Returns:
            Validation result status.
        """
        ...

    @abstractmethod
    async def validate_all(self) -> dict[ProxyStatus, int]:
        """Validate all proxies in pool.

        Returns:
            Status counts.
        """
        ...

    @abstractmethod
    async def get_stats(self) -> dict[str, int]:
        """Get proxy pool statistics.

        Returns:
            Statistics dictionary.
        """
        ...

    @abstractmethod
    async def remove_invalid(self) -> int:
        """Remove all invalid proxies from pool.

        Returns:
            Number of proxies removed.
        """
        ...
