"""Domain models for antidetect-playwright."""

from .browser_profile import BrowserProfile
from .fingerprint import (
    Fingerprint,
    ScreenResolution,
    WebGLConfig,
    NavigatorConfig,
    CanvasConfig,
    AudioConfig,
)
from .proxy import ProxyConfig, ProxyProtocol, ProxyStatus
from .task import Task, TaskResult, TaskStatus

__all__ = [
    "BrowserProfile",
    "Fingerprint",
    "ScreenResolution",
    "WebGLConfig",
    "NavigatorConfig",
    "CanvasConfig",
    "AudioConfig",
    "ProxyConfig",
    "ProxyProtocol",
    "ProxyStatus",
    "Task",
    "TaskResult",
    "TaskStatus",
]
