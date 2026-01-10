"""Browser launcher using Camoufox with auto-fingerprint."""

import json
import logging
import shutil
from pathlib import Path
from typing import Callable
import asyncio

from playwright.async_api import Page, BrowserContext
from camoufox.async_api import AsyncCamoufox
from camoufox.utils import launch_options as camoufox_launch_options
import orjson

from .models import BrowserProfile, ProfileStatus

logger = logging.getLogger(__name__)

# Path to bundled Chrome theme (Material Fox)
CHROME_THEME_DIR = Path(__file__).parent.parent / "resources" / "chrome" / "chrome"

# Screen/window dimension keys that should NOT be persisted or spoofed
# These values are spoofed by Camoufox via JavaScript API overrides
# If we set them, window/screen dimensions return constants
# regardless of actual window size = broken scaling!
SCREEN_WINDOW_KEYS_TO_EXCLUDE = {
    # Window dimensions
    "window.outerWidth",
    "window.outerHeight",
    "window.innerWidth",
    "window.innerHeight",
    "window.screenX",
    "window.screenY",
    # Screen dimensions - let browser use real screen
    "screen.width",
    "screen.height",
    "screen.availWidth",
    "screen.availHeight",
    "screen.availTop",
    "screen.availLeft",
    "screen.colorDepth",
    "screen.pixelDepth",
    # Document body dimensions
    "document.body.clientWidth",
    "document.body.clientHeight",
}


def _remove_screen_window_keys_from_env(env: dict) -> dict:
    """Remove screen/window keys from CAMOU_CONFIG_* env vars.
    
    Camoufox serializes config into CAMOU_CONFIG_1, CAMOU_CONFIG_2, etc.
    We need to deserialize, remove keys, and re-serialize.
    """
    # Collect all CAMOU_CONFIG chunks
    chunks = []
    i = 1
    while f"CAMOU_CONFIG_{i}" in env:
        chunks.append(env[f"CAMOU_CONFIG_{i}"])
        i += 1
    
    if not chunks:
        return env
    
    # Reconstruct full config JSON
    full_config_str = "".join(chunks)
    try:
        config = orjson.loads(full_config_str)
    except Exception as e:
        logger.warning(f"Failed to parse CAMOU_CONFIG: {e}")
        return env
    
    # Remove screen/window keys
    removed = []
    for key in list(config.keys()):
        if key in SCREEN_WINDOW_KEYS_TO_EXCLUDE:
            del config[key]
            removed.append(key)
    
    if removed:
        logger.debug(f"Removed screen/window keys from config: {removed}")
    
    # Re-serialize
    new_config_str = orjson.dumps(config).decode('utf-8')
    
    # Clear old chunks
    for j in range(1, i):
        del env[f"CAMOU_CONFIG_{j}"]
    
    # Split into new chunks (same chunk size logic as Camoufox)
    import sys
    chunk_size = 2047 if sys.platform == 'win32' else 32767
    for j, start in enumerate(range(0, len(new_config_str), chunk_size)):
        chunk = new_config_str[start:start + chunk_size]
        env[f"CAMOU_CONFIG_{j + 1}"] = chunk
    
    return env


