"""File-based profile storage implementation."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from ..domain.interfaces import ProfileStoragePort
from ..domain.models import (
    BrowserProfile,
    Fingerprint,
    ScreenResolution,
    NavigatorConfig,
    WebGLConfig,
    CanvasConfig,
    AudioConfig,
    ProxyConfig,
    ProxyProtocol,
)


class FileProfileStorage(ProfileStoragePort):
    """File-based profile persistence."""

    def __init__(self, storage_path: str) -> None:
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)

    def _profile_path(self, profile_id: str) -> Path:
        """Get profile file path."""
        return self._storage_path / f"{profile_id}.json"

    def _serialize_profile(self, profile: BrowserProfile) -> dict:
        """Serialize profile to dict."""
        fp = profile.fingerprint

        data = {
            "id": profile.id,
            "storage_path": profile.storage_path,
            "created_at": profile.created_at.isoformat(),
            "last_used_at": (
                profile.last_used_at.isoformat() if profile.last_used_at else None
            ),
            "cookies": profile.cookies,
            "local_storage": profile.local_storage,
            "session_storage": profile.session_storage,
            "fingerprint": {
                "id": fp.id,
                "screen": {
                    "width": fp.screen.width,
                    "height": fp.screen.height,
                },
                "navigator": {
                    "user_agent": fp.navigator.user_agent,
                    "platform": fp.navigator.platform,
                    "language": fp.navigator.language,
                    "languages": list(fp.navigator.languages),
                    "hardware_concurrency": fp.navigator.hardware_concurrency,
                    "device_memory": fp.navigator.device_memory,
                    "max_touch_points": fp.navigator.max_touch_points,
                    "vendor": fp.navigator.vendor,
                },
                "timezone": fp.timezone,
                "webgl": {
                    "vendor": fp.webgl.vendor,
                    "renderer": fp.webgl.renderer,
                    "unmasked_vendor": fp.webgl.unmasked_vendor,
                    "unmasked_renderer": fp.webgl.unmasked_renderer,
                },
                "canvas": {
                    "noise_r": fp.canvas.noise_r,
                    "noise_g": fp.canvas.noise_g,
                    "noise_b": fp.canvas.noise_b,
                    "noise_a": fp.canvas.noise_a,
                },
                "audio": {
                    "sample_rate": fp.audio.sample_rate,
                    "noise_factor": fp.audio.noise_factor,
                },
                "fonts": list(fp.fonts),
                "plugins": list(fp.plugins),
            },
        }

        if profile.proxy:
            data["proxy"] = {
                "host": profile.proxy.host,
                "port": profile.proxy.port,
                "protocol": profile.proxy.protocol.value,
                "username": profile.proxy.username,
                "password": profile.proxy.password,
            }
        else:
            data["proxy"] = None

        return data

    def _deserialize_profile(self, data: dict) -> BrowserProfile:
        """Deserialize profile from dict."""
        fp_data = data["fingerprint"]

        fingerprint = Fingerprint(
            id=fp_data["id"],
            screen=ScreenResolution(
                width=fp_data["screen"]["width"],
                height=fp_data["screen"]["height"],
            ),
            navigator=NavigatorConfig(
                user_agent=fp_data["navigator"]["user_agent"],
                platform=fp_data["navigator"]["platform"],
                language=fp_data["navigator"]["language"],
                languages=tuple(fp_data["navigator"]["languages"]),
                hardware_concurrency=fp_data["navigator"]["hardware_concurrency"],
                device_memory=fp_data["navigator"]["device_memory"],
                max_touch_points=fp_data["navigator"]["max_touch_points"],
                vendor=fp_data["navigator"]["vendor"],
            ),
            timezone=fp_data["timezone"],
            webgl=WebGLConfig(
                vendor=fp_data["webgl"]["vendor"],
                renderer=fp_data["webgl"]["renderer"],
                unmasked_vendor=fp_data["webgl"]["unmasked_vendor"],
                unmasked_renderer=fp_data["webgl"]["unmasked_renderer"],
            ),
            canvas=CanvasConfig(
                noise_r=fp_data["canvas"]["noise_r"],
                noise_g=fp_data["canvas"]["noise_g"],
                noise_b=fp_data["canvas"]["noise_b"],
                noise_a=fp_data["canvas"]["noise_a"],
            ),
            audio=AudioConfig(
                sample_rate=fp_data["audio"]["sample_rate"],
                noise_factor=fp_data["audio"]["noise_factor"],
            ),
            fonts=tuple(fp_data["fonts"]),
            plugins=tuple(fp_data["plugins"]),
        )

        proxy = None
        if data.get("proxy"):
            proxy_data = data["proxy"]
            proxy = ProxyConfig(
                host=proxy_data["host"],
                port=proxy_data["port"],
                protocol=ProxyProtocol(proxy_data["protocol"]),
                username=proxy_data.get("username"),
                password=proxy_data.get("password"),
            )

        return BrowserProfile(
            id=data["id"],
            fingerprint=fingerprint,
            proxy=proxy,
            storage_path=data["storage_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_used_at=(
                datetime.fromisoformat(data["last_used_at"])
                if data.get("last_used_at")
                else None
            ),
            cookies=data.get("cookies", []),
            local_storage=data.get("local_storage", {}),
            session_storage=data.get("session_storage", {}),
        )

    async def save(self, profile: BrowserProfile) -> None:
        """Save profile to file."""
        data = self._serialize_profile(profile)
        path = self._profile_path(profile.id)
        path.write_text(json.dumps(data, indent=2))

    async def load(self, profile_id: str) -> BrowserProfile | None:
        """Load profile from file."""
        path = self._profile_path(profile_id)
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        return self._deserialize_profile(data)

    async def delete(self, profile_id: str) -> bool:
        """Delete profile file."""
        path = self._profile_path(profile_id)
        if path.exists():
            path.unlink()
            return True
        return False

    async def list_all(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[BrowserProfile]:
        """List all profiles."""
        profiles = []
        files = sorted(self._storage_path.glob("*.json"))

        for file in files[offset : offset + limit]:
            data = json.loads(file.read_text())
            profiles.append(self._deserialize_profile(data))

        return profiles

    async def count(self) -> int:
        """Get total profile count."""
        return len(list(self._storage_path.glob("*.json")))

    async def exists(self, profile_id: str) -> bool:
        """Check if profile exists."""
        return self._profile_path(profile_id).exists()

    async def update_cookies(
        self,
        profile_id: str,
        cookies: list[dict],
    ) -> None:
        """Update profile cookies."""
        profile = await self.load(profile_id)
        if profile:
            profile.cookies = cookies
            await self.save(profile)

    async def update_storage(
        self,
        profile_id: str,
        local_storage: dict[str, str],
        session_storage: dict[str, str],
    ) -> None:
        """Update profile storage data."""
        profile = await self.load(profile_id)
        if profile:
            profile.local_storage = local_storage
            profile.session_storage = session_storage
            await self.save(profile)
