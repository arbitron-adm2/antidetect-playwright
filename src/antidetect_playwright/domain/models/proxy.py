"""Proxy domain model."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProxyProtocol(Enum):
    """Supported proxy protocols."""

    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(Enum):
    """Proxy health status."""

    UNKNOWN = "unknown"
    VALID = "valid"
    INVALID = "invalid"
    SLOW = "slow"
    BANNED = "banned"


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    """Proxy server configuration."""

    host: str
    port: int
    protocol: ProxyProtocol
    username: str | None = None
    password: str | None = None

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("Host cannot be empty")
        if not 1 <= self.port <= 65535:
            raise ValueError("Port must be between 1 and 65535")

    @property
    def requires_auth(self) -> bool:
        """Check if proxy requires authentication."""
        return self.username is not None and self.password is not None

    @property
    def url(self) -> str:
        """Get proxy URL string."""
        if self.requires_auth:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol.value}://{self.host}:{self.port}"

    @property
    def server_url(self) -> str:
        """Get proxy server URL without credentials."""
        return f"{self.protocol.value}://{self.host}:{self.port}"

    def to_playwright_proxy(self) -> dict[str, Any]:
        """Convert to Playwright proxy configuration."""
        proxy: dict[str, Any] = {
            "server": self.server_url,
        }
        if self.requires_auth:
            proxy["username"] = self.username
            proxy["password"] = self.password
        return proxy

    @classmethod
    def from_url(cls, url: str) -> "ProxyConfig":
        """Parse proxy from URL string."""
        import re

        pattern = r"^(?P<protocol>https?|socks[45])://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^:]+):(?P<port>\d+)$"
        match = re.match(pattern, url)

        if not match:
            raise ValueError(f"Invalid proxy URL format: {url}")

        return cls(
            host=match.group("host"),
            port=int(match.group("port")),
            protocol=ProxyProtocol(match.group("protocol")),
            username=match.group("user"),
            password=match.group("pass"),
        )

    @classmethod
    def from_line(
        cls, line: str, default_protocol: ProxyProtocol = ProxyProtocol.HTTP
    ) -> "ProxyConfig":
        """Parse proxy from simple format: host:port or host:port:user:pass."""
        parts = line.strip().split(":")

        if len(parts) == 2:
            return cls(
                host=parts[0],
                port=int(parts[1]),
                protocol=default_protocol,
            )
        elif len(parts) == 4:
            return cls(
                host=parts[0],
                port=int(parts[1]),
                protocol=default_protocol,
                username=parts[2],
                password=parts[3],
            )
        else:
            raise ValueError(f"Invalid proxy line format: {line}")