class BrowserLauncher:
    """Manages browser instances using Camoufox with automatic fingerprinting."""

    def __init__(self, data_dir: Path, settings=None):
        self._data_dir = data_dir
        self._settings = settings  # AppSettings for browser config
        self._browsers: dict[str, AsyncCamoufox] = {}
        self._browser_instances: dict[str, BrowserContext] = {}
        self._pages: dict[str, Page] = {}
        self._on_status_change: Callable[[str, ProfileStatus], None] | None = None
        self._on_browser_closed: Callable[[str], None] | None = None

    def set_status_callback(
        self, callback: Callable[[str, ProfileStatus], None]
    ) -> None:
        """Set callback for status changes."""
        self._on_status_change = callback

    def set_browser_closed_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for when browser is manually closed."""
        self._on_browser_closed = callback

    async def launch_profile(self, profile: BrowserProfile) -> bool:
        """Launch browser for profile with auto-configured fingerprint.

        Camoufox + BrowserForge handles:
        - User-Agent generation
        - Platform/OS fingerprint
        - WebGL vendor/renderer
        - Screen resolution
        - Hardware concurrency
        - Device memory
        - And more...

        If proxy is set with geoip=True:
        - Timezone auto-detected from IP
        - Locale auto-detected from IP
        - Language headers auto-configured
        """
        try:
            # Browser data directory for cookies/storage persistence
            user_data_dir = self._data_dir / profile.id
            user_data_dir.mkdir(parents=True, exist_ok=True)

            # Copy Chrome theme (Material Fox) to profile if not exists
            chrome_dir = user_data_dir / "chrome"
            if CHROME_THEME_DIR.exists() and not chrome_dir.exists():
                shutil.copytree(CHROME_THEME_DIR, chrome_dir)

            proxy = profile.proxy.to_camoufox()

            logger.info("Starting profile: %s", profile.name)
            logger.debug("Proxy: %s", proxy)
            logger.debug("Data dir: %s", user_data_dir)

            # Camoufox options - maximum protection
            camoufox_options = {
                "headless": False,
                # GeoIP auto-detects timezone/locale from proxy IP
                "geoip": proxy is not None,
                # Block WebRTC to prevent IP leak
                "block_webrtc": True,
                # Human-like cursor movement (critical for antidetect!)
                "humanize": 1.5,
                # Disable Cross-Origin-Opener-Policy for Turnstile/Cloudflare
                "disable_coop": True,
                # Suppress warnings for intentional settings
                "i_know_what_im_doing": True,
                # Persistent storage for cookies/localStorage
                "persistent_context": True,
                "user_data_dir": str(user_data_dir),
                # CRITICAL: Disable fixed viewport so browser content scales with window!
                # By default Playwright sets 1280x720 fixed viewport
                "no_viewport": True,
                # Enable Chrome theme (Material Fox userChrome.css)
                "firefox_user_prefs": {
                    # Enable Chrome theme (userChrome.css)
                    "toolkit.legacyUserProfileCustomizations.stylesheets": True,
                    # Chrome-like behaviour for clipped tabs
                    "browser.tabs.tabClipWidth": 83,
                    # Show "Not Secure" on HTTP like Chrome
                    "security.insecure_connection_text.enabled": True,
                    # Session restore settings - controlled by save_tabs
                    **(
                        {
                            "browser.startup.page": 3,  # 3 = restore previous session
                            "browser.sessionstore.resume_from_crash": True,
                            "browser.sessionstore.max_resumed_crashes": 3,
                        }
                        if (
                            self._settings
                            and getattr(self._settings, "save_tabs", True)
                        )
                        else {
                            "browser.startup.page": 0,  # 0 = blank page
                            "browser.sessionstore.max_resumed_crashes": 0,
                        }
                    ),
                },
            }

            if proxy:
                camoufox_options["proxy"] = proxy

            # OS hint for fingerprint generation
            os_map = {
                "windows": "windows",
                "macos": "macos",
                "linux": "linux",
            }
            # Short OS codes for WebGL lookup
            os_short_map = {
                "windows": "win",
                "macos": "mac",
                "linux": "lin",
            }
            if profile.os_type in os_map:
                camoufox_options["os"] = [os_map[profile.os_type]]

            # CRITICAL: Save complete fingerprint config to avoid detection!
            # Same profile must have same fingerprint across sessions
            # We save:
            # - fingerprint: navigator, screen, headers from BrowserForge
            # - webgl: GPU vendor/renderer
            # - canvas: anti-aliasing offset for Canvas fingerprint
            # - fonts: spacing seed for font fingerprint
            # - history: window.history.length
            # Without these, each launch would have different fingerprints but same cookies = 100% detection!
            #
            # IMPORTANT: We use `config=` parameter, NOT `fingerprint=`!
            # - fingerprint= expects a Fingerprint dataclass object
            # - config= accepts a dict that gets merged with generated fingerprint
            # - merge_into() only sets keys that don't exist, so our values are preserved
            # NOTE: Screen/window keys are removed later via _remove_screen_window_keys_from_env()

            fingerprint_file = user_data_dir / "fingerprint.json"
            if fingerprint_file.exists():
                # Load saved fingerprint config
                fp_data = json.loads(fingerprint_file.read_text())
                fp_config = fp_data.get("fingerprint", {})

                # Remove screen/window dimension keys so Camoufox uses real sizes
                for key in list(fp_config.keys()):
                    if key in SCREEN_WINDOW_KEYS_TO_EXCLUDE:
                        del fp_config[key]

                # Restore random values that Camoufox normally generates
                # These are set via set_into() which only sets if key not exists
                if "canvas" in fp_data:
                    fp_config["canvas:aaOffset"] = fp_data["canvas"]["aaOffset"]
                if "fonts" in fp_data:
                    fp_config["fonts:spacing_seed"] = fp_data["fonts"]["spacing_seed"]
                if "history_length" in fp_data:
                    fp_config["window.history.length"] = fp_data["history_length"]

                # Pass config dict - Camoufox will generate new fingerprint but
                # merge_into() won't overwrite our existing keys!
                camoufox_options["config"] = fp_config

                # Restore WebGL config to maintain GPU fingerprint
                webgl = fp_data.get("webgl")
                if webgl:
                    camoufox_options["webgl_config"] = (
                        webgl["vendor"],
                        webgl["renderer"],
                    )
                logger.info(f"Loaded fingerprint config from {fingerprint_file}")
            else:
                # Generate new fingerprint and convert to config
                from browserforge.fingerprints import FingerprintGenerator
                from camoufox.fingerprints import from_browserforge
                from camoufox.webgl import sample_webgl
                from random import randint, randrange

                generator = FingerprintGenerator(
                    browser="firefox",
                    os=camoufox_options.get("os", ["windows", "macos", "linux"]),
                )
                fingerprint = generator.generate()
                # Convert to Camoufox config dict
                fp_config = from_browserforge(fingerprint)

                # Generate random values that Camoufox would generate
                # We pre-generate them so we can save and restore later
                canvas_aa_offset = randint(-50, 50)
                fonts_spacing_seed = randint(0, 1_073_741_823)
                history_length = randrange(1, 6)

                # Add to config so Camoufox won't overwrite
                fp_config["canvas:aaOffset"] = canvas_aa_offset
                fp_config["fonts:spacing_seed"] = fonts_spacing_seed
                fp_config["window.history.length"] = history_length

                # Remove screen/window dimension keys so Camoufox uses real sizes
                for key in list(fp_config.keys()):
                    if key in SCREEN_WINDOW_KEYS_TO_EXCLUDE:
                        del fp_config[key]

                # Pass as config dict for first launch too (for consistency)
                camoufox_options["config"] = fp_config

                # Generate WebGL fingerprint
                os_short = os_short_map.get(profile.os_type, "win")
                webgl_fp = sample_webgl(os_short)
                webgl_vendor = webgl_fp["webGl:vendor"]
                webgl_renderer = webgl_fp["webGl:renderer"]
                camoufox_options["webgl_config"] = (webgl_vendor, webgl_renderer)

                # Save complete fingerprint data
                fp_data = {
                    "fingerprint": fp_config,
                    "webgl": {
                        "vendor": webgl_vendor,
                        "renderer": webgl_renderer,
                    },
                    "canvas": {
                        "aaOffset": canvas_aa_offset,
                    },
                    "fonts": {
                        "spacing_seed": fonts_spacing_seed,
                    },
                    "history_length": history_length,
                    "os": profile.os_type,
                }
                fingerprint_file.write_text(json.dumps(fp_data, indent=2, default=str))
                logger.info(
                    f"Generated and saved new fingerprint config to {fingerprint_file}"
                )

            # Create launch options manually to remove screen/window keys
            # This is needed because Camoufox generates these inside launch_options()
            # and we need to remove them AFTER generation but BEFORE launching
            from functools import partial
            
            # Extract persistent_context flag - it's handled separately by AsyncCamoufox
            persistent_context = camoufox_options.pop("persistent_context", False)
            
            # Generate launch options
            from_options = await asyncio.get_event_loop().run_in_executor(
                None,
                partial(camoufox_launch_options, **camoufox_options),
            )
            
            # CRITICAL: Remove screen/window keys from CAMOU_CONFIG env vars
            # This allows the browser to use real window/screen dimensions
            from_options["env"] = _remove_screen_window_keys_from_env(from_options["env"])
            
            # Add no_viewport for Playwright - let content scale with window
            from_options["no_viewport"] = True

            # Create and launch Camoufox with pre-generated options
            camoufox = AsyncCamoufox(
                from_options=from_options,
                persistent_context=persistent_context,
            )
            context = await camoufox.__aenter__()

            self._browsers[profile.id] = camoufox
            self._browser_instances[profile.id] = context

            # Get page (Firefox will restore tabs automatically if enabled)
            if context.pages:
                page = context.pages[-1]
            else:
                page = await context.new_page()

            # Navigate to start page if settings exist and page is blank
            if self._settings and page.url == "about:blank":
                start_page = self._settings.start_page or "about:blank"
                if start_page != "about:blank":
                    # Add https:// if no protocol specified
                    if not start_page.startswith(
                        ("http://", "https://", "about:", "file://")
                    ):
                        start_page = "https://" + start_page
                    try:
                        await page.goto(
                            start_page, wait_until="domcontentloaded", timeout=10000
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load start page {start_page}: {e}")

            self._pages[profile.id] = page

            # Monitor for browser close
            asyncio.create_task(self._monitor_browser(profile.id, context))

            if self._on_status_change:
                self._on_status_change(profile.id, ProfileStatus.RUNNING)

            return True

        except Exception as e:
            logger.exception("Error launching profile: %s", e)
            if self._on_status_change:
                self._on_status_change(profile.id, ProfileStatus.ERROR)
            return False

    async def _monitor_browser(self, profile_id: str, context: BrowserContext) -> None:
        """Monitor browser for manual close."""
        try:
            # Wait for context to close (user closed window)
            await context.wait_for_event("close", timeout=0)
        except Exception:
            pass
        finally:
            # Browser was closed manually - just cleanup
            logger.info(f"Browser closed for profile {profile_id}")
            if profile_id in self._browser_instances:
                await self._cleanup_profile(profile_id)
                if self._on_browser_closed:
                    self._on_browser_closed(profile_id)

    async def _save_browser_state(
        self, profile_id: str, context: BrowserContext
    ) -> None:
        """Save browser state (open tabs URLs) before closing."""
        try:
            # Save state file
            user_data_dir = self._data_dir / profile_id
            state_file = user_data_dir / "browser_state.json"

            # Try to get cookies (may fail if context is closing)
            cookies = []
            try:
                cookies = await context.cookies()
            except Exception as e:
                logger.debug(f"Could not get cookies (context may be closed): {e}")

            # Get all open tab URLs
            tab_urls = []
            for page in context.pages:
                try:
                    url = page.url
                    if url and url != "about:blank":
                        tab_urls.append(url)
                except Exception:
                    pass

            # Save state (cookies optional, tabs are main goal)
            state = {
                "cookies": cookies,
                "tabs": tab_urls,
            }
            state_file.write_text(json.dumps(state, indent=2))
            logger.info(
                f"Saved browser state: {len(cookies)} cookies, {len(tab_urls)} tabs"
            )

        except Exception as e:
            logger.exception(f"Error saving browser state: {e}")

    async def _cleanup_profile(self, profile_id: str) -> None:
        """Clean up profile resources."""
        if profile_id in self._browsers:
            del self._browsers[profile_id]
        if profile_id in self._browser_instances:
            del self._browser_instances[profile_id]
        if profile_id in self._pages:
            del self._pages[profile_id]

    async def _restore_browser_state(
        self, profile_id: str, context: BrowserContext
    ) -> None:
        """Restore browser state (cookies and tabs) from previous session."""
        try:
            user_data_dir = self._data_dir / profile_id
            state_file = user_data_dir / "browser_state.json"

            if not state_file.exists():
                return

            state = json.loads(state_file.read_text())

            # Restore cookies
            cookies = state.get("cookies", [])
            if cookies:
                await context.add_cookies(cookies)
                logger.info(f"Restored {len(cookies)} cookies")

            # Restore tabs
            tab_urls = state.get("tabs", [])
            if tab_urls:
                logger.info(f"Restoring {len(tab_urls)} tabs...")

                # Open saved tabs
                for i, url in enumerate(tab_urls):
                    try:
                        page = await context.new_page()
                        await page.goto(
                            url, wait_until="domcontentloaded", timeout=10000
                        )
                        logger.debug(f"Restored tab {i+1}/{len(tab_urls)}: {url}")
                    except Exception as e:
                        logger.warning(f"Failed to restore tab {url}: {e}")

                logger.info(
                    f"Successfully restored {len([p for p in context.pages if p.url != 'about:blank'])} tabs"
                )

        except Exception as e:
            logger.warning(f"Error restoring browser state: {e}")

    async def stop_profile(self, profile_id: str) -> bool:
        """Stop browser for profile."""
        try:
            # Firefox saves sessions automatically via sessionstore.jsonlz4
            if profile_id in self._browsers:
                camoufox = self._browsers[profile_id]
                try:
                    await camoufox.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning("Error closing browser: %s", e)

            await self._cleanup_profile(profile_id)

            if self._on_status_change:
                self._on_status_change(profile_id, ProfileStatus.STOPPED)

            return True

        except Exception as e:
            logger.exception("Error stopping profile: %s", e)
            return False

    def is_running(self, profile_id: str) -> bool:
        """Check if profile browser is running."""
        return profile_id in self._browser_instances

    async def cleanup(self) -> None:
        """Cleanup all browsers."""
        for profile_id in list(self._browser_instances.keys()):
            await self.stop_profile(profile_id)
