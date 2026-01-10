"""Profile storage interface."""

from abc import ABC, abstractmethod
from typing import Sequence

from ..models import BrowserProfile


class ProfileStoragePort(ABC):
    """Interface for browser profile persistence."""

    @abstractmethod
    async def save(self, profile: BrowserProfile) -> None:
        """Save profile to storage.

        Args:
            profile: Profile to save.
        """
        ...

    @abstractmethod
    async def load(self, profile_id: str) -> BrowserProfile | None:
        """Load profile from storage.

        Args:
            profile_id: Profile identifier.

        Returns:
            Profile or None if not found.
        """
        ...

    @abstractmethod
    async def delete(self, profile_id: str) -> bool:
        """Delete profile from storage.

        Args:
            profile_id: Profile identifier.

        Returns:
            True if profile was deleted.
        """
        ...

    @abstractmethod
    async def list_all(
        self, limit: int = 100, offset: int = 0
    ) -> Sequence[BrowserProfile]:
        """List all profiles.

        Args:
            limit: Maximum number of profiles.
            offset: Offset for pagination.

        Returns:
            List of profiles.
        """
        ...

    @abstractmethod
    async def count(self) -> int:
        """Get total profile count."""
        ...

    @abstractmethod
    async def exists(self, profile_id: str) -> bool:
        """Check if profile exists.

        Args:
            profile_id: Profile identifier.

        Returns:
            True if profile exists.
        """
        ...

    @abstractmethod
    async def update_cookies(
        self,
        profile_id: str,
        cookies: list[dict],
    ) -> None:
        """Update profile cookies.

        Args:
            profile_id: Profile identifier.
            cookies: New cookies list.
        """
        ...

    @abstractmethod
    async def update_storage(
        self,
        profile_id: str,
        local_storage: dict[str, str],
        session_storage: dict[str, str],
    ) -> None:
        """Update profile storage data.

        Args:
            profile_id: Profile identifier.
            local_storage: Local storage data.
            session_storage: Session storage data.
        """
        ...
