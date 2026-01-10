"""Fingerprint generator implementation."""

import hashlib
import random
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from ..domain.interfaces import FingerprintGeneratorPort
from ..domain.models import (
    Fingerprint,
    ScreenResolution,
    NavigatorConfig,
    WebGLConfig,
    CanvasConfig,
    AudioConfig,
)


@dataclass(frozen=True)
class PlatformProfile:
    """Platform-specific fingerprint template."""

    platform: str
    vendor: str
    user_agent_template: str
    webgl_vendors: tuple[str, ...]
    webgl_renderers: tuple[str, ...]
    device_memories: tuple[int, ...]
    hardware_concurrencies: tuple[int, ...]


PLATFORM_PROFILES = {
    "Win32": PlatformProfile(
        platform="Win32",
        vendor="Google Inc.",
        user_agent_template="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36",
        webgl_vendors=(
            "Google Inc. (NVIDIA)",
            "Google Inc. (AMD)",
            "Google Inc. (Intel)",
        ),
        webgl_renderers=(
            "ANGLE (NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA GeForce GTX 1660 Super Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
        ),
        device_memories=(4, 8, 16, 32),
        hardware_concurrencies=(4, 6, 8, 12, 16),
    ),
    "Linux x86_64": PlatformProfile(
        platform="Linux x86_64",
        vendor="Google Inc.",
        user_agent_template="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36",
        webgl_vendors=(
            "Google Inc. (NVIDIA Corporation)",
            "Google Inc. (AMD)",
            "Google Inc. (Intel)",
        ),
        webgl_renderers=(
            "ANGLE (NVIDIA Corporation NVIDIA GeForce RTX 3070/PCIe/SSE2)",
            "ANGLE (AMD Radeon RX 580 Series)",
            "ANGLE (Mesa Intel(R) UHD Graphics 630 (CFL GT2))",
        ),
        device_memories=(4, 8, 16, 32),
        hardware_concurrencies=(4, 6, 8, 12, 16),
    ),
    "MacIntel": PlatformProfile(
        platform="MacIntel",
        vendor="Google Inc.",
        user_agent_template="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36",
        webgl_vendors=(
            "Google Inc. (Apple)",
            "Google Inc. (AMD)",
            "Google Inc. (Intel Inc.)",
        ),
        webgl_renderers=(
            "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)",
            "ANGLE (Apple, Apple M2, OpenGL 4.1)",
            "ANGLE (AMD, AMD Radeon Pro 5500M OpenGL Engine, OpenGL 4.1)",
            "ANGLE (Intel Inc., Intel(R) Iris(TM) Plus Graphics 640, OpenGL 4.1)",
        ),
        device_memories=(8, 16, 32),
        hardware_concurrencies=(8, 10, 12),
    ),
}

CHROME_VERSIONS = (
    "120.0.6099.109",
    "121.0.6167.85",
    "122.0.6261.57",
    "123.0.6312.86",
    "124.0.6367.60",
)

LANGUAGES = (
    ("en-US", ("en-US", "en")),
    ("en-GB", ("en-GB", "en")),
    ("de-DE", ("de-DE", "de", "en")),
    ("fr-FR", ("fr-FR", "fr", "en")),
    ("es-ES", ("es-ES", "es", "en")),
)

TIMEZONES = (
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Paris",
    "Asia/Tokyo",
    "Asia/Singapore",
)

FONTS = (
    "Arial",
    "Arial Black",
    "Comic Sans MS",
    "Courier New",
    "Georgia",
    "Impact",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
    "Webdings",
)

PLUGINS = (
    "Chrome PDF Plugin",
    "Chrome PDF Viewer",
    "Native Client",
)


