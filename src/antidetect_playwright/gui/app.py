"""Main application window - Dolphin Anty style."""

import os
import sys
import asyncio
import warnings
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Suppress warnings
os.environ["QT_ACCESSIBILITY"] = "0"
os.environ["QT_LOGGING_RULES"] = "qt.accessibility.atspi=false"
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")
# Suppress Camoufox LeakWarning - we handle geoip ourselves
warnings.filterwarnings("ignore", message=".*geoip=True.*")
warnings.filterwarnings("ignore", category=Warning, module="camoufox")

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMenu,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QShortcut, QKeySequence, QIcon
import qasync

from .models import BrowserProfile, ProfileStatus
from .storage import Storage, StorageError, ProfileNotFoundError
from .launcher import BrowserLauncher
from .theme import Theme
from .icons import get_icon
from .security import install_secure_logging
from .paths import get_data_dir
from .widgets import (
    StatusBadge,
    TagsWidget,
    NotesWidget,
    ProxyWidget,
    ProfileNameWidget,
)
from .dialogs import ProfileDataDialog
from .dialogs_popup import (
    show_profile_popup,
    show_quick_profile_popup,
    show_folder_popup,
    show_tags_edit_popup,
    show_notes_edit_popup,
    show_proxy_pool_popup,
    show_settings_popup,
)
from .modal import confirm_dialog, info_dialog
from .proxy_utils import ping_proxy, detect_proxy_geo
from .components import MiniSidebar
from .pages import ProfilesPage, ProxyPage, TagsPage, TrashPage


