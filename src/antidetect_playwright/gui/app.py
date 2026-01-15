"""Main application window - Dolphin Anty style."""

import os
import sys
import asyncio
import warnings
from datetime import datetime
from pathlib import Path
import logging

# Suppress warnings
os.environ["QT_ACCESSIBILITY"] = "0"
os.environ["QT_LOGGING_RULES"] = "qt.accessibility.atspi=false"
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
    QMenu,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, QSize
import qasync

from .models import BrowserProfile, ProfileStatus
from .storage import Storage, StorageError, ProfileNotFoundError
from .launcher import BrowserLauncher
from .theme import Theme
from .icons import get_icon
from .security import install_secure_logging
from .widgets import (
    StatusBadge,
    TagsWidget,
    NotesWidget,
    ProxyWidget,
    ProfileNameWidget,
)
from .dialogs import (
    ProfileDialog,
    QuickProfileDialog,
    FolderDialog,
    TagsEditDialog,
    NotesEditDialog,
    ProxyPoolDialog,
    SettingsDialog,
    ProfileDataDialog,
)
from .proxy_utils import ping_proxy, detect_proxy_geo
from .components import MiniSidebar
from .pages import ProfilesPage, ProxyPage, TagsPage, TrashPage


class MainWindow(QMainWindow):
    """Main application window with Dolphin Anty-style UI."""

    def __init__(self):
        super().__init__()

        self.storage = Storage("data")
        self.settings = self.storage.get_settings()
        self.launcher = BrowserLauncher(Path("data/browser_data"), self.settings)

        # State
        self.current_folder = ""
        self.current_tag = ""
        self.search_query = ""
        self.current_page = 1

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

    def _refresh_table(self):
        """Refresh profiles table."""
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
            return
        else:
            self.profiles_page.show_table()

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

            # Actions (index 6)
            actions_widget = QWidget()
            actions_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            actions_widget.customContextMenuRequested.connect(
                lambda _pos, p=profile, w=actions_widget: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            btn_size = Theme.BTN_ICON_SIZE

            menu_btn = QPushButton("⋯")
            menu_btn.setFixedSize(btn_size, btn_size)
            menu_btn.setProperty("class", "icon")
            menu_btn.setToolTip("Menu")
            menu_btn.clicked.connect(
                lambda checked=False, p=profile, w=menu_btn: self._show_profile_context_menu(
                    p, w.mapToGlobal(w.rect().bottomLeft())
                )
            )
            actions_layout.addWidget(menu_btn)

            ping_btn = QPushButton()
            ping_btn.setIcon(get_icon("ping", 14))
            ping_btn.setIconSize(QSize(14, 14))
            ping_btn.setFixedSize(btn_size, btn_size)
            ping_btn.setProperty("class", "icon")
            ping_btn.setToolTip("Ping")
            ping_btn.clicked.connect(
                lambda checked=False, p=profile: self._ping_proxy(p)
            )
            ping_btn.setEnabled(bool(profile.proxy and profile.proxy.enabled))
            actions_layout.addWidget(ping_btn)

            change_btn = QPushButton()
            change_btn.setIcon(get_icon("swap", 14))
            change_btn.setIconSize(QSize(14, 14))
            change_btn.setFixedSize(btn_size, btn_size)
            change_btn.setProperty("class", "icon")
            change_btn.setToolTip("Quick change proxy")
            change_btn.clicked.connect(
                lambda checked=False, p=profile: self._quick_change_proxy(p)
            )
            actions_layout.addWidget(change_btn)

            actions_layout.addStretch()
            table.setIndexWidget(self.profiles_page.table_model.index(row, 6), actions_widget)

        # Keep toolbar + header checkbox state consistent after rebuild
        self.profiles_page._update_selection()
        self.profiles_page._update_header_checkbox_state()

    def _refresh_tags(self):
        """Refresh tag filters."""
        tags = self.storage.get_all_tags()
        self.profiles_page.update_tag_filter(tags, self.current_tag)

        # Calculate tag counts for tags management
        tag_counts = {}
        for tag in tags:
            count = sum(1 for p in self.storage.get_profiles() if tag in p.tags)
            tag_counts[tag] = count

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
        self._refresh_table()

    def _on_per_page_change(self, per_page: int):
        """Handle items per page change."""
        self.settings.items_per_page = per_page
        self.storage.update_settings(self.settings)
        self.current_page = 1
        self._refresh_table()

    def _create_profile(self):
        """Open profile creation dialog."""
        dialog = ProfileDialog(storage=self.storage, parent=self)
        if dialog.exec():
            profile = dialog.get_profile()
            profile.folder_id = self.current_folder
            self.storage.add_profile(profile)
            self._refresh_table()
            self._refresh_folders()

    def _quick_create_profile(self):
        """Quick profile creation."""
        dialog = QuickProfileDialog(parent=self)
        if dialog.exec():
            profile = dialog.get_profile()
            profile.folder_id = self.current_folder
            self.storage.add_profile(profile)
            self._refresh_table()
            self._refresh_folders()

    def _create_folder(self):
        """Create new folder."""
        dialog = FolderDialog(parent=self)
        if dialog.exec():
            folder = dialog.get_folder()
            self.storage.add_folder(folder)
            self._refresh_folders()

    def _show_settings(self):
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec():
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
            dialog = FolderDialog(folder, parent=self)
            if dialog.exec():
                self.storage.update_folder(dialog.get_folder())
                self._refresh_folders()

    def _delete_folder(self, folder_id: str):
        """Delete folder."""
        reply = QMessageBox.question(
            self,
            "Delete Folder",
            "Delete this folder? Profiles will be moved to All Profiles.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
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
            stop_action = menu.addAction("Stop")
            stop_action.triggered.connect(lambda: self._stop_profile(profile))
        else:
            start_action = menu.addAction("Start")
            start_action.triggered.connect(lambda: self._start_profile(profile))

        menu.addSeparator()

        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self._edit_profile(profile))

        # View Profile Data (fingerprint, cookies, storage, etc.)
        data_action = menu.addAction("View Profile Data")
        data_action.triggered.connect(lambda: self._view_fingerprint(profile))

        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self._duplicate_profile(profile))

        menu.addSeparator()

        # Move to folder submenu
        move_menu = menu.addMenu("Move to Folder")

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

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_profile(profile))

        menu.exec(pos)

    def _view_fingerprint(self, profile: BrowserProfile):
        """Show fingerprint dialog for profile."""
        data_dir = self.storage.get_browser_data_dir()
        dialog = ProfileDataDialog(profile, data_dir, parent=self)
        dialog.exec()

    def _edit_profile(self, profile: BrowserProfile):
        """Edit profile."""
        dialog = ProfileDialog(profile, storage=self.storage, parent=self)
        if dialog.exec():
            updated_profile = dialog.get_profile()

            # If regenerate was requested, delete fingerprint.json
            if dialog.should_regenerate():
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
        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile '{profile.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
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
        profile.last_used = datetime.now()
        self.storage.update_profile(profile)

        if self.launcher.is_running(profile.id):
            return
        success = await self.launcher.launch_profile(profile)
        if success:
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
        """Handle status change from launcher."""
        profile = self._safe_get_profile(profile_id)
        if profile is not None:
            profile.status = status
            self.storage.update_profile(profile)
        self._refresh_table()

    def _on_browser_closed(self, profile_id: str):
        """Handle browser manually closed."""
        profile = self._safe_get_profile(profile_id)
        if profile is not None:
            profile.status = ProfileStatus.STOPPED
            self.storage.update_profile(profile)
        self._refresh_table()

    def _edit_notes(self, profile: BrowserProfile):
        """Edit profile notes."""
        dialog = NotesEditDialog(
            profile.notes,
            note_templates=self.storage.get_note_templates_pool(),
            parent=self,
        )
        if dialog.exec():
            profile.notes = dialog.get_notes()
            self.storage.update_profile(profile)
            self._refresh_table()

    def _edit_tags(self, profile: BrowserProfile):
        """Edit profile tags."""
        all_tags = self.storage.get_all_tags()
        dialog = TagsEditDialog(profile.tags, all_tags, parent=self)
        if dialog.exec():
            profile.tags = dialog.get_tags()
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
            QMessageBox.information(
                self,
                "Proxy Pool Empty",
                "No proxies in pool. Add proxies via Proxy Pool button.",
            )

    def _open_proxy_pool(self):
        """Open proxy pool dialog."""
        pool = self.storage.get_proxy_pool()
        dialog = ProxyPoolDialog(pool.proxies, parent=self)
        if dialog.exec():
            self.storage.set_proxy_pool(dialog.get_proxies())

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
        """Start multiple profiles."""
        for pid in profile_ids:
            profile = self._safe_get_profile(pid)
            if profile is not None:
                self._start_profile(profile)

    def _batch_stop_profiles(self, profile_ids: list[str]):
        """Stop multiple profiles."""
        for pid in profile_ids:
            profile = self._safe_get_profile(pid)
            if profile is not None:
                self._stop_profile(profile)

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

        dialog = TagsEditDialog(profiles[0].tags, self.storage.get_all_tags(), self)
        if dialog.exec():
            new_tags = dialog.get_tags()
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

        dialog = NotesEditDialog(
            "",
            note_templates=self.storage.get_note_templates_pool(),
            parent=self,
        )
        if dialog.exec():
            new_notes = dialog.get_notes()
            for profile in profiles:
                profile.notes = new_notes
                self.storage.update_profile(profile)
            self._refresh_table()

    def _batch_ping_profiles(self, profile_ids: list[str]):
        """Ping proxies for multiple profiles."""
        for pid in profile_ids:
            profile = self._safe_get_profile(pid)
            if profile is not None and profile.proxy.enabled:
                self._ping_proxy(profile)

    def _batch_delete_profiles(self, profile_ids: list[str]):
        """Delete multiple profiles."""
        if not profile_ids:
            return

        reply = QMessageBox.question(
            self,
            "Delete Profiles",
            f"Delete {len(profile_ids)} selected profiles?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for pid in profile_ids:
                profile = self._safe_get_profile(pid)
                if profile is not None:
                    self._stop_profile(profile)
                try:
                    self.storage.delete_profile(pid)
                except (ValueError, ProfileNotFoundError, StorageError) as e:
                    logging.getLogger(__name__).warning(
                        "Failed to delete profile %s: %s", pid, e
                    )
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
        """Perform batch proxy ping."""

        async def ping_one(proxy) -> None:
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

        reply = QMessageBox.question(
            self,
            "Delete Proxies",
            f"Delete {len(indices)} selected proxies?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
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

        reply = QMessageBox.question(
            self,
            "Delete Tags",
            f"Delete {len(tag_names)} selected tags?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
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

        reply = QMessageBox.question(
            self,
            "Delete Statuses",
            f"Delete {len(status_names)} selected statuses?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for name in status_names:
                self.storage.remove_status_from_pool(name)
            self.tags_page.update_statuses(self.storage.get_statuses_pool())
            self.tags_page._deselect_all_statuses()

    def _batch_delete_templates(self, template_names: list[str]):
        """Delete selected note templates."""
        if not template_names:
            return

        reply = QMessageBox.question(
            self,
            "Delete Templates",
            f"Delete {len(template_names)} selected templates?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for name in template_names:
                self.storage.remove_note_template_from_pool(name)
            self.tags_page.update_note_templates(self.storage.get_note_templates_pool())
            self.tags_page._deselect_all_templates()

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

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setProperty("inline_alert_ttl_ms", config.gui.inline_alert_ttl_ms)

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