class FingerprintGenerator(FingerprintGeneratorPort):
    """Generates consistent browser fingerprints."""

    def __init__(
        self,
        screen_resolutions: list[dict[str, int]],
        languages: list[str],
        timezones: list[str],
        platforms: list[str],
    ) -> None:
        self._screen_resolutions = [
            ScreenResolution(width=s["width"], height=s["height"])
            for s in screen_resolutions
        ]
        self._languages = [lang for lang in LANGUAGES if lang[0] in languages]
        self._timezones = [tz for tz in timezones if tz in TIMEZONES]
        self._platforms = [p for p in platforms if p in PLATFORM_PROFILES]

    def generate(self) -> Fingerprint:
        """Generate random consistent fingerprint."""
        platform = random.choice(self._platforms)
        return self.generate_for_platform(platform)

    def generate_for_platform(self, platform: str) -> Fingerprint:
        """Generate fingerprint for specific platform."""
        if platform not in PLATFORM_PROFILES:
            raise ValueError(f"Unknown platform: {platform}")

        profile = PLATFORM_PROFILES[platform]

        fingerprint_id = str(uuid.uuid4())
        seed = int(hashlib.sha256(fingerprint_id.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        screen = rng.choice(self._screen_resolutions)

        lang_code, lang_list = rng.choice(self._languages)

        chrome_version = rng.choice(CHROME_VERSIONS)
        user_agent = profile.user_agent_template.format(chrome_version=chrome_version)

        webgl_vendor = rng.choice(profile.webgl_vendors)
        webgl_renderer = rng.choice(profile.webgl_renderers)

        navigator = NavigatorConfig(
            user_agent=user_agent,
            platform=profile.platform,
            language=lang_code,
            languages=lang_list,
            hardware_concurrency=rng.choice(profile.hardware_concurrencies),
            device_memory=rng.choice(profile.device_memories),
            max_touch_points=0,
            vendor=profile.vendor,
        )

        webgl = WebGLConfig(
            vendor="WebKit",
            renderer="WebKit WebGL",
            unmasked_vendor=webgl_vendor,
            unmasked_renderer=webgl_renderer,
        )

        canvas = CanvasConfig(
            noise_r=rng.uniform(-0.01, 0.01),
            noise_g=rng.uniform(-0.01, 0.01),
            noise_b=rng.uniform(-0.01, 0.01),
            noise_a=rng.uniform(-0.001, 0.001),
        )

        audio = AudioConfig(
            sample_rate=rng.choice([44100, 48000]),
            noise_factor=rng.uniform(0.0001, 0.0005),
        )

        num_fonts = rng.randint(6, len(FONTS))
        fonts = tuple(rng.sample(FONTS, num_fonts))

        return Fingerprint(
            id=fingerprint_id,
            screen=screen,
            navigator=navigator,
            timezone=rng.choice(self._timezones),
            webgl=webgl,
            canvas=canvas,
            audio=audio,
            fonts=fonts,
            plugins=PLUGINS,
        )

    def generate_mobile(self) -> Fingerprint:
        """Generate mobile device fingerprint."""
        fingerprint_id = str(uuid.uuid4())
        seed = int(hashlib.sha256(fingerprint_id.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        screen = ScreenResolution(width=393, height=873)

        navigator = NavigatorConfig(
            user_agent="Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
            platform="Linux armv8l",
            language="en-US",
            languages=("en-US", "en"),
            hardware_concurrency=8,
            device_memory=8,
            max_touch_points=5,
            vendor="Google Inc.",
        )

        webgl = WebGLConfig(
            vendor="WebKit",
            renderer="WebKit WebGL",
            unmasked_vendor="Qualcomm",
            unmasked_renderer="Adreno (TM) 730",
        )

        canvas = CanvasConfig(
            noise_r=rng.uniform(-0.01, 0.01),
            noise_g=rng.uniform(-0.01, 0.01),
            noise_b=rng.uniform(-0.01, 0.01),
            noise_a=rng.uniform(-0.001, 0.001),
        )

        audio = AudioConfig(
            sample_rate=48000,
            noise_factor=rng.uniform(0.0001, 0.0005),
        )

        return Fingerprint(
            id=fingerprint_id,
            screen=screen,
            navigator=navigator,
            timezone=rng.choice(self._timezones),
            webgl=webgl,
            canvas=canvas,
            audio=audio,
            fonts=("Roboto", "Droid Sans"),
            plugins=(),
        )

    def validate(self, fingerprint: Fingerprint) -> bool:
        """Validate fingerprint internal consistency."""
        platform = fingerprint.navigator.platform

        if platform not in PLATFORM_PROFILES:
            return False

        profile = PLATFORM_PROFILES[platform]

        if fingerprint.navigator.vendor != profile.vendor:
            return False

        if (
            fingerprint.navigator.hardware_concurrency
            not in profile.hardware_concurrencies
        ):
            return False

        if fingerprint.navigator.device_memory not in profile.device_memories:
            return False

        if fingerprint.timezone not in TIMEZONES:
            return False

        return True
