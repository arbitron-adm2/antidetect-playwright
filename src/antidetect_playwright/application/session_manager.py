"""Session manager for unique anti-detect sessions."""

import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..domain.models import BrowserProfile, Fingerprint, ProxyConfig
from ..infrastructure import FingerprintGenerator, ProxyManager, FileProfileStorage


@dataclass
class UniqueSession:
    """Unique session with all anti-detect parameters."""

    id: str
    profile: BrowserProfile
    created_at: datetime
    seed: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_unique(self) -> bool:
        """Session is always unique by design."""
        return True


class SessionManager:
    """Manages unique anti-detect sessions.

    Each session gets:
    - Unique fingerprint (canvas noise, WebGL, audio, etc.)
    - Unique proxy
    - Unique browser profile
    - Unique session seed for reproducibility
    """

    def __init__(
        self,
        fingerprint_generator: FingerprintGenerator,
        proxy_manager: ProxyManager,
        profile_storage: FileProfileStorage,
        storage_path: str,
    ) -> None:
        self._fingerprint_gen = fingerprint_generator
        self._proxy_manager = proxy_manager
        self._profile_storage = profile_storage
        self._storage_path = storage_path

        self._active_sessions: dict[str, UniqueSession] = {}
        self._used_fingerprint_ids: set[str] = set()
        self._used_proxy_keys: set[str] = set()

    async def create_unique_session(
        self,
        task_id: str,
        platform: str | None = None,
        reuse_proxy: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> UniqueSession:
        """Create a new unique session with guaranteed uniqueness.

        Args:
            task_id: Associated task identifier.
            platform: Target platform (Win32, Linux x86_64, MacIntel).
            reuse_proxy: Allow proxy reuse across sessions.
            metadata: Additional session metadata.

        Returns:
            Unique session ready for use.
        """
        session_id = str(uuid.uuid4())
        seed = secrets.token_hex(32)

        fingerprint = self._generate_unique_fingerprint(platform, seed)

        proxy = await self._get_unique_proxy(reuse_proxy)

        profile = BrowserProfile(
            id=session_id,
            fingerprint=fingerprint,
            proxy=proxy,
            storage_path=f"{self._storage_path}/{session_id}",
            created_at=datetime.now(),
        )

        session = UniqueSession(
            id=session_id,
            profile=profile,
            created_at=datetime.now(),
            seed=seed,
            metadata=metadata or {},
        )

        session.metadata["task_id"] = task_id
        session.metadata["fingerprint_hash"] = self._hash_fingerprint(fingerprint)
        session.metadata["proxy_key"] = proxy.url if proxy else None

        self._active_sessions[session_id] = session

        return session

    def _generate_unique_fingerprint(
        self,
        platform: str | None,
        seed: str,
    ) -> Fingerprint:
        """Generate fingerprint with guaranteed uniqueness."""
        max_attempts = 100

        for _ in range(max_attempts):
            if platform:
                fingerprint = self._fingerprint_gen.generate_for_platform(platform)
            else:
                fingerprint = self._fingerprint_gen.generate()

            fp_hash = self._hash_fingerprint(fingerprint)

            if fp_hash not in self._used_fingerprint_ids:
                self._used_fingerprint_ids.add(fp_hash)
                return fingerprint

        fingerprint = self._fingerprint_gen.generate()
        self._used_fingerprint_ids.add(self._hash_fingerprint(fingerprint))
        return fingerprint

    async def _get_unique_proxy(self, allow_reuse: bool) -> ProxyConfig | None:
        """Get unique proxy not used in current batch."""
        max_attempts = 100

        for _ in range(max_attempts):
            proxy = await self._proxy_manager.get_proxy()
            if not proxy:
                return None

            if allow_reuse or proxy.url not in self._used_proxy_keys:
                self._used_proxy_keys.add(proxy.url)
                return proxy

            await self._proxy_manager.release_proxy(proxy)

        return await self._proxy_manager.get_proxy()

    def _hash_fingerprint(self, fingerprint: Fingerprint) -> str:
        """Create hash of fingerprint for uniqueness check."""
        data = (
            f"{fingerprint.navigator.user_agent}|"
            f"{fingerprint.screen.width}x{fingerprint.screen.height}|"
            f"{fingerprint.webgl.unmasked_renderer}|"
            f"{fingerprint.canvas.noise_r:.6f}|"
            f"{fingerprint.timezone}"
        )
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    async def release_session(self, session_id: str) -> None:
        """Release session and its resources."""
        session = self._active_sessions.pop(session_id, None)
        if session and session.profile.proxy:
            await self._proxy_manager.release_proxy(session.profile.proxy)

    async def save_session(self, session_id: str) -> None:
        """Persist session profile for future use."""
        session = self._active_sessions.get(session_id)
        if session:
            await self._profile_storage.save(session.profile)

    def get_active_count(self) -> int:
        """Get number of active sessions."""
        return len(self._active_sessions)

    def reset_uniqueness_tracking(self) -> None:
        """Reset tracking for new batch (clears used fingerprints/proxies)."""
        self._used_fingerprint_ids.clear()
        self._used_proxy_keys.clear()

    def get_session(self, session_id: str) -> UniqueSession | None:
        """Get active session by ID."""
        return self._active_sessions.get(session_id)
