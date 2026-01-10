"""Domain layer - business logic and models."""

from .models import (
    BrowserProfile,
    Fingerprint,
    ScreenResolution,
    WebGLConfig,
    ProxyConfig,
    ProxyProtocol,
    ProxyStatus,
    Task,
    TaskResult,
    TaskStatus,
)
from .interfaces import (
    BrowserPoolPort,
    FingerprintGeneratorPort,
    ProxyManagerPort,
    TaskQueuePort,
    ProfileStoragePort,
)

__all__ = [
    "BrowserProfile",
    "Fingerprint",
    "ScreenResolution",
    "WebGLConfig",
    "ProxyConfig",
    "ProxyProtocol",
    "ProxyStatus",
    "Task",
    "TaskResult",
    "TaskStatus",
    "BrowserPoolPort",
    "FingerprintGeneratorPort",
    "ProxyManagerPort",
    "TaskQueuePort",
    "ProfileStoragePort",
]
