"""Proxy manager implementation."""

import asyncio
import random
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import aiohttp

from ..domain.interfaces import ProxyManagerPort
from ..domain.models import ProxyConfig, ProxyProtocol, ProxyStatus


@dataclass
class ProxyEntry:
    """Internal proxy tracking entry."""

    config: ProxyConfig
    status: ProxyStatus = ProxyStatus.UNKNOWN
    in_use: bool = False
    use_count: int = 0
    fail_count: int = 0
    last_validated: float = 0.0


class ProxyManager(ProxyManagerPort):
    """Manages proxy pool with rotation and validation."""

    def __init__(
        self,
        rotation_strategy: str,
        validation_timeout: int,
        max_retries: int,
        retry_delay: int,
    ) -> None:
        self._rotation_strategy = rotation_strategy
        self._validation_timeout = validation_timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        self._proxies: dict[str, ProxyEntry] = {}
        self._available: deque[str] = deque()
        self._lock = asyncio.Lock()
        self._round_robin_index = 0

    async def load_proxies(self, source: str) -> int:
        """Load proxies from file."""
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Proxy file not found: {source}")

        count = 0
        async with self._lock:
            content = path.read_text()
            for line in content.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                try:
                    if "://" in line:
                        proxy = ProxyConfig.from_url(line)
                    else:
                        proxy = ProxyConfig.from_line(line)

                    key = proxy.url
                    if key not in self._proxies:
                        self._proxies[key] = ProxyEntry(config=proxy)
                        self._available.append(key)
                        count += 1
                except ValueError:
                    continue

        return count

    async def get_proxy(self) -> ProxyConfig | None:
        """Get next available proxy based on rotation strategy."""
        async with self._lock:
            if not self._available:
                return None

            if self._rotation_strategy == "random":
                key = random.choice(list(self._available))
            elif self._rotation_strategy == "round_robin":
                if self._round_robin_index >= len(self._available):
                    self._round_robin_index = 0
                key = list(self._available)[self._round_robin_index]
                self._round_robin_index += 1
            else:
                key = self._available[0]

            entry = self._proxies[key]
            entry.in_use = True
            entry.use_count += 1

            return entry.config

    async def release_proxy(self, proxy: ProxyConfig) -> None:
        """Release proxy back to pool."""
        key = proxy.url
        async with self._lock:
            if key in self._proxies:
                self._proxies[key].in_use = False

    async def mark_proxy_status(
        self,
        proxy: ProxyConfig,
        status: ProxyStatus,
    ) -> None:
        """Update proxy status."""
        key = proxy.url
        async with self._lock:
            if key in self._proxies:
                entry = self._proxies[key]
                entry.status = status

                if status in (ProxyStatus.INVALID, ProxyStatus.BANNED):
                    entry.fail_count += 1
                    if key in self._available:
                        self._available.remove(key)

    async def validate_proxy(self, proxy: ProxyConfig) -> ProxyStatus:
        """Validate proxy connectivity."""
        try:
            timeout = aiohttp.ClientTimeout(total=self._validation_timeout)
            connector = aiohttp.TCPConnector(ssl=False)

            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
            ) as session:
                async with session.get(
                    "https://httpbin.org/ip",
                    proxy=proxy.url,
                ) as response:
                    if response.status == 200:
                        return ProxyStatus.VALID
                    return ProxyStatus.INVALID
        except asyncio.TimeoutError:
            return ProxyStatus.SLOW
        except Exception:
            return ProxyStatus.INVALID

    async def validate_all(self) -> dict[ProxyStatus, int]:
        """Validate all proxies concurrently."""

        async def validate_one(key: str) -> tuple[str, ProxyStatus]:
            entry = self._proxies[key]
            status = await self.validate_proxy(entry.config)
            return key, status

        tasks = [validate_one(key) for key in list(self._proxies.keys())]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        stats: dict[ProxyStatus, int] = {status: 0 for status in ProxyStatus}

        async with self._lock:
            for result in results:
                if isinstance(result, Exception):
                    continue
                key, status = result
                if key in self._proxies:
                    self._proxies[key].status = status
                    stats[status] += 1

                    if status == ProxyStatus.VALID:
                        if key not in self._available:
                            self._available.append(key)
                    else:
                        if key in self._available:
                            self._available.remove(key)

        return stats

    async def get_stats(self) -> dict[str, int]:
        """Get proxy pool statistics."""
        async with self._lock:
            status_counts = {status.value: 0 for status in ProxyStatus}
            for entry in self._proxies.values():
                status_counts[entry.status.value] += 1

            return {
                "total": len(self._proxies),
                "available": len(self._available),
                "in_use": sum(1 for e in self._proxies.values() if e.in_use),
                **status_counts,
            }

    async def remove_invalid(self) -> int:
        """Remove all invalid proxies."""
        async with self._lock:
            to_remove = [
                key
                for key, entry in self._proxies.items()
                if entry.status in (ProxyStatus.INVALID, ProxyStatus.BANNED)
            ]

            for key in to_remove:
                del self._proxies[key]
                if key in self._available:
                    self._available.remove(key)

            return len(to_remove)
