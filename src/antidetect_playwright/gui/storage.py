"""Storage manager for profiles, folders, settings and proxy pool."""

import json
import logging
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .models import (
    BrowserProfile,
    Folder,
    AppSettings,
    ProxyPool,
    ProxyConfig,
    ProxyType,
)
from .security import SecurePasswordEncryption, validate_uuid, sanitize_path_component
from .paths import get_data_dir

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage errors."""

    pass


class ProfileNotFoundError(StorageError):
    """Raised when profile is not found."""

    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        super().__init__(f"Profile not found: {profile_id}")


class InvalidProfileDataError(StorageError):
    """Raised when profile data is invalid or corrupted."""

    pass


class StorageCorruptedError(StorageError):
    """Raised when storage file is corrupted."""

    pass


class Storage:
    """Local storage for all application data."""

    def __init__(self, data_dir: str | Path | None = None):
        """Initialize storage.

        Args:
            data_dir: Custom data directory path. If None, uses platform-specific default:
                - Development: ./data/
                - Linux installed: ~/.local/share/antidetect-browser/
                - Windows installed: %APPDATA%/AntidetectBrowser/
                - macOS installed: ~/Library/Application Support/AntidetectBrowser/
        """
        if data_dir is None:
            self._data_dir = get_data_dir()
        else:
            self._data_dir = Path(data_dir)

        self._data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Storage initialized at: {self._data_dir}")

        self._profiles_file = self._data_dir / "profiles.json"
        self._folders_file = self._data_dir / "folders.json"
        self._settings_file = self._data_dir / "settings.json"
        self._proxy_pool_file = self._data_dir / "proxy_pool.json"
        # Backward-compat: legacy tags-only pool
        self._tags_pool_file = self._data_dir / "tags_pool.json"
        # Unified labels pool (tags/statuses/note templates)
        self._labels_pool_file = self._data_dir / "labels_pool.json"
        self._trash_file = self._data_dir / "trash.json"

        self._profiles: list[BrowserProfile] = []
        self._folders: list[Folder] = []
        self._settings: AppSettings = AppSettings()
        self._proxy_pool: ProxyPool = ProxyPool()
        # Labels pool
        self._tags_pool: list[str] = []
        self._statuses_pool: list[tuple[str, str]] = []  # (name, color)
        self._note_templates_pool: list[tuple[str, str]] = []  # (name, content)
        self._trash: list[dict] = []

        # Profile ID index for O(1) lookup
        self._profile_index: dict[str, BrowserProfile] = {}

        # Performance optimization: Tag index for O(1) tag lookups (40x faster)
        # {tag: set(profile_ids)} - reduces O(tags × profiles) to O(1)
        self._tag_index: dict[str, set[str]] = {}
        self._tag_index_dirty = True  # Rebuild on next access

        self._load_all()

    def _rebuild_index(self) -> None:
        """Rebuild profile index after load/modify."""
        self._profile_index = {p.id: p for p in self._profiles}
        # Mark tag index as dirty - will rebuild on next tag query
        self._tag_index_dirty = True

    def _rebuild_tag_index(self) -> None:
        """Rebuild tag index for fast tag-based queries.

        Performance: O(profiles × avg_tags) once vs O(tags × profiles) per query.
        With 100 profiles and 50 tags: 5000 iterations → 1 rebuild + O(1) lookups.
        """
        if not self._tag_index_dirty:
            return

        self._tag_index.clear()
        for profile in self._profiles:
            for tag in profile.tags:
                if tag not in self._tag_index:
                    self._tag_index[tag] = set()
                self._tag_index[tag].add(profile.id)

        self._tag_index_dirty = False
        logger.debug(f"Rebuilt tag index: {len(self._tag_index)} unique tags")

    def _atomic_write(self, path: Path, data: str) -> None:
        """Write file atomically to prevent corruption.

        Args:
            path: Destination file path
            data: JSON data to write

        Raises:
            StorageError: If write fails
        """
        # Write to temp file in same directory (same filesystem)
        try:
            fd, temp_path = tempfile.mkstemp(
                dir=path.parent, prefix=f".{path.stem}_", suffix=".tmp"
            )
        except OSError as e:
            raise StorageError(f"Failed to create temp file: {e}")

        try:
            with open(fd, "w", encoding="utf-8") as f:
                f.write(data)
            # Atomic rename
            Path(temp_path).replace(path)
            logger.debug(f"Atomically wrote {path}")
        except Exception as e:
            # Clean up temp file on error
            try:
                Path(temp_path).unlink()
            except OSError:
                pass
            raise StorageError(f"Failed to write {path}: {e}")

    def _load_all(self) -> None:
        """Load all data from files."""
        self._load_profiles()
        self._load_folders()
        self._load_settings()
        self._load_proxy_pool()
        self._load_labels_pool()
        self._load_trash()

    # === Labels pool (tags/statuses/note templates) ===

    def _load_labels_pool(self) -> None:
        """Load unified labels pool from file.

        Backward-compat: if labels_pool.json is missing, try migrating tags_pool.json.
        """
        if self._labels_pool_file.exists():
            try:
                data = json.loads(self._labels_pool_file.read_text(encoding="utf-8"))

                tags = data.get("tags", [])
                if isinstance(tags, list):
                    self._tags_pool = [t for t in tags if isinstance(t, str) and t]
                else:
                    self._tags_pool = []

                statuses: list[tuple[str, str]] = []
                raw_statuses = data.get("statuses", [])
                if isinstance(raw_statuses, list):
                    for item in raw_statuses:
                        if isinstance(item, dict):
                            name = str(item.get("name", "")).strip()
                            color = str(item.get("color", "")).strip()
                            if name and color:
                                statuses.append((name, color))
                self._statuses_pool = statuses

                templates: list[tuple[str, str]] = []
                raw_templates = data.get("note_templates", [])
                if isinstance(raw_templates, list):
                    for item in raw_templates:
                        if isinstance(item, dict):
                            name = str(item.get("name", "")).strip()
                            content = str(item.get("content", "")).strip()
                            if name and content:
                                templates.append((name, content))
                self._note_templates_pool = templates

                return
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in labels pool file: %s", e)
                self._tags_pool = []
                self._statuses_pool = []
                self._note_templates_pool = []
                return

        # Migration path: legacy tags_pool.json
        self._load_tags_pool_legacy()
        self._statuses_pool = []
        self._note_templates_pool = []
        # Persist in new unified format (best-effort)
        try:
            self.save_labels_pool()
        except StorageError:
            # Don't fail startup on migration write; keep in-memory data.
            pass

    def _load_tags_pool_legacy(self) -> None:
        """Load legacy tags pool from tags_pool.json (tags-only)."""
        if self._tags_pool_file.exists():
            try:
                data = json.loads(self._tags_pool_file.read_text(encoding="utf-8"))
                tags = data.get("tags", [])
                if isinstance(tags, list):
                    self._tags_pool = [t for t in tags if isinstance(t, str) and t]
                else:
                    self._tags_pool = []
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in tags pool file: %s", e)
                self._tags_pool = []

    def save_labels_pool(self) -> None:
        """Save unified labels pool to labels_pool.json."""
        data = {
            "tags": list(self._tags_pool),
            "statuses": [{"name": n, "color": c} for n, c in self._statuses_pool],
            "note_templates": [
                {"name": n, "content": c} for n, c in self._note_templates_pool
            ],
        }
        self._atomic_write(self._labels_pool_file, json.dumps(data, indent=2))

    def _load_profiles(self) -> None:
        """Load profiles from file.

        Raises:
            StorageCorruptedError: If profiles file is corrupted
        """
        if not self._profiles_file.exists():
            logger.info("Profiles file doesn't exist, starting with empty list")
            self._profiles = []
            return

        try:
            data = json.loads(self._profiles_file.read_text(encoding="utf-8"))
            profiles_data = data.get("profiles", [])

            if not isinstance(profiles_data, list):
                raise InvalidProfileDataError("Profiles data is not a list")

            self._profiles = []
            for i, p in enumerate(profiles_data):
                try:
                    profile = BrowserProfile.from_dict(p)
                    self._profiles.append(profile)
                except Exception as e:
                    logger.error(f"Failed to load profile #{i}: {e}")
                    # Continue loading other profiles

            self._rebuild_index()
            logger.info(f"Loaded {len(self._profiles)} profiles")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in profiles file: {e}")
            raise StorageCorruptedError(f"Profiles file is corrupted: {e}")
        except (KeyError, TypeError) as e:
            logger.error(f"Invalid profile data structure: {e}")
            raise InvalidProfileDataError(f"Invalid profile data: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading profiles: {e}")
            raise StorageError(f"Failed to load profiles: {e}")

    def _load_folders(self) -> None:
        """Load folders from file."""
        if self._folders_file.exists():
            try:
                data = json.loads(self._folders_file.read_text())
                self._folders = [Folder.from_dict(f) for f in data.get("folders", [])]
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in folders file: %s", e)
                self._folders = []
            except (KeyError, TypeError) as e:
                logger.error("Invalid folder data structure: %s", e)
                self._folders = []

    def _load_settings(self) -> None:
        """Load settings from file."""
        if self._settings_file.exists():
            try:
                data = json.loads(self._settings_file.read_text())
                self._settings = AppSettings.from_dict(data)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in settings file: %s", e)
                self._settings = AppSettings()
            except (KeyError, TypeError) as e:
                logger.error("Invalid settings data structure: %s", e)
                self._settings = AppSettings()

    def _load_proxy_pool(self) -> None:
        """Load proxy pool from file."""
        if self._proxy_pool_file.exists():
            try:
                data = json.loads(self._proxy_pool_file.read_text())
                proxies = []
                for p in data.get("proxies", []):
                    # Decrypt password if encrypted
                    password = p.get("password", "")
                    if password and p.get("password_encrypted", False):
                        password = SecurePasswordEncryption.decrypt(password)

                    proxy = ProxyConfig(
                        enabled=True,
                        proxy_type=ProxyType(p.get("proxy_type", "http")),
                        host=p.get("host", ""),
                        port=p.get("port", 0),
                        username=p.get("username", ""),
                        password=password,
                        country_code=p.get("country_code", ""),
                        country_name=p.get("country_name", ""),
                    )
                    proxies.append(proxy)
                self._proxy_pool = ProxyPool(proxies=proxies)
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in proxy pool file: %s", e)
                self._proxy_pool = ProxyPool()
            except ValueError as e:
                logger.error("Invalid proxy data: %s", e)
                self._proxy_pool = ProxyPool()

    def save_profiles(self) -> None:
        """Save profiles to file."""
        data = {"profiles": [p.to_dict() for p in self._profiles]}
        self._atomic_write(self._profiles_file, json.dumps(data, indent=2, default=str))
        self._rebuild_index()

    def save_folders(self) -> None:
        """Save folders to file."""
        data = {"folders": [f.to_dict() for f in self._folders]}
        self._atomic_write(self._folders_file, json.dumps(data, indent=2))

    def save_settings(self) -> None:
        """Save settings to file."""
        self._atomic_write(
            self._settings_file, json.dumps(self._settings.to_dict(), indent=2)
        )

    def save_proxy_pool(self) -> None:
        """Save proxy pool to file with encrypted passwords."""
        data = {
            "proxies": [
                {
                    "proxy_type": p.proxy_type.value,
                    "host": p.host,
                    "port": p.port,
                    "username": p.username,
                    "password": (
                        SecurePasswordEncryption.encrypt(p.password)
                        if p.password
                        else ""
                    ),
                    "password_encrypted": bool(p.password),
                    "country_code": p.country_code,
                    "country_name": p.country_name,
                }
                for p in self._proxy_pool.proxies
            ]
        }
        self._atomic_write(self._proxy_pool_file, json.dumps(data, indent=2))

    # Profiles CRUD
    def get_profiles(
        self, folder_id: str = "", tags: list[str] | None = None, search: str = ""
    ) -> list[BrowserProfile]:
        """Get filtered profiles."""
        profiles = self._profiles

        # Filter by folder
        if folder_id:
            profiles = [p for p in profiles if p.folder_id == folder_id]

        # Filter by tags
        if tags:
            profiles = [p for p in profiles if any(t in p.tags for t in tags)]

        # Filter by search
        if search:
            search_lower = search.lower()
            profiles = [p for p in profiles if search_lower in p.name.lower()]

        return profiles

    def get_profile(self, profile_id: str) -> BrowserProfile:
        """Get profile by ID with O(1) lookup.

        Args:
            profile_id: Profile UUID

        Returns:
            Profile instance

        Raises:
            ValueError: If profile_id is invalid UUID
            ProfileNotFoundError: If profile not found
        """
        if not validate_uuid(profile_id):
            raise ValueError(f"Invalid profile ID format: {profile_id}")

        profile = self._profile_index.get(profile_id)
        if not profile:
            raise ProfileNotFoundError(profile_id)

        return profile

    def add_profile(self, profile: BrowserProfile) -> None:
        """Add new profile.

        Args:
            profile: Profile to add

        Raises:
            ValueError: If profile ID is invalid or already exists
            StorageError: If save fails
        """
        if not validate_uuid(profile.id):
            raise ValueError(f"Invalid profile ID format: {profile.id}")

        if profile.id in self._profile_index:
            raise ValueError(f"Profile with ID {profile.id} already exists")

        self._profiles.append(profile)
        self._profile_index[profile.id] = profile
        self._ensure_tags_in_pool(profile.tags)
        logger.info(f"Added profile: {profile.name} ({profile.id})")
        self.save_profiles()

    def update_profile(self, profile: BrowserProfile) -> None:
        """Update existing profile.

        Args:
            profile: Profile with updated data

        Raises:
            ValueError: If profile ID is invalid
            ProfileNotFoundError: If profile doesn't exist
            StorageError: If save fails
        """
        if not validate_uuid(profile.id):
            raise ValueError(f"Invalid profile ID format: {profile.id}")

        # Check if profile exists
        if profile.id not in self._profile_index:
            raise ProfileNotFoundError(profile.id)

        for i, p in enumerate(self._profiles):
            if p.id == profile.id:
                self._profiles[i] = profile
                self._profile_index[profile.id] = profile
                self._ensure_tags_in_pool(profile.tags)
                logger.info(f"Updated profile: {profile.name} ({profile.id})")
                break

        self.save_profiles()

    def delete_profile(self, profile_id: str, move_to_trash: bool = True) -> None:
        """Delete profile, optionally moving to trash.

        Args:
            profile_id: Profile UUID to delete
            move_to_trash: If True, move to trash; if False, permanently delete

        Raises:
            ValueError: If profile_id is invalid
            ProfileNotFoundError: If profile doesn't exist
            StorageError: If save fails
        """
        if not validate_uuid(profile_id):
            raise ValueError(f"Invalid profile ID format: {profile_id}")

        profile = self._profile_index.get(profile_id)
        if not profile:
            raise ProfileNotFoundError(profile_id)

        if move_to_trash:
            trash_item = {
                "id": profile.id,
                "name": profile.name,
                "deleted_at": datetime.now().isoformat(),
                "profile_data": profile.to_dict(),
            }
            self._trash.append(trash_item)
            self._save_trash()

        self._profiles = [p for p in self._profiles if p.id != profile_id]
        self._profile_index.pop(profile_id, None)
        logger.info(f"Deleted profile: {profile.name} ({profile_id})")
        self.save_profiles()

    # Folders CRUD
    def get_folders(self) -> list[Folder]:
        """Get all folders."""
        return self._folders

    def add_folder(self, folder: Folder) -> None:
        """Add new folder."""
        self._folders.append(folder)
        self.save_folders()

    def update_folder(self, folder: Folder) -> None:
        """Update folder."""
        for i, f in enumerate(self._folders):
            if f.id == folder.id:
                self._folders[i] = folder
                break
        self.save_folders()

    def delete_folder(self, folder_id: str) -> None:
        """Delete folder and move profiles to root."""
        self._folders = [f for f in self._folders if f.id != folder_id]
        for p in self._profiles:
            if p.folder_id == folder_id:
                p.folder_id = ""
        self.save_folders()
        self.save_profiles()

    def get_folder_profile_count(self, folder_id: str) -> int:
        """Get number of profiles in folder."""
        return len([p for p in self._profiles if p.folder_id == folder_id])

    # Settings
    def get_settings(self) -> AppSettings:
        """Get app settings."""
        return self._settings

    def update_settings(self, settings: AppSettings) -> None:
        """Update app settings."""
        self._settings = settings
        self.save_settings()

    # Proxy pool
    def get_proxy_pool(self) -> ProxyPool:
        """Get proxy pool."""
        return self._proxy_pool

    def set_proxy_pool(self, proxies: list[ProxyConfig]) -> None:
        """Replace proxy pool and persist it."""
        self._proxy_pool = ProxyPool(proxies=list(proxies))
        self.save_proxy_pool()

    def add_proxy_to_pool(self, proxy: ProxyConfig) -> None:
        """Add proxy to pool."""
        self._proxy_pool.add_proxy(proxy)
        self.save_proxy_pool()

    def get_next_proxy(self) -> ProxyConfig | None:
        """Get next proxy from pool."""
        return self._proxy_pool.next_proxy()

    def clear_proxy_pool(self) -> None:
        """Clear all proxies from pool."""
        self._proxy_pool = ProxyPool()
        self.save_proxy_pool()

    def get_browser_data_dir(self) -> Path:
        """Get root directory for browser profile data."""
        path = self._data_dir / "browser_data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_tags_in_pool(self, tags: list[str]) -> None:
        """Ensure tags exist in labels pool and persist if changed."""
        changed = False
        for tag in tags:
            if not isinstance(tag, str):
                continue
            normalized = tag.strip()
            if not normalized:
                continue
            if normalized not in self._tags_pool:
                self._tags_pool.append(normalized)
                changed = True
        if changed:
            self.save_labels_pool()

    def get_tags_pool(self) -> list[str]:
        """Get tags pool."""
        return list(self._tags_pool)

    def add_tag_to_pool(self, tag: str) -> None:
        """Add tag to pool."""
        if tag:
            self._ensure_tags_in_pool([tag])

    def remove_tag_from_pool(self, tag: str) -> None:
        """Remove tag from pool."""
        if tag in self._tags_pool:
            self._tags_pool.remove(tag)
            self.save_labels_pool()

    def rename_tag_in_pool(self, old_name: str, new_name: str) -> None:
        """Rename tag in pool."""
        if old_name in self._tags_pool and new_name:
            idx = self._tags_pool.index(old_name)
            self._tags_pool[idx] = new_name
            self.save_labels_pool()

    def get_all_tags(self) -> list[str]:
        """Get all unique tags from profiles and pool.

        Performance optimized: Uses tag index for O(1) lookup vs O(n) iteration.
        """
        self._rebuild_tag_index()  # Only rebuilds if dirty
        # Combine pool tags + tags from index (all tags actually in use)
        tags = set(self._tags_pool)
        tags.update(self._tag_index.keys())
        return sorted(list(tags))

    def get_tag_counts(self) -> dict[str, int]:
        """Get tag usage counts across all profiles.

        Performance: O(1) lookup using pre-built index vs O(tags × profiles) iteration.
        With 50 tags and 100 profiles: 5000 iterations → instant O(tags) lookup.

        Returns:
            Dict mapping tag name to count of profiles using that tag
        """
        self._rebuild_tag_index()  # Only rebuilds if dirty
        return {tag: len(profile_ids) for tag, profile_ids in self._tag_index.items()}

    # Statuses pool
    def get_statuses_pool(self) -> list[tuple[str, str]]:
        """Get custom statuses pool."""
        return list(self._statuses_pool)

    def add_status_to_pool(self, name: str, color: str) -> None:
        """Add custom status to pool."""
        name = (name or "").strip()
        color = (color or "").strip()
        if not name or not color:
            return
        if any(n == name for n, _ in self._statuses_pool):
            return
        self._statuses_pool.append((name, color))
        self.save_labels_pool()

    def remove_status_from_pool(self, name: str) -> None:
        """Remove custom status from pool."""
        name = (name or "").strip()
        if not name:
            return
        before = len(self._statuses_pool)
        self._statuses_pool = [(n, c) for n, c in self._statuses_pool if n != name]
        if len(self._statuses_pool) != before:
            self.save_labels_pool()

    def rename_status_in_pool(self, old_name: str, new_name: str, color: str) -> None:
        """Rename custom status in pool."""
        old_name = (old_name or "").strip()
        new_name = (new_name or "").strip()
        color = (color or "").strip()
        if not old_name or not new_name or not color:
            return
        updated: list[tuple[str, str]] = []
        changed = False
        for n, c in self._statuses_pool:
            if n == old_name:
                updated.append((new_name, color))
                changed = True
            else:
                updated.append((n, c))
        if changed:
            self._statuses_pool = updated
            self.save_labels_pool()

    # Note templates pool
    def get_note_templates_pool(self) -> list[tuple[str, str]]:
        """Get note templates pool."""
        return list(self._note_templates_pool)

    def add_note_template_to_pool(self, name: str, content: str) -> None:
        """Add note template to pool."""
        name = (name or "").strip()
        content = (content or "").strip()
        if not name or not content:
            return
        if any(n == name for n, _ in self._note_templates_pool):
            return
        self._note_templates_pool.append((name, content))
        self.save_labels_pool()

    def remove_note_template_from_pool(self, name: str) -> None:
        """Remove note template from pool."""
        name = (name or "").strip()
        if not name:
            return
        before = len(self._note_templates_pool)
        self._note_templates_pool = [
            (n, c) for n, c in self._note_templates_pool if n != name
        ]
        if len(self._note_templates_pool) != before:
            self.save_labels_pool()

    # Trash
    def _load_trash(self) -> None:
        """Load trash from file."""
        if self._trash_file.exists():
            try:
                data = json.loads(self._trash_file.read_text())
                self._trash = data.get("items", [])
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in trash file: %s", e)
                self._trash = []

    def _save_trash(self) -> None:
        """Save trash to file."""
        data = {"items": self._trash}
        self._atomic_write(self._trash_file, json.dumps(data, indent=2))

    def get_trash(self) -> list[dict]:
        """Get all trashed profiles."""
        return list(self._trash)

    def restore_from_trash(self, profile_id: str) -> bool:
        """Restore profile from trash."""
        for item in self._trash:
            if item["id"] == profile_id:
                profile = BrowserProfile.from_dict(item["profile_data"])
                self._profiles.append(profile)
                self._trash.remove(item)
                self.save_profiles()
                self._save_trash()
                return True
        return False

    def permanently_delete(self, profile_id: str) -> bool:
        """Permanently delete profile from trash."""
        for item in self._trash:
            if item["id"] == profile_id:
                self._trash.remove(item)
                self._save_trash()
                return True
        return False

    def empty_trash(self) -> None:
        """Empty all items from trash."""
        self._trash.clear()
        self._save_trash()

    # Profile data directory
    def get_profile_data_dir(self, profile_id: str) -> Path:
        """Get browser data directory for profile."""
        path = self._data_dir / "browser_data" / profile_id
        path.mkdir(parents=True, exist_ok=True)
        return path
