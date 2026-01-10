"""Browser profile domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .fingerprint import Fingerprint
from .proxy import ProxyConfig


@dataclass(slots=True)
class BrowserProfile:
    """Browser profile with fingerprint and state."""

    id: str
    fingerprint: Fingerprint
    proxy: ProxyConfig | None
    storage_path: str
    created_at: datetime
    last_used_at: datetime | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    local_storage: dict[str, str] = field(default_factory=dict)
    session_storage: dict[str, str] = field(default_factory=dict)

    def mark_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now()

    def to_context_options(self) -> dict[str, Any]:
        """Convert profile to Playwright browser context options."""
        injection_data = self.fingerprint.to_injection_data()

        options: dict[str, Any] = {
            "viewport": {
                "width": self.fingerprint.screen.width,
                "height": self.fingerprint.screen.height,
            },
            "user_agent": self.fingerprint.navigator.user_agent,
            "locale": self.fingerprint.navigator.language,
            "timezone_id": self.fingerprint.timezone,
            "color_scheme": "light",
            "device_scale_factor": 1.0,
            "has_touch": self.fingerprint.navigator.max_touch_points > 0,
            "is_mobile": False,
            "storage_state": {
                "cookies": self.cookies,
                "origins": (
                    [
                        {
                            "origin": origin,
                            "localStorage": [
                                {"name": k, "value": v}
                                for k, v in self.local_storage.items()
                            ],
                        }
                        for origin in set(
                            c.get("domain", "") for c in self.cookies if c.get("domain")
                        )
                    ]
                    if self.local_storage
                    else []
                ),
            },
        }

        if self.proxy:
            options["proxy"] = self.proxy.to_playwright_proxy()

        return options
