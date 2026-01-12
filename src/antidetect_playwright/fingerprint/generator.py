"""Fingerprint preset generator with maximum randomness."""

import hashlib
import random
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

from .presets import (
    AntidetectPreset,
    AudioPreset,
    CanvasPreset,
    NavigatorPreset,
    ScreenPreset,
    TimezonePreset,
    WebGLPreset,
    WebRTCPreset,
)


# Chrome versions (recent, realistic distribution)
CHROME_VERSIONS = [
    "120.0.0.0",
    "121.0.0.0",
    "122.0.0.0",
    "123.0.0.0",
    "124.0.0.0",
    "125.0.0.0",
    "126.0.0.0",
    "127.0.0.0",
    "128.0.0.0",
    "129.0.0.0",
    "130.0.0.0",
    "131.0.0.0",
    "132.0.0.0",
    "133.0.0.0",
]

FIREFOX_VERSIONS = [
    "128.0",
    "129.0",
    "130.0",
    "131.0",
    "132.0",
    "133.0",
    "134.0",
    "135.0",
]

# Platform configurations
PLATFORMS = {
    "win32": {
        "platform": "Win32",
        "oscpu": "Windows NT 10.0; Win64; x64",
        "vendor": "Google Inc.",
    },
    "win11": {
        "platform": "Win32",
        "oscpu": "Windows NT 10.0; Win64; x64",
        "vendor": "Google Inc.",
    },
    "macos": {
        "platform": "MacIntel",
        "oscpu": "Intel Mac OS X 10_15_7",
        "vendor": "Google Inc.",
    },
    "macos_arm": {
        "platform": "MacIntel",
        "oscpu": "Intel Mac OS X 14_0",
        "vendor": "Google Inc.",
    },
    "linux": {
        "platform": "Linux x86_64",
        "oscpu": "Linux x86_64",
        "vendor": "Google Inc.",
    },
}

# Screen resolutions with real-world distribution weights
SCREEN_RESOLUTIONS = [
    (1920, 1080, 50),  # Full HD - most common
    (2560, 1440, 15),  # QHD
    (1366, 768, 12),  # Common laptop
    (1536, 864, 8),  # Scaled HD
    (1440, 900, 5),  # MacBook
    (1680, 1050, 4),  # Common desktop
    (2560, 1080, 3),  # Ultrawide
    (3840, 2160, 2),  # 4K
    (1280, 720, 1),  # HD
]