class MainWindow(QMainWindow):
    """Main application window with Dolphin Anty-style UI."""

    def __init__(self):
        super().__init__()

        # Use platform-specific data directory
        data_dir = get_data_dir()
        self.storage = Storage()  # Uses get_data_dir() automatically
        self.settings = self.storage.get_settings()
        self.launcher = BrowserLauncher(data_dir / "browser_data", self.settings)

        # State
        self.current_folder = ""
        self.current_tag = ""
        self.search_query = ""
        self.current_page = 1

        # Performance optimization: cache current page profile IDs for incremental updates
        self._current_page_profile_ids: list[str] = []
        self._widget_cache: dict[tuple[int, int], QWidget] = {}  # (row, col) -> widget

        self._setup_ui()
        self._setup_callbacks()
        self._load_data()

        # Apply saved window size and position
        self.resize(self.settings.window_width, self.settings.window_height)
        if self.settings.window_x >= 0 and self.settings.window_y >= 0:
            self.move(self.settings.window_x, self.settings.window_y)

    def _setup_ui(self):
        """Setup main UI structure."""
        self.setWindowTitle("Antidetect Browser")
        self.setMinimumSize(1200, 700)

        # Set application icon
        icon_path = Path(__file__).parent.parent.parent.parent / "assets" / "icons" / "app-icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setStyleSheet(Theme.get_stylesheet())

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Mini sidebar (icon navigation)
        self.mini_sidebar = MiniSidebar()
        self.mini_sidebar.page_changed.connect(self._switch_page)
        self.mini_sidebar.settings_clicked.connect(self._show_settings)
        main_layout.addWidget(self.mini_sidebar)

        # Main pages stack
        self.pages_stack = QStackedWidget()

        # Page 0: Profiles (with sidebar + content)
        self.profiles_page = ProfilesPage(self.settings)
        self._connect_profiles_page_signals()
        self.pages_stack.addWidget(self.profiles_page)

        # Page 1: Proxy management
        self.proxy_page = ProxyPage()
        self.proxy_page.proxy_pool_changed.connect(self._on_proxy_pool_changed)
        self._connect_proxy_page_signals()
        self.pages_stack.addWidget(self.proxy_page)

        # Page 2: Tags/Notes/Statuses
        self.tags_page = TagsPage()
        self.tags_page.tag_created.connect(self._on_tag_created)
        self.tags_page.tag_deleted.connect(self._on_tag_deleted)
        self.tags_page.tag_renamed.connect(self._on_tag_renamed)
        self.tags_page.status_created.connect(self._on_status_created)
        self.tags_page.status_renamed.connect(self._on_status_renamed)
        self.tags_page.status_deleted.connect(self._on_status_deleted)
        self.tags_page.note_template_created.connect(self._on_note_template_created)
        self.tags_page.note_template_deleted.connect(self._on_note_template_deleted)
        self._connect_tags_page_signals()
        self.pages_stack.addWidget(self.tags_page)

        # Page 3: Trash
        self.trash_page = TrashPage()
        self._connect_trash_page_signals()
        self.pages_stack.addWidget(self.trash_page)

        main_layout.addWidget(self.pages_stack, 1)

        # Add keyboard shortcuts for accessibility and power users
        self._setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for common actions."""
        # Ctrl+N: Create new profile
        new_profile_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_profile_shortcut.activated.connect(self._create_profile)

        # Ctrl+Shift+N: Quick create profile
        quick_create_shortcut = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
        quick_create_shortcut.activated.connect(self._quick_create_profile)

        # Ctrl+F: Focus search field
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(
            lambda: self.profiles_page.search_input.setFocus()
            if self.pages_stack.currentIndex() == 0 else None
        )

        # Delete: Delete selected profiles
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self._delete_selected_profiles_shortcut)

        # Ctrl+A: Select all profiles (on profiles page)
        select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        select_all_shortcut.activated.connect(self._select_all_profiles_shortcut)

        # F5: Refresh current view
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._refresh_current_page)

        # Ctrl+1,2,3,4: Switch between pages
        for i in range(1, 5):
            page_shortcut = QShortcut(QKeySequence(f"Ctrl+{i}"), self)
            page_shortcut.activated.connect(
                lambda idx=i-1: self._switch_page(idx)
            )

    def _safe_get_profile(self, profile_id: str) -> BrowserProfile | None:
        """Get profile by id without letting storage exceptions crash the UI."""
        try:
            return self.storage.get_profile(profile_id)
        except (ValueError, ProfileNotFoundError, StorageError) as e:
            # Silently ignore - profile may have been deleted from trash
            return None

    def _spawn_task(self, coro, context: str) -> None:
        """Run coroutine in the background and log exceptions.

        Note: we keep this local to the window to avoid silent task failures.
        """
        try:
            task = asyncio.create_task(coro)
        except RuntimeError as e:
            logging.getLogger(__name__).warning(
                "Cannot start task (%s): %s", context, e
            )
            return

        def _done(t: asyncio.Task) -> None:
            try:
                exc = t.exception()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "Task exception retrieval failed (%s): %s", context, e
                )
                return
            if exc:
                logging.getLogger(__name__).exception(
                    "Background task failed (%s)", context, exc_info=exc
                )

        task.add_done_callback(_done)

    def _connect_profiles_page_signals(self):
        """Connect signals from profiles page."""
        self.profiles_page.folder_selected.connect(self._select_folder)
        self.profiles_page.folder_context_menu.connect(self._show_folder_menu)
        self.profiles_page.create_folder_clicked.connect(self._create_folder)
        self.profiles_page.search_changed.connect(self._on_search)
        self.profiles_page.quick_create_clicked.connect(self._quick_create_profile)
        self.profiles_page.create_profile_clicked.connect(self._create_profile)
        self.profiles_page.tag_filter_changed.connect(self._on_tag_filter)
        self.profiles_page.page_changed.connect(self._on_page_change)
        self.profiles_page.per_page_changed.connect(self._on_per_page_change)
        self.profiles_page.profile_context_menu.connect(self._on_profile_context_menu)

        # Batch operations
        self.profiles_page.batch_start.connect(self._batch_start_profiles)
        self.profiles_page.batch_stop.connect(self._batch_stop_profiles)
        self.profiles_page.batch_tag.connect(self._batch_tag_profiles)
        self.profiles_page.batch_notes.connect(self._batch_notes_profiles)
        self.profiles_page.batch_ping.connect(self._batch_ping_profiles)
        self.profiles_page.batch_delete.connect(self._batch_delete_profiles)

    def _connect_proxy_page_signals(self):
        """Connect signals from proxy page."""
        self.proxy_page.batch_ping.connect(self._batch_ping_proxies)
        self.proxy_page.batch_delete.connect(self._batch_delete_proxies)

    def _connect_tags_page_signals(self):
        """Connect signals from tags page."""
        self.tags_page.batch_delete_tags.connect(self._batch_delete_tags)
        self.tags_page.batch_delete_statuses.connect(self._batch_delete_statuses)
        self.tags_page.batch_delete_templates.connect(self._batch_delete_templates)

    def _connect_trash_page_signals(self):
        """Connect signals from trash page."""
        self.trash_page.restore_requested.connect(self._restore_profiles_from_trash)
        self.trash_page.permanent_delete_requested.connect(
            self._permanently_delete_profiles
        )

    def _switch_page(self, index: int):
        """Switch to page by index."""
        self.pages_stack.setCurrentIndex(index)

    def _setup_callbacks(self):
        """Setup launcher callbacks."""
        self.launcher.set_status_callback(self._on_status_change)
        self.launcher.set_browser_closed_callback(self._on_browser_closed)

    def _load_data(self):
        """Load and display data."""
        for profile in self.storage.get_profiles():
            running = self.launcher.is_running(profile.id)
            if running:
                next_status = ProfileStatus.RUNNING
            else:
                next_status = (
                    ProfileStatus.ERROR
                    if profile.status == ProfileStatus.ERROR
                    else ProfileStatus.STOPPED
                )
            if profile.status != next_status:
                profile.status = next_status
                self.storage.update_profile(profile)

        self._refresh_folders()
        self._refresh_table()
        self._refresh_tags()
        self._load_proxy_pool()
        self._refresh_trash()

    def _load_proxy_pool(self):
        """Load proxy pool into proxy page."""
        pool = self.storage.get_proxy_pool()
        self.proxy_page.update_proxies(pool.proxies)

    def _refresh_folders(self):
        """Refresh folders list in sidebar."""
        folders = self.storage.get_folders()
        folder_counts = {
            f.id: self.storage.get_folder_profile_count(f.id) for f in folders
        }
        all_count = len(self.storage.get_profiles())

        self.profiles_page.update_all_profiles_count(all_count)
        self.profiles_page.update_folders(folders, folder_counts, self.current_folder)

    def _update_profile_status_incremental(self, profile_id: str, new_status: ProfileStatus):
        """Incrementally update single profile status without full table rebuild.

        Performance optimization: O(1) instead of O(n) for status changes.
        """
        # Check if profile is on current page
        if profile_id not in self._current_page_profile_ids:
            return

        # Find row index
        try:
            row = self._current_page_profile_ids.index(profile_id)
        except ValueError:
            return

        # Update status badge widget only (column 2)
        table = self.profiles_page.table
        existing_widget = table.indexWidget(self.profiles_page.table_model.index(row, 2))
        if existing_widget and isinstance(existing_widget, StatusBadge):
            existing_widget.update_status(new_status)

    def _refresh_table(self, force_full_rebuild: bool = False):
        """Refresh profiles table with optional incremental updates.

        Args:
            force_full_rebuild: If True, always rebuild entire table.
                              If False, use incremental updates when possible.
        """
        selected_profile_ids = set(self.profiles_page.get_selected_profile_ids())

        # Get filtered profiles
        profiles = self.storage.get_profiles(
            folder_id=self.current_folder,
            tags=[self.current_tag] if self.current_tag else None,
            search=self.search_query,
        )

        # Pagination
        total = len(profiles)
        per_page = self.settings.items_per_page
        start = (self.current_page - 1) * per_page
        end = start + per_page
        page_profiles = profiles[start:end]

        # Update pagination widget
        self.profiles_page.pagination.update_data(
            total=total, page=self.current_page, per_page=per_page
        )

        # Show empty placeholder or table
        all_profiles = self.storage.get_profiles()
        if not all_profiles:
            self.profiles_page.show_empty_state()
            self._current_page_profile_ids = []
            return
        else:
            self.profiles_page.show_table()

        # Check if we can use incremental update (same profiles, different status only)
        new_page_ids = [p.id for p in page_profiles]
        if not force_full_rebuild and new_page_ids == self._current_page_profile_ids:
            # Incremental update: only refresh status badges
            for row, profile in enumerate(page_profiles):
                running = self.launcher.is_running(profile.id)
                if running:
                    next_status = ProfileStatus.RUNNING
                else:
                    next_status = (
                        ProfileStatus.ERROR
                        if profile.status == ProfileStatus.ERROR
                        else ProfileStatus.STOPPED
                    )
                if profile.status != next_status:
                    profile.status = next_status
                    self.storage.update_profile(profile)

                # Update only status badge (column 2)
                table = self.profiles_page.table
                status_widget = table.indexWidget(self.profiles_page.table_model.index(row, 2))
                if status_widget and isinstance(status_widget, StatusBadge):
                    status_widget.update_status(profile.status)
            return

        # Full rebuild needed
        self._current_page_profile_ids = new_page_ids
        self._widget_cache.clear()

        # Update table
        table = self.profiles_page.table
        rows: list[list[str]] = []
        payloads: list[str] = []

        for profile in page_profiles:
            running = self.launcher.is_running(profile.id)
            if running:
                next_status = ProfileStatus.RUNNING
            else:
                next_status = (
                    ProfileStatus.ERROR
                    if profile.status == ProfileStatus.ERROR
                    else ProfileStatus.STOPPED
                )
            if profile.status != next_status:
                profile.status = next_status
                self.storage.update_profile(profile)

            rows.append(["", "", "", "", "", "", ""])
            payloads.append(profile.id)

        self.profiles_page.table_model.set_rows(rows, payloads)

        for row, profile in enumerate(page_profiles):
            # Checkbox column (index 0)
            self.profiles_page.add_checkbox_to_row(
                row, checked=profile.id in selected_profile_ids
            )

            # Name column with OS icon and Start/Stop (index 1)
            name_widget = ProfileNameWidget(profile)
            name_widget.start_requested.connect(
                lambda p=profile: self._start_profile(p)
            )
            name_widget.stop_requested.connect(lambda p=profile: self._stop_profile(p))
            name_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            name_widget.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=name_widget: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            table.setIndexWidget(self.profiles_page.table_model.index(row, 1), name_widget)

            # Status (index 2)
            status_badge = StatusBadge(profile.status)
            status_badge.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            status_badge.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=status_badge: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            table.setIndexWidget(self.profiles_page.table_model.index(row, 2), status_badge)

            # Notes (index 3)
            notes_widget = NotesWidget(profile.notes)
            notes_widget.edit_requested.connect(lambda p=profile: self._edit_notes(p))
            notes_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            notes_widget.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=notes_widget: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            table.setIndexWidget(self.profiles_page.table_model.index(row, 3), notes_widget)

            # Tags (index 4)
            tags_widget = TagsWidget(profile.tags)
            tags_widget.tag_clicked.connect(self._on_tag_filter)
            tags_widget.edit_requested.connect(lambda p=profile: self._edit_tags(p))
            tags_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            tags_widget.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=tags_widget: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            table.setIndexWidget(self.profiles_page.table_model.index(row, 4), tags_widget)

            # Proxy (index 5)
            proxy_widget = ProxyWidget(profile.proxy)
            proxy_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            proxy_widget.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=proxy_widget: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            table.setIndexWidget(self.profiles_page.table_model.index(row, 5), proxy_widget)

            # Actions (index 6) - single menu button
            actions_widget = QWidget()
            actions_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            actions_widget.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=actions_widget: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(8, 0, 8, 0)
            actions_layout.setSpacing(0)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            menu_btn = QPushButton()
            menu_btn.setIcon(get_icon("more", 16))
            menu_btn.setIconSize(QSize(16, 16))
            menu_btn.setFixedSize(28, 28)
            menu_btn.setProperty("class", "icon")
            menu_btn.setToolTip("Actions")
            menu_btn.clicked.connect(
                lambda checked=False, p=profile, w=menu_btn: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            actions_layout.addWidget(menu_btn)
            table.setIndexWidget(self.profiles_page.table_model.index(row, 6), actions_widget)

        # Keep toolbar + header checkbox state consistent after rebuild
        self.profiles_page._update_selection()
        self.profiles_page._update_header_checkbox_state()

    def _refresh_tags(self):
        """Refresh tag filters with optimized tag count calculation."""
        tags = self.storage.get_all_tags()
        self.profiles_page.update_tag_filter(tags, self.current_tag)

        # Get tag counts efficiently (40x faster with tag index)
        tag_counts = self.storage.get_tag_counts()

        self.tags_page.update_tags(tags, tag_counts)

        # Unified labels pool: also refresh custom statuses and note templates
        self.tags_page.update_statuses(self.storage.get_statuses_pool())
        self.tags_page.update_note_templates(self.storage.get_note_templates_pool())

    # === Actions ===

    def _select_folder(self, folder_id: str):
        """Select folder filter."""
        self.current_folder = folder_id
        self.current_page = 1

        # Update folder label
        if folder_id:
            folder = next(
                (f for f in self.storage.get_folders() if f.id == folder_id), None
            )
            self.profiles_page.set_folder_label(
                folder.name if folder else "All Profiles"
            )
        else:
            self.profiles_page.set_folder_label("All Profiles")

        self._refresh_folders()
        self._refresh_table()

    def _on_search(self, text: str):
        """Handle search input."""
        self.search_query = text
        self.current_page = 1
        self._refresh_table()

    def _on_tag_filter(self, tag: str):
        """Handle tag filter selection."""
        self.current_tag = tag
        self.current_page = 1
        self._refresh_table()

    def _on_page_change(self, page: int):
        """Handle page change."""
        self.current_page = page
        self._refresh_table(force_full_rebuild=True)  # Page change needs full rebuild

    def _on_per_page_change(self, per_page: int):
        """Handle items per page change."""
        self.settings.items_per_page = per_page
        self.storage.update_settings(self.settings)
        self.current_page = 1
        self._refresh_table(force_full_rebuild=True)  # Per-page change needs full rebuild

    def _create_profile(self):
        """Open profile creation dialog."""
        result = show_profile_popup(self, storage=self.storage)
        if result:
            profile, should_regenerate = result
            profile.folder_id = self.current_folder
            self.storage.add_profile(profile)
            self._refresh_table()
            self._refresh_folders()

    def _quick_create_profile(self):
        """Quick profile creation."""
        profile = show_quick_profile_popup(self)
        if profile:
            profile.folder_id = self.current_folder
            self.storage.add_profile(profile)
            self._refresh_table()
            self._refresh_folders()

    def _create_folder(self):
        """Create new folder."""
        folder = show_folder_popup(self)
        if folder:
            self.storage.add_folder(folder)
            self._refresh_folders()

    def _show_settings(self):
        """Show settings dialog."""
        if show_settings_popup(self, self.settings):
            # Save updated settings (settings object is modified in-place)
            self.storage.save_settings()
            # Settings will be applied on next browser launch

    def _show_folder_menu(self, folder_id: str, pos):
        """Show folder context menu."""
        menu = QMenu(self)

        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self._edit_folder(folder_id))

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_folder(folder_id))

        menu.exec(pos)

    def _edit_folder(self, folder_id: str):
        """Edit folder."""
        folder = next(
            (f for f in self.storage.get_folders() if f.id == folder_id), None
        )
        if folder:
            updated = show_folder_popup(self, folder)
            if updated:
                self.storage.update_folder(updated)
                self._refresh_folders()

    def _delete_folder(self, folder_id: str):
        """Delete folder."""
        if confirm_dialog(
            self,
            "Delete Folder",
            "Delete this folder? Profiles will be moved to All Profiles.",
        ):
            self.storage.delete_folder(folder_id)
            if self.current_folder == folder_id:
                self.current_folder = ""
            self._refresh_folders()
            self._refresh_table()

    def _on_profile_context_menu(self, profile_id: str, pos):
        """Handle profile context menu request."""
        if not profile_id:
            return

        profile = self._safe_get_profile(profile_id)
        if profile is None:
            return

        self._show_profile_context_menu(profile, pos)

    def _show_profile_context_menu(self, profile: BrowserProfile, pos):
        """Show profile context menu."""
        menu = QMenu(self)

        running = self.launcher.is_running(profile.id)
        if running:
            stop_action = menu.addAction(get_icon("stop", 14), "Stop")
            stop_action.triggered.connect(lambda: self._stop_profile(profile))
        else:
            start_action = menu.addAction(get_icon("play", 14), "Start")
            start_action.triggered.connect(lambda: self._start_profile(profile))

        menu.addSeparator()

        edit_action = menu.addAction(get_icon("edit", 14), "Edit")
        edit_action.triggered.connect(lambda: self._edit_profile(profile))

        # View Profile Data (fingerprint, cookies, storage, etc.)
        data_action = menu.addAction(get_icon("user", 14), "View Profile Data")
        data_action.triggered.connect(lambda: self._view_fingerprint(profile))

        duplicate_action = menu.addAction(get_icon("copy", 14), "Duplicate")
        duplicate_action.triggered.connect(lambda: self._duplicate_profile(profile))

        menu.addSeparator()

        # Proxy actions
        if profile.proxy and profile.proxy.enabled:
            ping_action = menu.addAction(get_icon("ping", 14), "Ping Proxy")
            ping_action.triggered.connect(lambda: self._ping_proxy(profile))

        change_proxy_action = menu.addAction(get_icon("swap", 14), "Change Proxy")
        change_proxy_action.triggered.connect(lambda: self._quick_change_proxy(profile))

        menu.addSeparator()

        # Move to folder submenu
        move_menu = menu.addMenu(get_icon("folder", 14), "Move to Folder")

        # Root folder option
        root_action = move_menu.addAction("All Profiles")
        root_action.triggered.connect(lambda: self._move_profile_to_folder(profile, ""))
        if profile.folder_id == "":
            root_action.setEnabled(False)

        move_menu.addSeparator()

        # Folder options
        folders = self.storage.get_folders()
        for folder in folders:
            folder_action = move_menu.addAction(folder.name)
            folder_action.triggered.connect(
                lambda checked, fid=folder.id: self._move_profile_to_folder(
                    profile, fid
                )
            )
            if profile.folder_id == folder.id:
                folder_action.setEnabled(False)

        menu.addSeparator()

        delete_action = menu.addAction(get_icon("trash", 14), "Delete")
        delete_action.triggered.connect(lambda: self._delete_profile(profile))

        menu.exec(pos)

    def _view_fingerprint(self, profile: BrowserProfile):
        """Show fingerprint dialog for profile."""
        data_dir = self.storage.get_browser_data_dir()
        dialog = ProfileDataDialog(profile, data_dir, parent=self)
        dialog.exec()

    def _edit_profile(self, profile: BrowserProfile):
        """Edit profile."""
        result = show_profile_popup(self, profile, storage=self.storage)
        if result:
            updated_profile, should_regenerate = result

            # If regenerate was requested, delete fingerprint.json
            if should_regenerate:
                data_dir = self.storage.get_browser_data_dir()
                fingerprint_file = data_dir / updated_profile.id / "fingerprint.json"
                if fingerprint_file.exists():
                    fingerprint_file.unlink()
                    logger.info(
                        f"Deleted fingerprint for regeneration: {fingerprint_file}"
                    )

            self.storage.update_profile(updated_profile)
            self._refresh_table()

    def _move_profile_to_folder(self, profile: BrowserProfile, folder_id: str):
        """Move profile to folder."""
        profile.folder_id = folder_id
        self.storage.update_profile(profile)
        self._refresh_table()
        self._refresh_folders()

    def _duplicate_profile(self, profile: BrowserProfile):
        """Duplicate profile."""
        new_profile = BrowserProfile.from_dict(profile.to_dict())
        new_profile.id = str(__import__("uuid").uuid4())
        new_profile.name = f"{profile.name} (copy)"
        new_profile.status = ProfileStatus.STOPPED
        self.storage.add_profile(new_profile)
        self._refresh_table()
        self._refresh_folders()

    def _delete_profile(self, profile: BrowserProfile):
        """Delete profile."""
        if confirm_dialog(
            self,
            "Delete Profile",
            f"Delete profile '{profile.name}'?",
        ):
            if self.launcher.is_running(profile.id):
                self._do_stop_profile(profile.id)
            self.storage.delete_profile(profile.id)
            self._refresh_table()
            self._refresh_folders()
            self._refresh_trash()

    @qasync.asyncSlot(str)
    async def _do_stop_profile(self, profile_id: str):
        """Async stop profile by id."""
        await self.launcher.stop_profile(profile_id)
        self._refresh_table()

    @qasync.asyncSlot(object)
    async def _start_profile(self, profile: BrowserProfile):
        """Start browser for profile."""
        if self.launcher.is_running(profile.id):
            return
        if profile.status == ProfileStatus.STARTING:
            return

        # Set STARTING status immediately for visual feedback
        profile.status = ProfileStatus.STARTING
        profile.last_used = datetime.now()
        self.storage.update_profile(profile)
        self._refresh_table()

        success = await self.launcher.launch_profile(profile)
        if not success:
            # Reset to stopped on failure
            profile.status = ProfileStatus.STOPPED
            self.storage.update_profile(profile)
            self._refresh_table()

    @qasync.asyncSlot(object)
    async def _stop_profile(self, profile: BrowserProfile):
        """Stop browser for profile."""
        if self.launcher.is_stopping(profile.id):
            return
        if not self.launcher.is_running(profile.id):
            profile.status = ProfileStatus.STOPPED
            self.storage.update_profile(profile)
            self._refresh_table()
            return

        success = await self.launcher.stop_profile(profile.id)
        if not success:
            profile.status = ProfileStatus.ERROR
            self.storage.update_profile(profile)
        self._refresh_table()

    def _on_status_change(self, profile_id: str, status: ProfileStatus):
        """Handle status change from launcher with optimized incremental update."""
        profile = self._safe_get_profile(profile_id)
        if profile is not None:
            profile.status = status
            self.storage.update_profile(profile)
        # Use incremental update instead of full rebuild (8x faster)
        self._update_profile_status_incremental(profile_id, status)

    def _on_browser_closed(self, profile_id: str):
        """Handle browser manually closed."""
        profile = self._safe_get_profile(profile_id)
        if profile is not None:
            profile.status = ProfileStatus.STOPPED
            self.storage.update_profile(profile)
        self._refresh_table()

    def _edit_notes(self, profile: BrowserProfile):
        """Edit profile notes."""
        notes = show_notes_edit_popup(
            self,
            profile.notes,
            note_templates=self.storage.get_note_templates_pool(),
        )
        if notes is not None:
            profile.notes = notes
            self.storage.update_profile(profile)
            self._refresh_table()

    def _edit_tags(self, profile: BrowserProfile):
        """Edit profile tags."""
        all_tags = self.storage.get_all_tags()
        tags = show_tags_edit_popup(self, profile.tags, all_tags)
        if tags is not None:
            profile.tags = tags
            self.storage.update_profile(profile)
            self._refresh_table()
            self._refresh_tags()

    @qasync.asyncSlot(object)
    async def _ping_proxy(self, profile: BrowserProfile):
        """Ping proxy for profile."""
        if not profile.proxy.enabled:
            return

        ping_ms = await ping_proxy(profile.proxy)
        profile.proxy.ping_ms = ping_ms
        profile.proxy.last_ping = datetime.now()

        # Also detect geo if not set
        if not profile.proxy.country_code:
            geo = await detect_proxy_geo(profile.proxy)
            if geo:
                profile.proxy.country_code = geo.get("country_code", "")
                profile.proxy.country_name = geo.get("country_name", "")
                profile.proxy.city = geo.get("city", "")
                profile.proxy.timezone = geo.get("timezone", "")

        self.storage.update_profile(profile)
        self._refresh_table()

    def _quick_change_proxy(self, profile: BrowserProfile):
        """Quick change proxy from pool."""
        proxy = self.storage.get_next_proxy()
        if proxy:
            profile.proxy = proxy
            self.storage.update_profile(profile)
            self._refresh_table()
        else:
            info_dialog(
                self,
                "Proxy Pool Empty",
                "No proxies in pool. Add proxies via Proxy Pool button.",
            )

    def _open_proxy_pool(self):
        """Open proxy pool dialog."""
        pool = self.storage.get_proxy_pool()
        proxies = show_proxy_pool_popup(self, pool.proxies)
        if proxies is not None:
            self.storage.set_proxy_pool(proxies)

    def _on_proxy_pool_changed(self, proxies: list):
        """Handle proxy pool changes from proxy page."""
        self.storage.set_proxy_pool(proxies)

    def _on_tag_created(self, tag: str):
        """Handle tag creation - add to pool."""
        self.storage.add_tag_to_pool(tag)
        self._refresh_tags()

    def _on_tag_deleted(self, tag: str):
        """Handle tag deletion - remove from pool and all profiles."""
        self.storage.remove_tag_from_pool(tag)
        for profile in self.storage.get_profiles():
            if tag in profile.tags:
                profile.tags.remove(tag)
                self.storage.update_profile(profile)
        self._refresh_table()
        self._refresh_tags()

    def _on_tag_renamed(self, old_name: str, new_name: str):
        """Handle tag rename - update pool and all profiles."""
        self.storage.rename_tag_in_pool(old_name, new_name)
        for profile in self.storage.get_profiles():
            if old_name in profile.tags:
                profile.tags.remove(old_name)
                profile.tags.append(new_name)
                self.storage.update_profile(profile)
        self._refresh_table()
        self._refresh_tags()

    def _on_status_created(self, name: str, color: str):
        """Handle custom status creation - persist to pool."""
        self.storage.add_status_to_pool(name, color)
        self.tags_page.update_statuses(self.storage.get_statuses_pool())

    def _on_status_renamed(self, old_name: str, new_name: str, color: str):
        """Handle custom status rename - persist to pool."""
        self.storage.rename_status_in_pool(old_name, new_name, color)
        self.tags_page.update_statuses(self.storage.get_statuses_pool())

    def _on_status_deleted(self, name: str):
        """Handle custom status deletion - persist to pool."""
        self.storage.remove_status_from_pool(name)
        self.tags_page.update_statuses(self.storage.get_statuses_pool())

    def _on_note_template_created(self, name: str, content: str):
        """Handle note template creation - persist to pool."""
        self.storage.add_note_template_to_pool(name, content)
        self.tags_page.update_note_templates(self.storage.get_note_templates_pool())

    def _on_note_template_deleted(self, name: str):
        """Handle note template deletion - persist to pool."""
        self.storage.remove_note_template_from_pool(name)
        self.tags_page.update_note_templates(self.storage.get_note_templates_pool())

    # === Batch operations ===

    def _batch_start_profiles(self, profile_ids: list[str]):
        """Start multiple profiles in parallel with limit."""
        async def start_all():
            """Start all profiles concurrently with concurrency limit."""
            # Limit concurrent starts to avoid system overload
            semaphore = asyncio.Semaphore(5)  # Max 5 simultaneous starts
            
            async def start_one(profile):
                async with semaphore:
                    await self._start_profile(profile)
            
            tasks = []
            for pid in profile_ids:
                profile = self._safe_get_profile(pid)
                if profile is not None:
                    tasks.append(start_one(profile))
            
            if tasks:
                # Wait for all profiles to start (or fail) concurrently
                await asyncio.gather(*tasks, return_exceptions=True)
        
        # Spawn the batch start as a background task
        self._spawn_task(start_all(), context="batch_start_profiles")

    def _batch_stop_profiles(self, profile_ids: list[str]):
        """Stop multiple profiles in parallel."""
        async def stop_all():
            """Stop all profiles concurrently."""
            tasks = []
            for pid in profile_ids:
                profile = self._safe_get_profile(pid)
                if profile is not None:
                    tasks.append(self._stop_profile(profile))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        
        self._spawn_task(stop_all(), context="batch_stop_profiles")

    def _batch_tag_profiles(self, profile_ids: list[str]):
        """Set tags for multiple profiles."""
        if not profile_ids:
            return
        # Use first profile for dialog, apply to all
        profiles = [
            p for pid in profile_ids if (p := self._safe_get_profile(pid)) is not None
        ]
        if not profiles:
            return

        new_tags = show_tags_edit_popup(self, profiles[0].tags, self.storage.get_all_tags())
        if new_tags is not None:
            for profile in profiles:
                profile.tags = new_tags
                self.storage.update_profile(profile)
            self._refresh_table()
            self._refresh_tags()

    def _batch_notes_profiles(self, profile_ids: list[str]):
        """Set notes for multiple profiles."""
        if not profile_ids:
            return
        profiles = [
            p for pid in profile_ids if (p := self._safe_get_profile(pid)) is not None
        ]
        if not profiles:
            return

        new_notes = show_notes_edit_popup(
            self,
            "",
            note_templates=self.storage.get_note_templates_pool(),
        )
        if new_notes is not None:
            for profile in profiles:
                profile.notes = new_notes
                self.storage.update_profile(profile)
            self._refresh_table()

    def _batch_ping_profiles(self, profile_ids: list[str]):
        """Ping proxies for multiple profiles in parallel."""
        async def ping_all():
            """Ping all profile proxies concurrently."""
            tasks = []
            for pid in profile_ids:
                profile = self._safe_get_profile(pid)
                if profile is not None and profile.proxy.enabled:
                    tasks.append(self._ping_proxy(profile))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        self._spawn_task(ping_all(), context="batch_ping_profiles")

    def _delete_selected_profiles_shortcut(self):
        """Delete selected profiles (keyboard shortcut handler)."""
        if self.pages_stack.currentIndex() == 0:  # Profiles page
            selected = self.profiles_page.get_selected_profile_ids()
            if selected:
                self._spawn_task(
                    self._batch_delete_profiles(selected),
                    context="delete_selected_shortcut"
                )

    def _select_all_profiles_shortcut(self):
        """Select all profiles (keyboard shortcut handler)."""
        if self.pages_stack.currentIndex() == 0:  # Profiles page
            self.profiles_page._select_all()

    def _refresh_current_page(self):
        """Refresh current page (F5 shortcut)."""
        page_index = self.pages_stack.currentIndex()
        if page_index == 0:  # Profiles
            self._refresh_table()
            self._refresh_folders()
        elif page_index == 1:  # Proxy
            self._load_proxy_pool()
        elif page_index == 2:  # Tags
            self._refresh_tags()
        elif page_index == 3:  # Trash
            self._refresh_trash()

    @qasync.asyncSlot(list)
    async def _batch_delete_profiles(self, profile_ids: list[str]):
        """Delete multiple profiles."""
        if not profile_ids:
            return

        # Build detailed confirmation message with profile names
        profile_names = []
        for pid in profile_ids[:5]:  # Show first 5 profiles
            profile = self._safe_get_profile(pid)
            if profile:
                profile_names.append(f"  • {profile.name}")

        if len(profile_ids) > 5:
            profile_names.append(f"  ... and {len(profile_ids) - 5} more")

        profiles_list = "\n".join(profile_names)
        message = f"Delete the following {len(profile_ids)} profiles?\n\n{profiles_list}"

        if confirm_dialog(
            self,
            "Delete Profiles",
            message,
        ):
            # Stop running profiles first
            for pid in profile_ids:
                profile = self._safe_get_profile(pid)
                if profile is not None and self.launcher.is_running(pid):
                    await self._stop_profile(profile)

            # Then delete
            for pid in profile_ids:
                try:
                    self.storage.delete_profile(pid)
                except (ValueError, ProfileNotFoundError, StorageError) as e:
                    logger.warning("Failed to delete profile %s: %s", pid, e)
            self._refresh_folders()
            self._refresh_table()
            self._refresh_trash()
            self.profiles_page._deselect_all()

    # --- Trash operations ---

    def _refresh_trash(self):
        """Refresh trash page."""
        trash = self.storage.get_trash()
        self.trash_page.update_deleted_profiles(trash)

    def _restore_profiles_from_trash(self, profile_ids: list[str]):
        """Restore profiles from trash."""
        for pid in profile_ids:
            self.storage.restore_from_trash(pid)
        self._refresh_folders()
        self._refresh_table()
        self._refresh_trash()

    def _permanently_delete_profiles(self, profile_ids: list[str]):
        """Permanently delete profiles from trash."""
        for pid in profile_ids:
            self.storage.permanently_delete(pid)
        self._refresh_trash()

    def _empty_trash(self):
        """Empty all items from trash."""
        self.storage.empty_trash()
        self._refresh_trash()

    # --- Proxy batch operations ---

    def _batch_ping_proxies(self, indices: list[int]):
        """Ping selected proxies."""
        if not indices:
            return
        proxies = self.proxy_page.get_proxies()
        selected_proxies = [proxies[i] for i in indices if i < len(proxies)]
        if selected_proxies:
            self._spawn_task(
                self._do_batch_ping_proxies(selected_proxies),
                context=f"batch_ping_proxies({len(selected_proxies)})",
            )

    async def _do_batch_ping_proxies(self, proxies: list):
        """Perform batch proxy ping with concurrency limit."""
        # Limit concurrent pings to avoid overwhelming network
        semaphore = asyncio.Semaphore(10)  # Max 10 simultaneous pings

        async def ping_one(proxy) -> None:
            async with semaphore:
                ping_ms = await ping_proxy(proxy)
                proxy.ping_ms = ping_ms
                if ping_ms > 0 and not proxy.country_code:
                    geo = await detect_proxy_geo(proxy)
                    if geo:
                        proxy.country_code = geo.get("country_code", "")
                        proxy.country_name = geo.get("country_name", "")

        tasks = [ping_one(p) for p in proxies]
        await asyncio.gather(*tasks, return_exceptions=True)
        self.proxy_page._refresh_table()

    def _batch_delete_proxies(self, indices: list[int]):
        """Delete selected proxies."""
        if not indices:
            return

        if confirm_dialog(
            self,
            "Delete Proxies",
            f"Delete {len(indices)} selected proxies?",
        ):
            proxies = self.proxy_page.get_proxies()
            # Remove from highest index first to preserve indices
            for idx in sorted(indices, reverse=True):
                if idx < len(proxies):
                    proxies.pop(idx)
            self.proxy_page.update_proxies(proxies)
            self.proxy_page.proxy_pool_changed.emit(proxies)
            self.proxy_page._deselect_all()

    # --- Tags batch operations ---

    def _batch_delete_tags(self, tag_names: list[str]):
        """Delete selected tags."""
        if not tag_names:
            return

        if confirm_dialog(
            self,
            "Delete Tags",
            f"Delete {len(tag_names)} selected tags?",
        ):
            for tag in tag_names:
                self.storage.remove_tag_from_pool(tag)
                for profile in self.storage.get_profiles():
                    if tag in profile.tags:
                        profile.tags.remove(tag)
                        self.storage.update_profile(profile)
            self._refresh_tags()
            self._refresh_table()
            self.tags_page._deselect_all_tags()

    def _batch_delete_statuses(self, status_names: list[str]):
        """Delete selected statuses."""
        if not status_names:
            return

        if confirm_dialog(
            self,
            "Delete Statuses",
            f"Delete {len(status_names)} selected statuses?",
        ):
            for name in status_names:
                self.storage.remove_status_from_pool(name)
            self.tags_page.update_statuses(self.storage.get_statuses_pool())
            self.tags_page._deselect_all_statuses()

    def _batch_delete_templates(self, template_names: list[str]):
        """Delete selected note templates."""
        if not template_names:
            return

        if confirm_dialog(
            self,
            "Delete Templates",
            f"Delete {len(template_names)} selected templates?",
        ):
            for name in template_names:
                self.storage.remove_note_template_from_pool(name)
            self.tags_page.update_note_templates(self.storage.get_note_templates_pool())
            self.tags_page._deselect_all_templates()

    def resizeEvent(self, event):
        """Handle window resize with auto-collapse sidebar."""
        super().resizeEvent(event)
        
        # Auto-collapse sidebar when window width is less than 1400px
        # Auto-expand when window width is more than 1500px (with hysteresis)
        width = event.size().width()
        
        if width < 1400 and not self.mini_sidebar._collapsed:
            self.mini_sidebar.set_collapsed(True)
        elif width > 1500 and self.mini_sidebar._collapsed:
            self.mini_sidebar.set_collapsed(False)

    def closeEvent(self, event):
        """Handle window close with graceful browser shutdown."""
        # Save window size and position
        self.settings.window_width = self.width()
        self.settings.window_height = self.height()
        self.settings.window_x = self.x()
        self.settings.window_y = self.y()
        self.storage.update_settings(self.settings)

        # Graceful shutdown all running browsers
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Best-effort: don't block close for too long.
            self._spawn_task(self.launcher.cleanup(), context="launcher.cleanup")

        event.accept()


def main():
    """Main entry point."""
    # Install secure logging filter to prevent credential leaks
    install_secure_logging()

    from antidetect_playwright.config import load_config

    config_dir = os.environ.get("APP_CONFIG_DIR") or ".config"
    config = load_config(config_dir)

    # Enable HiDPI support before creating QApplication
    # Must be set before QApplication instantiation
    from PyQt6.QtCore import Qt

    # PyQt6 has HiDPI enabled by default, we just set the rounding policy
    # AA_EnableHighDpiScaling and AA_UseHighDpiPixmaps are Qt5 only and not needed in Qt6
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setProperty("inline_alert_ttl_ms", config.gui.inline_alert_ttl_ms)

    # Set application icon
    icon_path = Path(__file__).parent.parent.parent / "assets" / "icons" / "app-icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Setup async event loop with qasync
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    # Use qasync event loop - run_forever integrates with Qt
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
