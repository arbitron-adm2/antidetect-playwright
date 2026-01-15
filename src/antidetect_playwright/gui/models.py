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
            # Password stored in plain text in memory for runtime use
            proxy["password"] = self.password
        return proxy

    def to_dict(self, encrypt_password: bool = True) -> dict:
        """Serialize to dict with optional password encryption.

        Args:
            encrypt_password: If True, encrypt password using Fernet

        Returns:
            Dict representation
        """
        from .security import SecurePasswordEncryption

        password = self.password
        if encrypt_password and password:
            try:
                password = SecurePasswordEncryption.encrypt(password)
            except Exception as e:
                # Log error but don't fail - worst case password stored in plaintext
                import logging

                logging.getLogger(__name__).error(f"Failed to encrypt password: {e}")

        return {
            "enabled": self.enabled,
            "proxy_type": self.proxy_type.value,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": password,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "city": self.city,
            "timezone": self.timezone,
            "ping_ms": self.ping_ms,
        }

    @classmethod
    def from_dict(cls, data: dict, decrypt_password: bool = True) -> "ProxyConfig":
        """Deserialize from dict with optional password decryption.

        Args:
            data: Dict representation
            decrypt_password: If True, decrypt password using Fernet

        Returns:
            ProxyConfig instance
        """
        from .security import SecurePasswordEncryption

        password = data.get("password", "")
        if decrypt_password and password:
            try:
                password = SecurePasswordEncryption.decrypt(password)
            except Exception as e:
                # If decryption fails, assume it's plaintext (migration)
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to decrypt password, using as-is: {e}"
                )

        return cls(
            enabled=data.get("enabled", False),
            proxy_type=ProxyType(data.get("proxy_type", "none")),
            host=data.get("host", ""),
            port=data.get("port", 0),
            username=data.get("username", ""),
            password=password,
            country_code=data.get("country_code", ""),
            country_name=data.get("country_name", ""),
            city=data.get("city", ""),
            timezone=data.get("timezone", ""),
            ping_ms=data.get("ping_ms", -1),
        )

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
        """Serialize to dictionary with encrypted proxy password."""
        return {
            "id": self.id,
            "name": self.name,
            "folder_id": self.folder_id,
            "status": self.status.value,
            "proxy": self.proxy.to_dict(encrypt_password=True),
            "notes": self.notes,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "os_type": self.os_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BrowserProfile":
        """Deserialize from dictionary with decrypted proxy password."""
        proxy_data = data.get("proxy", {})
        proxy = ProxyConfig.from_dict(proxy_data, decrypt_password=True)

        status_value = data.get("status", "stopped")
        if status_value == "stopping":
            status_value = "stopped"

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "New Profile"),
            folder_id=data.get("folder_id", ""),
            status=ProfileStatus(status_value),
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

    # Browser settings
    save_tabs: bool = True
    start_page: str = "about:blank"

    # Performance settings
    block_images: bool = False
    enable_cache: bool = True

    # Privacy settings
    humanize: float = 1.5

    # Extensions
    exclude_ublock: bool = False
    exclude_bpc: bool = False
    custom_addons: list[str] = field(default_factory=list)

    # Custom browser path (empty = use bundled Camoufox)
    browser_executable_path: str = ""

    # Debug
    debug_mode: bool = False

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
            "save_tabs": self.save_tabs,
            "start_page": self.start_page,
            "block_images": self.block_images,
            "enable_cache": self.enable_cache,
            "humanize": self.humanize,
            "exclude_ublock": self.exclude_ublock,
            "exclude_bpc": self.exclude_bpc,
            "custom_addons": self.custom_addons,
            "browser_executable_path": self.browser_executable_path,
            "debug_mode": self.debug_mode,
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
            save_tabs=data.get("save_tabs", True),
            start_page=data.get("start_page", "about:blank"),
            block_images=data.get("block_images", False),
            enable_cache=data.get("enable_cache", True),
            humanize=data.get("humanize", 1.5),
            exclude_ublock=data.get("exclude_ublock", False),
            exclude_bpc=data.get("exclude_bpc", False),
            custom_addons=data.get("custom_addons", []),
            browser_executable_path=data.get("browser_executable_path", ""),
            debug_mode=data.get("debug_mode", False),
        )
