"""Browser launcher using Camoufox with auto-fingerprint."""

import json
import logging
import shutil
from pathlib import Path
from typing import Callable
import asyncio

from playwright.async_api import Page, BrowserContext
from camoufox.async_api import AsyncCamoufox

from .models import BrowserProfile, ProfileStatus

logger = logging.getLogger(__name__)

# Path to bundled Chrome theme (Material Fox)
CHROME_THEME_DIR = Path(__file__).parent.parent / "resources" / "chrome" / "chrome"


class BrowserLauncher:
    """Manages browser instances using Camoufox with automatic fingerprinting."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
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

            # Camoufox options - everything is auto-configured!
            camoufox_options = {
                "headless": False,
                # GeoIP auto-detects timezone/locale from proxy IP
                "geoip": proxy is not None,
                # Block WebRTC to prevent IP leak
                "block_webrtc": True,
                # Persistent storage for cookies/localStorage
                "persistent_context": True,
                "user_data_dir": str(user_data_dir),
                # Enable Chrome theme (Material Fox userChrome.css)
                "firefox_user_prefs": {
                    # Enable Chrome theme (userChrome.css)
                    "toolkit.legacyUserProfileCustomizations.stylesheets": True,
                    # Chrome-like behaviour for clipped tabs
                    "browser.tabs.tabClipWidth": 83,
                    # Show "Not Secure" on HTTP like Chrome
                    "security.insecure_connection_text.enabled": True,
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
            if profile.os_type in os_map:
                camoufox_options["os"] = [os_map[profile.os_type]]

            # Create and launch Camoufox
            camoufox = AsyncCamoufox(**camoufox_options)
            context = await camoufox.__aenter__()

            self._browsers[profile.id] = camoufox
            self._browser_instances[profile.id] = context

            # Restore browser state if exists (creates tabs)
            await self._restore_browser_state(profile.id, context)

            # Get page after restoration (use last opened tab or create new)
            if context.pages:
                page = context.pages[-1]  # Use last opened tab
            else:
                page = await context.new_page()

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
            # Browser was closed manually - just cleanup (cookies already saved by persistent_context)
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
            # Save state before closing
            if profile_id in self._browser_instances:
                context = self._browser_instances[profile_id]
                await self._save_browser_state(profile_id, context)

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
