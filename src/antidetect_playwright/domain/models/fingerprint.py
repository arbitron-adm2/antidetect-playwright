"""Fingerprint domain model."""

from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ScreenResolution:
    """Screen resolution configuration."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise ValueError("Width must be positive")
        if self.height <= 0:
            raise ValueError("Height must be positive")


@dataclass(frozen=True, slots=True)
class WebGLConfig:
    """WebGL fingerprint configuration."""

    vendor: str
    renderer: str
    unmasked_vendor: str
    unmasked_renderer: str


@dataclass(frozen=True, slots=True)
class AudioConfig:
    """Audio context fingerprint configuration."""

    sample_rate: int
    noise_factor: float

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        if not 0 <= self.noise_factor <= 1:
            raise ValueError("Noise factor must be between 0 and 1")


@dataclass(frozen=True, slots=True)
class CanvasConfig:
    """Canvas fingerprint configuration."""

    noise_r: float
    noise_g: float
    noise_b: float
    noise_a: float

    def __post_init__(self) -> None:
        for noise in (self.noise_r, self.noise_g, self.noise_b, self.noise_a):
            if not -1 <= noise <= 1:
                raise ValueError("Noise values must be between -1 and 1")


@dataclass(frozen=True, slots=True)
class NavigatorConfig:
    """Navigator properties configuration."""

    user_agent: str
    platform: str
    language: str
    languages: tuple[str, ...]
    hardware_concurrency: int
    device_memory: int
    max_touch_points: int
    vendor: str

    def __post_init__(self) -> None:
        if self.hardware_concurrency <= 0:
            raise ValueError("Hardware concurrency must be positive")
        if self.device_memory <= 0:
            raise ValueError("Device memory must be positive")
        if self.max_touch_points < 0:
            raise ValueError("Max touch points cannot be negative")


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """Complete browser fingerprint configuration."""

    id: str
    screen: ScreenResolution
    navigator: NavigatorConfig
    timezone: str
    webgl: WebGLConfig
    canvas: CanvasConfig
    audio: AudioConfig
    fonts: tuple[str, ...]
    plugins: tuple[str, ...]

    def to_injection_data(self) -> dict:
        """Convert fingerprint to injection-ready data structure."""
        return {
            "screen": {
                "width": self.screen.width,
                "height": self.screen.height,
                "availWidth": self.screen.width,
                "availHeight": self.screen.height - 40,
                "colorDepth": 24,
                "pixelDepth": 24,
            },
            "navigator": {
                "userAgent": self.navigator.user_agent,
                "platform": self.navigator.platform,
                "language": self.navigator.language,
                "languages": list(self.navigator.languages),
                "hardwareConcurrency": self.navigator.hardware_concurrency,
                "deviceMemory": self.navigator.device_memory,
                "maxTouchPoints": self.navigator.max_touch_points,
                "vendor": self.navigator.vendor,
            },
            "timezone": self.timezone,
            "webgl": {
                "vendor": self.webgl.vendor,
                "renderer": self.webgl.renderer,
                "unmaskedVendor": self.webgl.unmasked_vendor,
                "unmaskedRenderer": self.webgl.unmasked_renderer,
            },
            "canvas": {
                "noiseR": self.canvas.noise_r,
                "noiseG": self.canvas.noise_g,
                "noiseB": self.canvas.noise_b,
                "noiseA": self.canvas.noise_a,
            },
            "audio": {
                "sampleRate": self.audio.sample_rate,
                "noiseFactor": self.audio.noise_factor,
            },
            "fonts": list(self.fonts),
            "plugins": list(self.plugins),
        }