# WebGL configurations per platform
WEBGL_CONFIGS = {
    "nvidia_windows": [
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 2080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (NVIDIA)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
    ],
    "amd_windows": [
        (
            "Google Inc. (AMD)",
            "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (AMD)",
            "ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (AMD)",
            "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (AMD)",
            "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (AMD)",
            "ANGLE (AMD, AMD Radeon RX 5700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
    ],
    "intel_windows": [
        (
            "Google Inc. (Intel)",
            "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (Intel)",
            "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (Intel)",
            "ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
        (
            "Google Inc. (Intel)",
            "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        ),
    ],
    "macos_apple": [
        ("Apple Inc.", "Apple M1"),
        ("Apple Inc.", "Apple M1 Pro"),
        ("Apple Inc.", "Apple M1 Max"),
        ("Apple Inc.", "Apple M2"),
        ("Apple Inc.", "Apple M2 Pro"),
        ("Apple Inc.", "Apple M3"),
        ("Apple Inc.", "Apple M3 Pro"),
        (
            "Google Inc. (Apple)",
            "ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)",
        ),
        (
            "Google Inc. (Apple)",
            "ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)",
        ),
    ],
    "macos_intel": [
        ("Intel Inc.", "Intel Iris Pro OpenGL Engine"),
        ("Intel Inc.", "Intel(R) UHD Graphics 630"),
        ("AMD Inc.", "AMD Radeon Pro 5500M OpenGL Engine"),
    ],
    "linux_nvidia": [
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3080/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2"),
        ("NVIDIA Corporation", "NVIDIA GeForce GTX 1660 SUPER/PCIe/SSE2"),
    ],
    "linux_amd": [
        ("X.Org", "AMD Radeon RX 6800 XT (navi21, LLVM 15.0.7, DRM 3.49, 6.1.0)"),
        ("X.Org", "AMD Radeon RX 580 Series (polaris10, LLVM 15.0.7, DRM 3.49, 6.1.0)"),
    ],
    "linux_intel": [
        ("Intel", "Mesa Intel(R) UHD Graphics 630 (CFL GT2)"),
        ("Intel", "Mesa Intel(R) Xe Graphics (TGL GT2)"),
    ],
}

# Timezones with offsets
TIMEZONES = [
    ("America/New_York", -300),
    ("America/Chicago", -360),
    ("America/Denver", -420),
    ("America/Los_Angeles", -480),
    ("America/Sao_Paulo", -180),
    ("Europe/London", 0),
    ("Europe/Paris", 60),
    ("Europe/Berlin", 60),
    ("Europe/Moscow", 180),
    ("Europe/Istanbul", 180),
    ("Asia/Dubai", 240),
    ("Asia/Kolkata", 330),
    ("Asia/Singapore", 480),
    ("Asia/Tokyo", 540),
    ("Asia/Shanghai", 480),
    ("Asia/Seoul", 540),
    ("Australia/Sydney", 600),
    ("Pacific/Auckland", 720),
]

# Languages with locale
LANGUAGES = [
    ("en-US", ["en-US", "en"]),
    ("en-GB", ["en-GB", "en"]),
    ("de-DE", ["de-DE", "de", "en"]),
    ("fr-FR", ["fr-FR", "fr", "en"]),
    ("es-ES", ["es-ES", "es", "en"]),
    ("it-IT", ["it-IT", "it", "en"]),
    ("pt-BR", ["pt-BR", "pt", "en"]),
    ("ru-RU", ["ru-RU", "ru", "en"]),
    ("ja-JP", ["ja-JP", "ja", "en"]),
    ("ko-KR", ["ko-KR", "ko", "en"]),
    ("zh-CN", ["zh-CN", "zh", "en"]),
    ("zh-TW", ["zh-TW", "zh", "en"]),
    ("nl-NL", ["nl-NL", "nl", "en"]),
    ("pl-PL", ["pl-PL", "pl", "en"]),
    ("tr-TR", ["tr-TR", "tr", "en"]),
]

# Common fonts per platform
FONTS_WINDOWS = [
    "Arial",
    "Arial Black",
    "Calibri",
    "Cambria",
    "Cambria Math",
    "Comic Sans MS",
    "Consolas",
    "Courier New",
    "Georgia",
    "Impact",
    "Lucida Console",
    "Microsoft Sans Serif",
    "Palatino Linotype",
    "Segoe UI",
    "Segoe UI Symbol",
    "Tahoma",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
    "Webdings",
    "Wingdings",
]

FONTS_MACOS = [
    "American Typewriter",
    "Andale Mono",
    "Arial",
    "Arial Black",
    "Arial Narrow",
    "Avenir",
    "Avenir Next",
    "Baskerville",
    "Big Caslon",
    "Brush Script MT",
    "Chalkboard",
    "Cochin",
    "Comic Sans MS",
    "Copperplate",
    "Courier New",
    "Georgia",
    "Gill Sans",
    "Helvetica",
    "Helvetica Neue",
    "Hoefler Text",
    "Impact",
    "Lucida Grande",
    "Menlo",
    "Monaco",
    "Optima",
    "Palatino",
    "Papyrus",
    "SF Pro Display",
    "SF Pro Text",
    "Times New Roman",
    "Trebuchet MS",
    "Verdana",
]

FONTS_LINUX = [
    "DejaVu Sans",
    "DejaVu Sans Mono",
    "DejaVu Serif",
    "Droid Sans",
    "Droid Sans Mono",
    "FreeMono",
    "FreeSans",
    "FreeSerif",
    "Liberation Mono",
    "Liberation Sans",
    "Liberation Serif",
    "Noto Sans",
    "Noto Serif",
    "Ubuntu",
    "Ubuntu Mono",
]

# Hardware configurations
HARDWARE_CONCURRENCY = [2, 4, 6, 8, 10, 12, 16, 20, 24, 32]
DEVICE_MEMORY = [2, 4, 8, 16, 32]
DEVICE_PIXEL_RATIOS = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
COLOR_DEPTHS = [24, 30, 32]


class FingerprintPresetGenerator:
    """Generator for antidetect fingerprint presets with maximum randomness."""

    def __init__(
        self,
        seed: str | None = None,
        platform: str | None = None,
        browser: str = "chrome",
    ):
        """
        Initialize generator.

        Args:
            seed: Optional seed for reproducible randomness
            platform: Target platform (win32, win11, macos, macos_arm, linux)
            browser: Browser type (chrome, firefox)
        """
        self._seed = seed
        self._rng = random.Random(seed)
        self._platform = platform
        self._browser = browser

    def _weighted_choice(self, choices: list[tuple[Any, int]]) -> Any:
        """Select item based on weight distribution."""
        total = sum(w for _, w in choices)
        r = self._rng.uniform(0, total)
        cumulative = 0
        for item, weight in choices:
            cumulative += weight
            if r <= cumulative:
                return item
        return choices[-1][0]

    def _random_choice(self, items: list) -> Any:
        """Random choice from list."""
        return self._rng.choice(items)

    def _random_float(self, min_val: float, max_val: float) -> float:
        """Random float in range."""
        return self._rng.uniform(min_val, max_val)

    def _select_platform(self) -> str:
        """Select platform based on real-world distribution."""
        if self._platform:
            return self._platform

        platforms_weighted = [
            ("win32", 65),
            ("win11", 10),
            ("macos", 12),
            ("macos_arm", 8),
            ("linux", 5),
        ]
        return self._weighted_choice([(p, w) for p, w in platforms_weighted])

    def _generate_user_agent(self, platform_id: str, chrome_version: str) -> str:
        """Generate realistic user agent string."""
        platform_info = PLATFORMS[platform_id]

        if self._browser == "firefox":
            firefox_version = self._random_choice(FIREFOX_VERSIONS)
            if platform_id in ("win32", "win11"):
                return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{firefox_version}) Gecko/20100101 Firefox/{firefox_version}"
            elif platform_id in ("macos", "macos_arm"):
                return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:{firefox_version}) Gecko/20100101 Firefox/{firefox_version}"
            else:
                return f"Mozilla/5.0 (X11; Linux x86_64; rv:{firefox_version}) Gecko/20100101 Firefox/{firefox_version}"

        # Chrome
        if platform_id in ("win32", "win11"):
            return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        elif platform_id in ("macos", "macos_arm"):
            return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        else:
            return f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"

    def _generate_app_version(self, platform_id: str, chrome_version: str) -> str:
        """Generate appVersion matching user agent."""
        if platform_id in ("win32", "win11"):
            return f"5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        elif platform_id in ("macos", "macos_arm"):
            return f"5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        else:
            return f"5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"

    def _select_webgl(self, platform_id: str) -> tuple[str, str]:
        """Select WebGL configuration based on platform."""
        if platform_id in ("win32", "win11"):
            gpu_type = self._weighted_choice(
                [
                    ("nvidia_windows", 50),
                    ("amd_windows", 25),
                    ("intel_windows", 25),
                ]
            )
        elif platform_id == "macos_arm":
            gpu_type = "macos_apple"
        elif platform_id == "macos":
            gpu_type = self._weighted_choice(
                [
                    ("macos_apple", 60),
                    ("macos_intel", 40),
                ]
            )
        else:
            gpu_type = self._weighted_choice(
                [
                    ("linux_nvidia", 50),
                    ("linux_amd", 30),
                    ("linux_intel", 20),
                ]
            )

        return self._random_choice(WEBGL_CONFIGS[gpu_type])

    def _select_fonts(self, platform_id: str) -> list[str]:
        """Select fonts for platform with randomness."""
        if platform_id in ("win32", "win11"):
            base_fonts = FONTS_WINDOWS
        elif platform_id in ("macos", "macos_arm"):
            base_fonts = FONTS_MACOS
        else:
            base_fonts = FONTS_LINUX

        # Random subset (70-95% of fonts)
        num_fonts = int(len(base_fonts) * self._random_float(0.7, 0.95))
        return self._rng.sample(base_fonts, num_fonts)

    def _generate_canvas_noise(self) -> CanvasPreset:
        """Generate canvas noise values."""
        # Subtle noise that doesn't break detection but creates unique fingerprint
        noise_scale = self._random_float(0.0001, 0.001)
        return CanvasPreset(
            noise_r=self._random_float(-noise_scale, noise_scale),
            noise_g=self._random_float(-noise_scale, noise_scale),
            noise_b=self._random_float(-noise_scale, noise_scale),
            noise_a=0.0,  # Alpha noise can cause issues
        )

    def _generate_sec_ch_ua(self, chrome_version: str) -> tuple[str, str]:
        """Generate Sec-CH-UA header."""
        major = chrome_version.split(".")[0]
        sec_ch_ua = (
            f'"Chromium";v="{major}", "Not_A Brand";v="8", "Google Chrome";v="{major}"'
        )
        return sec_ch_ua, f'"{PLATFORMS[self._select_platform()]["platform"]}"'

    def generate(self, name: str | None = None) -> AntidetectPreset:
        """
        Generate a complete antidetect preset with maximum randomness.

        Args:
            name: Optional preset name

        Returns:
            Complete AntidetectPreset with all fingerprint data
        """
        preset_id = str(uuid.uuid4())
        preset_name = name or f"Preset-{preset_id[:8]}"

        # Select platform and base configs
        platform_id = self._select_platform()
        platform_config = PLATFORMS[platform_id]
        chrome_version = self._random_choice(CHROME_VERSIONS)

        # Generate user agent
        user_agent = self._generate_user_agent(platform_id, chrome_version)
        app_version = self._generate_app_version(platform_id, chrome_version)

        # Select language
        language, languages = self._random_choice(LANGUAGES)

        # Select hardware
        hardware_concurrency = self._random_choice(HARDWARE_CONCURRENCY)
        device_memory = self._random_choice(DEVICE_MEMORY)

        # Select screen
        screen_data = self._weighted_choice(
            [((w, h), weight) for w, h, weight in SCREEN_RESOLUTIONS]
        )
        screen_width, screen_height = screen_data
        device_pixel_ratio = self._random_choice(DEVICE_PIXEL_RATIOS)

        # Touch points based on platform
        if platform_id in ("win32", "win11"):
            max_touch_points = self._random_choice(
                [0, 0, 0, 1, 5, 10]
            )  # Most Windows no touch
        else:
            max_touch_points = 0

        # Navigator preset
        navigator = NavigatorPreset(
            user_agent=user_agent,
            platform=platform_config["platform"],
            language=language,
            languages=languages,
            hardware_concurrency=hardware_concurrency,
            device_memory=device_memory,
            max_touch_points=max_touch_points,
            vendor=platform_config["vendor"],
            app_version=app_version,
            build_id="20100101",  # Firefox buildID (always static)
            do_not_track=self._random_choice([None, "1", None, None]),  # Usually null
            webdriver=False,
        )

        # Screen preset
        taskbar_height = self._random_choice([40, 48, 60, 72, 80])
        screen = ScreenPreset(
            width=screen_width,
            height=screen_height,
            avail_width=screen_width,
            avail_height=screen_height - taskbar_height,
            color_depth=self._random_choice(COLOR_DEPTHS),
            pixel_depth=24,
            device_pixel_ratio=device_pixel_ratio,
            outer_width=screen_width,
            outer_height=screen_height - taskbar_height - self._rng.randint(50, 150),
        )

        # WebGL preset
        webgl_vendor, webgl_renderer = self._select_webgl(platform_id)
        webgl = WebGLPreset(
            vendor="WebKit",
            renderer="WebKit WebGL",
            unmasked_vendor=webgl_vendor,
            unmasked_renderer=webgl_renderer,
        )

        # Audio preset
        audio = AudioPreset(
            sample_rate=self._random_choice([44100, 48000]),
            channel_count=2,
            noise_factor=self._random_float(0.00001, 0.0001),
        )

        # Canvas preset
        canvas = self._generate_canvas_noise()

        # WebRTC preset
        webrtc = WebRTCPreset(disabled=True)

        # Timezone preset
        tz_id, tz_offset = self._random_choice(TIMEZONES)
        timezone = TimezonePreset(timezone_id=tz_id, offset=tz_offset)

        # Fonts
        fonts = self._select_fonts(platform_id)

        # Plugins
        plugins = ["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer"]

        # Generate headers
        sec_ch_ua, sec_ch_ua_platform = self._generate_sec_ch_ua(chrome_version)
        accept_language = ",".join(
            [f"{l};q={1 - i*0.1:.1f}" for i, l in enumerate(languages[:3])]
        )

        return AntidetectPreset(
            id=preset_id,
            name=preset_name,
            navigator=navigator,
            screen=screen,
            webgl=webgl,
            audio=audio,
            canvas=canvas,
            webrtc=webrtc,
            timezone=timezone,
            fonts=fonts,
            plugins=plugins,
            accept_language=accept_language,
            sec_ch_ua=sec_ch_ua,
            sec_ch_ua_platform=sec_ch_ua_platform,
        )

    def generate_batch(self, count: int) -> list[AntidetectPreset]:
        """Generate multiple unique presets."""
        return [self.generate(f"Preset-{i+1}") for i in range(count)]


def generate_random_preset(
    name: str | None = None,
    platform: str | None = None,
    browser: str = "chrome",
) -> AntidetectPreset:
    """
    Generate a single random antidetect preset.

    This is the main entry point for quick fingerprint generation.

    Args:
        name: Optional preset name
        platform: Target platform (win32, win11, macos, macos_arm, linux)
        browser: Browser type (chrome, firefox)

    Returns:
        Complete AntidetectPreset with randomized fingerprint data

    Example:
        >>> preset = generate_random_preset()
        >>> print(preset.navigator.user_agent)
        Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...

        >>> # Generate for specific platform
        >>> preset = generate_random_preset(platform="macos_arm")

        >>> # Get injection script
        >>> script = preset.to_injection_script()

        >>> # Get Playwright context options
        >>> options = preset.to_playwright_context_options()
    """
    generator = FingerprintPresetGenerator(platform=platform, browser=browser)
    return generator.generate(name)


# Convenience function using external libraries if available
def generate_with_browserforge() -> AntidetectPreset | None:
    """
    Generate fingerprint using BrowserForge library if installed.

    Returns None if browserforge is not installed.

    Install with: pip install browserforge[all]
    """
    try:
        from browserforge.fingerprints import FingerprintGenerator

        gen = FingerprintGenerator(mock_webrtc=True)
        fp = gen.generate()

        # Convert browserforge fingerprint to our preset format
        preset_id = str(uuid.uuid4())

        navigator = NavigatorPreset(
            user_agent=fp.navigator.userAgent,
            platform=fp.navigator.platform,
            language=fp.navigator.language,
            languages=list(fp.navigator.languages),
            hardware_concurrency=fp.navigator.hardwareConcurrency,
            device_memory=fp.navigator.deviceMemory or 8,
            max_touch_points=fp.navigator.maxTouchPoints,
            vendor=fp.navigator.vendor,
            app_version=fp.navigator.appVersion,
            app_name=fp.navigator.appName,
            app_code_name=fp.navigator.appCodeName,
            product=fp.navigator.product,
            product_sub=fp.navigator.productSub,
            build_id="20100101",  # Firefox buildID (always static)
            do_not_track=fp.navigator.doNotTrack,
            webdriver=False,
        )

        screen = ScreenPreset(
            width=fp.screen.width,
            height=fp.screen.height,
            avail_width=fp.screen.availWidth,
            avail_height=fp.screen.availHeight,
            color_depth=fp.screen.colorDepth,
            pixel_depth=fp.screen.pixelDepth,
            device_pixel_ratio=fp.screen.devicePixelRatio,
            inner_width=fp.screen.innerWidth,
            inner_height=fp.screen.innerHeight,
            outer_width=fp.screen.outerWidth,
            outer_height=fp.screen.outerHeight,
        )

        webgl = WebGLPreset(
            vendor="WebKit",
            renderer="WebKit WebGL",
            unmasked_vendor=fp.videoCard.vendor if fp.videoCard else "Google Inc.",
            unmasked_renderer=fp.videoCard.renderer if fp.videoCard else "ANGLE",
        )

        audio = AudioPreset()
        canvas = CanvasPreset(
            noise_r=random.uniform(-0.001, 0.001),
            noise_g=random.uniform(-0.001, 0.001),
            noise_b=random.uniform(-0.001, 0.001),
        )
        webrtc = WebRTCPreset(disabled=fp.mockWebRTC or True)

        # Extract timezone from headers or use default
        timezone = TimezonePreset(timezone_id="America/New_York", offset=-300)

        return AntidetectPreset(
            id=preset_id,
            name=f"BrowserForge-{preset_id[:8]}",
            navigator=navigator,
            screen=screen,
            webgl=webgl,
            audio=audio,
            canvas=canvas,
            webrtc=webrtc,
            timezone=timezone,
            fonts=list(fp.fonts) if fp.fonts else [],
            plugins=["PDF Viewer"],
            accept_language=fp.headers.get("Accept-Language", "en-US,en;q=0.9"),
            sec_ch_ua=fp.headers.get("sec-ch-ua", ""),
            sec_ch_ua_platform=fp.headers.get("sec-ch-ua-platform", ""),
        )

    except ImportError:
        return None


def generate_with_fpgen() -> AntidetectPreset | None:
    """
    Generate fingerprint using Scrapfly's fpgen library if installed.

    Returns None if fpgen is not installed.

    Install with: pip install fingerprint-generator
    Then run: python -m fpgen fetch
    """
    try:
        import fpgen

        fp = fpgen.generate(flatten=True)
        preset_id = str(uuid.uuid4())

        navigator = NavigatorPreset(
            user_agent=fp.get("navigator.userAgent", ""),
            platform=fp.get("navigator.platform", "Win32"),
            language=fp.get("navigator.language", "en-US"),
            languages=fp.get("navigator.languages", ["en-US", "en"]),
            hardware_concurrency=fp.get("navigator.hardwareConcurrency", 8),
            device_memory=fp.get("navigator.deviceMemory", 8),
            max_touch_points=fp.get("navigator.maxTouchPoints", 0),
            vendor=fp.get("navigator.vendor", "Google Inc."),
            app_version=fp.get("navigator.appVersion", ""),
            app_name=fp.get("navigator.appName", "Netscape"),
            app_code_name=fp.get("navigator.appCodeName", "Mozilla"),
            product=fp.get("navigator.product", "Gecko"),
            product_sub=fp.get("navigator.productSub", "20030107"),
            build_id="20100101",  # Firefox buildID (always static)
            do_not_track=fp.get("navigator.doNotTrack"),
            webdriver=False,
        )

        screen = ScreenPreset(
            width=fp.get("screen.width", 1920),
            height=fp.get("screen.height", 1080),
            avail_width=fp.get("screen.availWidth", 1920),
            avail_height=fp.get("screen.availHeight", 1040),
            color_depth=fp.get("screen.colorDepth", 24),
            pixel_depth=fp.get("screen.pixelDepth", 24),
            device_pixel_ratio=fp.get("window.devicePixelRatio", 1.0),
            inner_width=fp.get("window.innerWidth", 0),
            inner_height=fp.get("window.innerHeight", 0),
            outer_width=fp.get("window.outerWidth", 0),
            outer_height=fp.get("window.outerHeight", 0),
        )

        webgl = WebGLPreset(
            vendor="WebKit",
            renderer="WebKit WebGL",
            unmasked_vendor=fp.get("gpu.vendor", "Google Inc."),
            unmasked_renderer=fp.get("gpu.renderer", "ANGLE"),
        )

        audio = AudioPreset()
        canvas = CanvasPreset(
            noise_r=random.uniform(-0.001, 0.001),
            noise_g=random.uniform(-0.001, 0.001),
            noise_b=random.uniform(-0.001, 0.001),
        )
        webrtc = WebRTCPreset(disabled=True)

        tz = fp.get("intl.timezone", "America/New_York")
        timezone = TimezonePreset(timezone_id=tz, offset=-300)

        return AntidetectPreset(
            id=preset_id,
            name=f"FPGen-{preset_id[:8]}",
            navigator=navigator,
            screen=screen,
            webgl=webgl,
            audio=audio,
            canvas=canvas,
            webrtc=webrtc,
            timezone=timezone,
            fonts=fp.get("fonts.list", []),
            plugins=["PDF Viewer"],
            accept_language=fp.get("headers.accept-language", "en-US,en;q=0.9"),
            sec_ch_ua=fp.get("headers.sec-ch-ua", ""),
            sec_ch_ua_platform=fp.get("headers.sec-ch-ua-platform", ""),
        )

    except (ImportError, Exception):
        return None


def generate_best_available(
    name: str | None = None,
    platform: str | None = None,
) -> AntidetectPreset:
    """
    Generate fingerprint using the best available method.

    Tries in order:
    1. fpgen (Scrapfly) - most comprehensive
    2. browserforge - good Bayesian network
    3. Built-in generator - always available

    Args:
        name: Optional preset name
        platform: Target platform

    Returns:
        AntidetectPreset from best available source
    """
    # Try fpgen first (most data coverage)
    preset = generate_with_fpgen()
    if preset:
        if name:
            preset.name = name
        return preset

    # Try browserforge
    preset = generate_with_browserforge()
    if preset:
        if name:
            preset.name = name
        return preset

    # Fall back to built-in
    return generate_random_preset(name=name, platform=platform)
