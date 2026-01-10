"""Data models for antidetect browser profiles."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class ProfileStatus(Enum):
    """Profile browser status."""

    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


class ProxyType(Enum):
    """Proxy protocol types."""

    NONE = "none"
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


@dataclass
class ProxyConfig:
    """Proxy configuration - the only user input needed."""

    enabled: bool = False
    proxy_type: ProxyType = ProxyType.NONE
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    # Auto-detected from proxy IP
    country_code: str = ""
    country_name: str = ""
    city: str = ""
    timezone: str = ""

    # Ping result
    ping_ms: int = -1
    last_ping: datetime | None = None

    def to_url(self) -> str | None:
        """Convert to proxy URL string."""
        if not self.enabled or self.proxy_type == ProxyType.NONE:
            return None
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"

    def to_camoufox(self) -> dict | None:
        """Convert to Camoufox proxy format."""
        if not self.enabled or self.proxy_type == ProxyType.NONE:
            return None
        proxy = {"server": f"{self.proxy_type.value}://{self.host}:{self.port}"}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy

    def display_string(self) -> str:
        """Display string for UI."""
        if not self.enabled or self.proxy_type == ProxyType.NONE:
            return "No proxy"
        return f"{self.host}:{self.port}"


@dataclass
class BrowserProfile:
    """Browser profile with auto-configured fingerprint."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Profile"
    folder_id: str = ""  # Empty = root folder

    # Status
    status: ProfileStatus = ProfileStatus.STOPPED

    # Only user input needed - proxy
    proxy: ProxyConfig = field(default_factory=ProxyConfig)

    # Organization
    notes: str = ""
    tags: list[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime | None = None

    # OS for icon display (auto-detected or user choice)
    os_type: str = "macos"  # windows, macos, linux

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "folder_id": self.folder_id,
            "status": self.status.value,
            "proxy": {
                "enabled": self.proxy.enabled,
                "proxy_type": self.proxy.proxy_type.value,
                "host": self.proxy.host,
                "port": self.proxy.port,
                "username": self.proxy.username,
                "password": self.proxy.password,
                "country_code": self.proxy.country_code,
                "country_name": self.proxy.country_name,
                "city": self.proxy.city,
                "timezone": self.proxy.timezone,
                "ping_ms": self.proxy.ping_ms,
            },
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "os_type": self.os_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrowserProfile":
        """Deserialize from dictionary."""
        proxy_data = data.get("proxy", {})
        proxy = ProxyConfig(
            enabled=proxy_data.get("enabled", False),
            proxy_type=ProxyType(proxy_data.get("proxy_type", "none")),
            host=proxy_data.get("host", ""),
            port=proxy_data.get("port", 0),
            username=proxy_data.get("username", ""),
            password=proxy_data.get("password", ""),
            country_code=proxy_data.get("country_code", ""),
            country_name=proxy_data.get("country_name", ""),
            city=proxy_data.get("city", ""),
            timezone=proxy_data.get("timezone", ""),
            ping_ms=proxy_data.get("ping_ms", -1),
        )

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "New Profile"),
            folder_id=data.get("folder_id", ""),
            status=ProfileStatus(data.get("status", "stopped")),
            proxy=proxy,
            notes=data.get("notes", ""),
            tags=data.get("tags", []),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now()
            ),
            last_used=(
                datetime.fromisoformat(data["last_used"])
                if data.get("last_used")
                else None
            ),
            os_type=data.get("os_type", "macos"),
        )


@dataclass
class Folder:
    """Folder for organizing profiles."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Folder"
    color: str = "#6366f1"  # Indigo default

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict) -> "Folder":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "New Folder"),
            color=data.get("color", "#6366f1"),
        )


@dataclass
class ProxyPool:
    """Pool of proxies for quick rotation."""

    proxies: list[ProxyConfig] = field(default_factory=list)
    current_index: int = 0

    def next_proxy(self) -> ProxyConfig | None:
        """Get next proxy from pool (round-robin)."""
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def add_proxy(self, proxy: ProxyConfig) -> None:
        """Add proxy to pool."""
        self.proxies.append(proxy)


@dataclass
class AppSettings:
    """Application settings stored locally."""

    items_per_page: int = 25
    selected_folder: str = ""  # Empty = all profiles
    selected_tags: list[str] = field(default_factory=list)
    window_width: int = 1400
    window_height: int = 800
    window_x: int = -1  # -1 = center on screen
    window_y: int = -1
    sidebar_width: int = 220

    def to_dict(self) -> dict:
        return {
            "items_per_page": self.items_per_page,
            "selected_folder": self.selected_folder,
            "selected_tags": self.selected_tags,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "sidebar_width": self.sidebar_width,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        return cls(
            items_per_page=data.get("items_per_page", 25),
            selected_folder=data.get("selected_folder", ""),
            selected_tags=data.get("selected_tags", []),
            window_width=data.get("window_width", 1400),
            window_height=data.get("window_height", 800),
            window_x=data.get("window_x", -1),
            window_y=data.get("window_y", -1),
            sidebar_width=data.get("sidebar_width", 220),
        )
