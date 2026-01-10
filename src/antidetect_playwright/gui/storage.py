"""Storage manager for profiles, folders, settings and proxy pool."""

import json
import logging
from pathlib import Path
from typing import Callable

from .models import (
    BrowserProfile,
    Folder,
    AppSettings,
    ProxyPool,
    ProxyConfig,
    ProxyType,
)

logger = logging.getLogger(__name__)


class Storage:
    """Local storage for all application data."""

    def __init__(self, data_dir: str = "data"):
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._profiles_file = self._data_dir / "profiles.json"
        self._folders_file = self._data_dir / "folders.json"
        self._settings_file = self._data_dir / "settings.json"
        self._proxy_pool_file = self._data_dir / "proxy_pool.json"
        self._tags_pool_file = self._data_dir / "tags_pool.json"
        self._trash_file = self._data_dir / "trash.json"

        self._profiles: list[BrowserProfile] = []
        self._folders: list[Folder] = []
        self._settings: AppSettings = AppSettings()
        self._proxy_pool: ProxyPool = ProxyPool()
        self._tags_pool: list[str] = []
        self._trash: list[dict] = []  # [{id, name, deleted_at, profile_data}]

        self._load_all()

    def _load_all(self) -> None:
        """Load all data from files."""
        self._load_profiles()
        self._load_folders()
        self._load_settings()
        self._load_proxy_pool()
        self._load_tags_pool()
        self._load_trash()

    def _load_profiles(self) -> None:
        """Load profiles from file."""
        if self._profiles_file.exists():
            try:
                data = json.loads(self._profiles_file.read_text())
                self._profiles = [
                    BrowserProfile.from_dict(p) for p in data.get("profiles", [])
                ]
            except Exception as e:
                logger.exception("Error loading profiles: %s", e)
                self._profiles = []

    def _load_folders(self) -> None:
        """Load folders from file."""
        if self._folders_file.exists():
            try:
                data = json.loads(self._folders_file.read_text())
                self._folders = [Folder.from_dict(f) for f in data.get("folders", [])]
            except Exception:
                self._folders = []

    def _load_settings(self) -> None:
        """Load settings from file."""
        if self._settings_file.exists():
            try:
                data = json.loads(self._settings_file.read_text())
                self._settings = AppSettings.from_dict(data)
            except Exception:
                self._settings = AppSettings()

    def _load_proxy_pool(self) -> None:
        """Load proxy pool from file."""
        if self._proxy_pool_file.exists():
            try:
                data = json.loads(self._proxy_pool_file.read_text())
                proxies = []
                for p in data.get("proxies", []):
                    proxy = ProxyConfig(
                        enabled=True,
                        proxy_type=ProxyType(p.get("proxy_type", "http")),
                        host=p.get("host", ""),
                        port=p.get("port", 0),
                        username=p.get("username", ""),
                        password=p.get("password", ""),
                        country_code=p.get("country_code", ""),
                        country_name=p.get("country_name", ""),
                    )
                    proxies.append(proxy)
                self._proxy_pool = ProxyPool(proxies=proxies)
            except Exception:
                self._proxy_pool = ProxyPool()

    def save_profiles(self) -> None:
        """Save profiles to file."""
        data = {"profiles": [p.to_dict() for p in self._profiles]}
        self._profiles_file.write_text(json.dumps(data, indent=2, default=str))

    def save_folders(self) -> None:
        """Save folders to file."""
        data = {"folders": [f.to_dict() for f in self._folders]}
        self._folders_file.write_text(json.dumps(data, indent=2))

    def save_settings(self) -> None:
        """Save settings to file."""
        self._settings_file.write_text(json.dumps(self._settings.to_dict(), indent=2))

    def save_proxy_pool(self) -> None:
        """Save proxy pool to file."""
        data = {
            "proxies": [
                {
                    "proxy_type": p.proxy_type.value,
                    "host": p.host,
                    "port": p.port,
                    "username": p.username,
                    "password": p.password,
                    "country_code": p.country_code,
                    "country_name": p.country_name,
                }
                for p in self._proxy_pool.proxies
            ]
        }
        self._proxy_pool_file.write_text(json.dumps(data, indent=2))

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

    def get_profile(self, profile_id: str) -> BrowserProfile | None:
        """Get profile by ID."""
        for p in self._profiles:
            if p.id == profile_id:
                return p
        return None

    def add_profile(self, profile: BrowserProfile) -> None:
        """Add new profile."""
        self._profiles.append(profile)
        self.save_profiles()

    def update_profile(self, profile: BrowserProfile) -> None:
        """Update existing profile."""
        for i, p in enumerate(self._profiles):
            if p.id == profile.id:
                self._profiles[i] = profile
                break
        self.save_profiles()

    def delete_profile(self, profile_id: str, move_to_trash: bool = True) -> None:
        """Delete profile, optionally moving to trash."""
        from datetime import datetime

        profile = self.get_profile(profile_id)
        if profile:
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

    # Tags Pool
    def _load_tags_pool(self) -> None:
        """Load tags pool from file."""
        if self._tags_pool_file.exists():
            try:
                data = json.loads(self._tags_pool_file.read_text())
                self._tags_pool = data.get("tags", [])
            except Exception:
                self._tags_pool = []

    def save_tags_pool(self) -> None:
        """Save tags pool to file."""
        data = {"tags": self._tags_pool}
        self._tags_pool_file.write_text(json.dumps(data, indent=2))

    def get_tags_pool(self) -> list[str]:
        """Get tags pool."""
        return list(self._tags_pool)

    def add_tag_to_pool(self, tag: str) -> None:
        """Add tag to pool."""
        if tag and tag not in self._tags_pool:
            self._tags_pool.append(tag)
            self.save_tags_pool()

    def remove_tag_from_pool(self, tag: str) -> None:
        """Remove tag from pool."""
        if tag in self._tags_pool:
            self._tags_pool.remove(tag)
            self.save_tags_pool()

    def rename_tag_in_pool(self, old_name: str, new_name: str) -> None:
        """Rename tag in pool."""
        if old_name in self._tags_pool and new_name:
            idx = self._tags_pool.index(old_name)
            self._tags_pool[idx] = new_name
            self.save_tags_pool()

    def get_all_tags(self) -> list[str]:
        """Get all unique tags from profiles and pool."""
        tags = set(self._tags_pool)
        for p in self._profiles:
            tags.update(p.tags)
        return sorted(list(tags))

    # Trash
    def _load_trash(self) -> None:
        """Load trash from file."""
        if self._trash_file.exists():
            try:
                data = json.loads(self._trash_file.read_text())
                self._trash = data.get("items", [])
            except Exception:
                self._trash = []

    def _save_trash(self) -> None:
        """Save trash to file."""
        data = {"items": self._trash}
        self._trash_file.write_text(json.dumps(data, indent=2))

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
