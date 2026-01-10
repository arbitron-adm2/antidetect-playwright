"""Domain interfaces (ports)."""

from .browser_pool import BrowserPoolPort
from .fingerprint_generator import FingerprintGeneratorPort
from .proxy_manager import ProxyManagerPort
from .task_queue import TaskQueuePort
from .profile_storage import ProfileStoragePort

__all__ = [
    "BrowserPoolPort",
    "FingerprintGeneratorPort",
    "ProxyManagerPort",
    "TaskQueuePort",
    "ProfileStoragePort",
]
