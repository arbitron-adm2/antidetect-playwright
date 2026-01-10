"""Fingerprint generator interface."""

from abc import ABC, abstractmethod

from ..models import Fingerprint


class FingerprintGeneratorPort(ABC):
    """Interface for fingerprint generation."""

    @abstractmethod
    def generate(self) -> Fingerprint:
        """Generate a new consistent fingerprint.

        Returns:
            Complete fingerprint with all properties consistent.
        """
        ...

    @abstractmethod
    def generate_for_platform(self, platform: str) -> Fingerprint:
        """Generate fingerprint for specific platform.

        Args:
            platform: Target platform (Win32, Linux x86_64, MacIntel).

        Returns:
            Fingerprint consistent with platform.
        """
        ...

    @abstractmethod
    def generate_mobile(self) -> Fingerprint:
        """Generate mobile device fingerprint.

        Returns:
            Fingerprint for mobile device.
        """
        ...

    @abstractmethod
    def validate(self, fingerprint: Fingerprint) -> bool:
        """Validate fingerprint consistency.

        Args:
            fingerprint: Fingerprint to validate.

        Returns:
            True if fingerprint is internally consistent.
        """
        ...
