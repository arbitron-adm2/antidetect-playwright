"""Dialogs for profile, folder, proxy and tag editing."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QTabWidget,
    QWidget,
    QLabel,
    QPushButton,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
    QHeaderView,
    QMessageBox,
    QCheckBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QIcon

from .models import BrowserProfile, Folder, ProxyConfig, ProxyType
from .styles import COLORS, get_country_flag
from .proxy_utils import parse_proxy_string
from .modal import (
    confirm_dialog,
    info_dialog,
    error_dialog,
    warning_dialog,
    get_item_dialog,
)


class ProfileDialog(QDialog):
    """Dialog for creating/editing a profile.

    Simplified UX - only name, proxy and OS needed.
    Everything else is auto-configured.
    """

    def __init__(
        self, profile: BrowserProfile | None = None, storage=None, parent=None
    ):
        super().__init__(parent)
        self.profile = profile or BrowserProfile()
        self.is_new = profile is None
        self.storage = storage
        self._regenerate_on_save = False  # Flag for fingerprint regeneration
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("New Profile" if self.is_new else "Edit Profile")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        from .components import InlineAlert, make_combobox_searchable

        self._alert = InlineAlert(self)
        layout.addWidget(self._alert)

        # Name
        name_group = QGroupBox("Profile")
        name_layout = QFormLayout(name_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile name")
        self.name_input.textChanged.connect(
            lambda _t: self._clear_error(self.name_input)
        )
        name_layout.addRow("Name:", self.name_input)

        self.os_combo = QComboBox()
        self.os_combo.addItems(["macOS", "Windows", "Linux"])
        make_combobox_searchable(self.os_combo, "Search OS")

        # OS cannot be changed after profile creation (fingerprint is tied to OS)
        if not self.is_new:
            self.os_combo.setEnabled(False)
            self.os_combo.setToolTip(
                "OS cannot be changed. Use 'Regenerate Fingerprint' to change OS."
            )

        name_layout.addRow("OS:", self.os_combo)

        layout.addWidget(name_group)

        # Regenerate Fingerprint button (only for existing profiles)
        if not self.is_new:
            regen_group = QGroupBox("Fingerprint")
            regen_layout = QVBoxLayout(regen_group)

            regen_info = QLabel(
                "Fingerprint is generated once and saved for consistency.\n"
                "Regenerating will change all browser identifiers."
            )
            regen_info.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 11px;"
            )
            regen_info.setWordWrap(True)
            regen_layout.addWidget(regen_info)

            regen_btn = QPushButton("🔄 Regenerate Fingerprint")
            regen_btn.setStyleSheet(
                f"""
                background-color: {COLORS['warning']};
                color: white;
                font-weight: 600;
                padding: 8px 16px;
            """
            )
            regen_btn.clicked.connect(self._regenerate_fingerprint)
            regen_layout.addWidget(regen_btn)

            layout.addWidget(regen_group)

        # Proxy
        proxy_group = QGroupBox("Proxy (Optional)")
        proxy_layout = QVBoxLayout(proxy_group)

        # Quick paste
        paste_layout = QHBoxLayout()
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText(
            "host:port or host:port:user:pass or socks5://..."
        )
        self.proxy_input.textChanged.connect(
            lambda _t: self._clear_error(self.proxy_input)
        )
        paste_layout.addWidget(self.proxy_input)

        parse_btn = QPushButton("Parse")
        parse_btn.clicked.connect(self._parse_proxy)
        paste_layout.addWidget(parse_btn)

        # From pool button
        if self.storage:
            pool_btn = QPushButton("From Pool")
            pool_btn.clicked.connect(self._select_from_pool)
            paste_layout.addWidget(pool_btn)

        proxy_layout.addLayout(paste_layout)

        # Parsed proxy display
        self.proxy_info = QLabel("No proxy configured")
        self.proxy_info.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 8px;")
        proxy_layout.addWidget(self.proxy_info)

        # Clear proxy button
        clear_btn = QPushButton("Clear Proxy")
        clear_btn.clicked.connect(self._clear_proxy)
        proxy_layout.addWidget(clear_btn)

        layout.addWidget(proxy_group)

        # Info
        info_label = QLabel(
            "Fingerprint (User-Agent, WebGL, etc.) will be auto-generated.\n"
            "If proxy is set, timezone and language will be auto-detected from IP."
        )
        info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            f"""
            background-color: {COLORS['accent']};
            color: white;
            font-weight: 600;
        """
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(self.profile.name)

        os_map = {"macos": 0, "windows": 1, "linux": 2}
        self.os_combo.setCurrentIndex(os_map.get(self.profile.os_type, 0))

        if self.profile.proxy.enabled:
            self._update_proxy_info()

    def _parse_proxy(self):
        text = self.proxy_input.text().strip()
        if not text:
            return

        proxy = parse_proxy_string(text)
        if proxy:
            self.profile.proxy = proxy
            self._update_proxy_info()
            self.proxy_input.clear()
            self._clear_error(self.proxy_input)
        else:
            self._set_error(self.proxy_input, True)
            self._alert.show_error("Parse Error", "Could not parse proxy string")

    def _update_proxy_info(self):
        p = self.profile.proxy
        if p.enabled:
            auth = f" (auth: {p.username})" if p.username else ""
            self.proxy_info.setText(
                f"[OK] {p.proxy_type.value.upper()}://{p.host}:{p.port}{auth}"
            )
            self.proxy_info.setStyleSheet(f"color: {COLORS['success']}; padding: 8px;")
        else:
            self.proxy_info.setText("No proxy configured")
            self.proxy_info.setStyleSheet(
                f"color: {COLORS['text_muted']}; padding: 8px;"
            )

    def _clear_proxy(self):
        self.profile.proxy = ProxyConfig()
        self._update_proxy_info()

    def _select_from_pool(self):
        """Select proxy from pool."""
        if not self.storage:
            return

        proxy_pool = self.storage.get_proxy_pool()
        if not proxy_pool.proxies:
            info_dialog(
                self,
                "Empty Pool",
                "Proxy pool is empty. Add proxies in the Proxy page first.",
            )
            return

        # Create selection dialog
        items = []
        for proxy in proxy_pool.proxies:
            auth = f" (auth: {proxy.username})" if proxy.username else ""
            flag = get_country_flag(proxy.country_code)
            label = f"{proxy.proxy_type.value.upper()}://{proxy.host}:{proxy.port}{auth}"
            if flag:
                label = f"{flag} {label}"
            items.append(label)

        item, ok = get_item_dialog(
            self,
            "Select Proxy from Pool",
            "Choose proxy:",
            items,
            0,
            False,
        )

        if ok and item:
            # Get index and set proxy
            idx = items.index(item)
            self.profile.proxy = proxy_pool.proxies[idx]
            self._update_proxy_info()

    def _regenerate_fingerprint(self):
        """Show confirmation and mark fingerprint for regeneration."""
        # Enable OS combo temporarily to allow selection
        self.os_combo.setEnabled(True)

        if confirm_dialog(
            self,
            "Regenerate Fingerprint",
            "⚠️ This will generate a completely new fingerprint:\n\n"
            "• New User-Agent\n"
            "• New WebGL signature\n"
            "• New Canvas fingerprint\n"
            "• New hardware identifiers\n\n"
            "The profile will appear as a different browser.\n"
            "Select the OS for the new fingerprint and click Save.\n\n"
            "Continue?",
            icon=QMessageBox.Icon.Warning,
        ):
            # Mark for regeneration - will delete fingerprint.json on save
            self._regenerate_on_save = True
            self._alert.show_success(
                "Ready", "Select OS and click Save to regenerate fingerprint"
            )
        else:
            # Re-disable if cancelled
            self.os_combo.setEnabled(False)

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._set_error(self.name_input, True)
            self._alert.show_error("Error", "Profile name is required")
            return

        self.profile.name = name

        os_map = {0: "macos", 1: "windows", 2: "linux"}
        self.profile.os_type = os_map.get(self.os_combo.currentIndex(), "macos")

        self.accept()

    def _set_error(self, widget: QWidget, is_error: bool) -> None:
        widget.setProperty("error", "true" if is_error else "false")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _clear_error(self, widget: QWidget) -> None:
        self._set_error(widget, False)
        self._alert.hide()

    def get_profile(self) -> BrowserProfile:
        return self.profile

    def should_regenerate(self) -> bool:
        """Check if fingerprint should be regenerated."""
        return self._regenerate_on_save


class QuickProfileDialog(QDialog):
    """Quick profile creation - just name, creates with defaults."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile = BrowserProfile()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Quick Profile")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(
            QLabel("Create a new profile with auto-configured fingerprint:")
        )

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile name")
        self.name_input.returnPressed.connect(self._save)
        layout.addWidget(self.name_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create")
        create_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        create_btn.clicked.connect(self._save)
        btn_layout.addWidget(create_btn)

        layout.addLayout(btn_layout)

        self.name_input.setFocus()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            return
        self.profile.name = name
        self.accept()

    def get_profile(self) -> BrowserProfile:
        return self.profile


class FolderDialog(QDialog):
    """Dialog for creating/editing a folder."""

    COLORS_LIST = [
        ("#6366f1", "Indigo"),
        ("#ec4899", "Pink"),
        ("#22c55e", "Green"),
        ("#f59e0b", "Orange"),
        ("#3b82f6", "Blue"),
        ("#8b5cf6", "Purple"),
        ("#14b8a6", "Teal"),
        ("#f43f5e", "Rose"),
    ]

    def __init__(self, folder: Folder | None = None, parent=None):
        super().__init__(parent)
        self.folder = folder or Folder()
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("New Folder" if not self.folder.name else "Edit Folder")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        from .components import InlineAlert, make_combobox_searchable

        self._alert = InlineAlert(self)
        layout.addWidget(self._alert)

        # Name
        layout.addWidget(QLabel("Folder Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Folder name")
        self.name_input.textChanged.connect(
            lambda _t: self._clear_error(self.name_input)
        )
        layout.addWidget(self.name_input)

        # Color
        layout.addWidget(QLabel("Color:"))
        self.color_combo = QComboBox()
        for color, name in self.COLORS_LIST:
            # Create colored icon
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(color))
            icon = QIcon(pixmap)
            self.color_combo.addItem(icon, name, color)
        make_combobox_searchable(self.color_combo, "Search color")
        self.color_combo.setStyleSheet(
            f"""
            QComboBox::item {{
                padding: 4px 8px;
            }}
        """
        )
        layout.addWidget(self.color_combo)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.name_input.setText(
            self.folder.name if self.folder.name != "New Folder" else ""
        )

        for i, (color, _) in enumerate(self.COLORS_LIST):
            if color == self.folder.color:
                self.color_combo.setCurrentIndex(i)
                break

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self._set_error(self.name_input, True)
            self._alert.show_error("Error", "Folder name is required")
            return

        self.folder.name = name
        self.folder.color = self.color_combo.currentData()
        self.accept()

    def _set_error(self, widget: QWidget, is_error: bool) -> None:
        widget.setProperty("error", "true" if is_error else "false")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _clear_error(self, widget: QWidget) -> None:
        self._set_error(widget, False)
        self._alert.hide()

    def get_folder(self) -> Folder:
        return self.folder


class TagsEditDialog(QDialog):
    """Dialog for editing profile tags."""

    def __init__(self, current_tags: list[str], all_tags: list[str], parent=None):
        super().__init__(parent)
        self.current_tags = list(current_tags)
        self.all_tags = all_tags
        self.available_tags = [t for t in self.all_tags if t not in self.current_tags]
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Tags")
        self.setMinimumSize(450, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        from .components import InlineAlert

        self._alert = InlineAlert(self)
        layout.addWidget(self._alert)

        # Add from pool section
        if self.available_tags:
            layout.addWidget(QLabel("Add from pool:"))

            search_layout = QHBoxLayout()
            search_layout.setSpacing(8)

            self.available_search = QLineEdit()
            self.available_search.setPlaceholderText("Search tags")
            self.available_search.textChanged.connect(self._filter_available_tags)
            search_layout.addWidget(self.available_search, 1)
            layout.addLayout(search_layout)

            self.available_list = QListWidget()
            self.available_list.addItems(self.available_tags)
            self.available_list.itemDoubleClicked.connect(
                lambda _item: self._add_from_pool()
            )
            layout.addWidget(self.available_list, 1)

            add_pool_btn = QPushButton("Add")
            add_pool_btn.setProperty("class", "primary")
            add_pool_btn.clicked.connect(self._add_from_pool)
            layout.addWidget(add_pool_btn)
        else:
            self.available_search = None
            self.available_list = None

        # Add custom tag section
        layout.addWidget(QLabel("Add custom tag:"))

        custom_layout = QHBoxLayout()
        custom_layout.setSpacing(8)

        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Enter new tag name...")
        self.new_tag_input.returnPressed.connect(self._add_custom_tag)
        custom_layout.addWidget(self.new_tag_input, 1)

        add_custom_btn = QPushButton("Add")
        add_custom_btn.clicked.connect(self._add_custom_tag)
        custom_layout.addWidget(add_custom_btn)

        layout.addLayout(custom_layout)

        # Current tags list
        layout.addWidget(QLabel("Current tags (click to remove):"))
        self.tags_list = QListWidget()
        self.tags_list.itemClicked.connect(self._remove_tag)
        self._refresh_tags_list()
        layout.addWidget(self.tags_list, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _refresh_tags_list(self):
        self.tags_list.clear()
        for tag in self.current_tags:
            item = QListWidgetItem(f"✕  {tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.tags_list.addItem(item)

    def _filter_available_tags(self, text: str) -> None:
        if not self.available_list:
            return
        text = text.lower().strip()
        for row in range(self.available_list.count()):
            item = self.available_list.item(row)
            item.setHidden(text not in item.text().lower())

    def _refresh_available_list(self) -> None:
        if not self.available_list:
            return
        self.available_list.clear()
        self.available_list.addItems(self.available_tags)
        if self.available_search:
            self._filter_available_tags(self.available_search.text())

    def _add_from_pool(self):
        if not self.available_list:
            return
        item = self.available_list.currentItem()
        if not item and self.available_list.count() > 0:
            self.available_list.setCurrentRow(0)
            item = self.available_list.currentItem()
        if not item:
            return
        tag = item.text().strip()
        if not tag:
            return
        if tag in self.current_tags:
            self._alert.show_error("Duplicate", f"Tag '{tag}' already added.")
            return
        self.current_tags.append(tag)
        if tag in self.available_tags:
            self.available_tags.remove(tag)
        self._refresh_tags_list()
        self._refresh_available_list()

    def _add_custom_tag(self):
        tag = self.new_tag_input.text().strip()
        if not tag:
            return
        if tag in self.current_tags:
            self._alert.show_error("Duplicate", f"Tag '{tag}' already added.")
            return
        self.current_tags.append(tag)
        if tag in self.available_tags:
            self.available_tags.remove(tag)
        self._refresh_tags_list()
        self._refresh_available_list()
        self.new_tag_input.clear()

    def _remove_tag(self, item: QListWidgetItem):
        tag = item.data(Qt.ItemDataRole.UserRole)
        if tag in self.current_tags:
            self.current_tags.remove(tag)
            self._refresh_tags_list()
            if tag in self.all_tags and tag not in self.available_tags:
                self.available_tags.append(tag)
                self.available_tags.sort()
                self._refresh_available_list()

    def get_tags(self) -> list[str]:
        return self.current_tags


class NotesEditDialog(QDialog):
    """Dialog for editing profile notes."""

    def __init__(
        self,
        notes: str,
        note_templates: list[tuple[str, str]] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.notes = notes
        self._note_templates = list(note_templates or [])
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Notes")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        from .components import InlineAlert

        self._alert = InlineAlert(self)
        layout.addWidget(self._alert)

        # Templates section (if available)
        if self._note_templates:
            layout.addWidget(QLabel("Insert from templates:"))

            self.template_search = QLineEdit()
            self.template_search.setPlaceholderText("Search templates")
            self.template_search.textChanged.connect(self._filter_templates)
            layout.addWidget(self.template_search)

            self.template_list = QListWidget()
            self.template_list.addItems([name for name, _ in self._note_templates])
            self.template_list.itemDoubleClicked.connect(
                lambda _item: self._insert_template()
            )
            layout.addWidget(self.template_list, 1)

            templates_row = QHBoxLayout()
            templates_row.setSpacing(8)

            insert_btn = QPushButton("Insert")
            insert_btn.setProperty("class", "primary")
            insert_btn.clicked.connect(self._insert_template)
            templates_row.addWidget(insert_btn)

            replace_btn = QPushButton("Replace")
            replace_btn.clicked.connect(self._replace_with_template)
            templates_row.addWidget(replace_btn)

            layout.addLayout(templates_row)
        else:
            self.template_search = None
            self.template_list = None

        # Notes editor
        layout.addWidget(QLabel("Notes:"))
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Enter notes for this profile...")
        self.notes_edit.setText(self.notes)
        layout.addWidget(self.notes_edit, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _filter_templates(self, text: str) -> None:
        if not self.template_list:
            return
        text = text.lower().strip()
        for row in range(self.template_list.count()):
            item = self.template_list.item(row)
            item.setHidden(text not in item.text().lower())

    def _selected_template_name(self) -> str:
        if not self.template_list:
            return ""
        item = self.template_list.currentItem()
        if not item and self.template_list.count() > 0:
            self.template_list.setCurrentRow(0)
            item = self.template_list.currentItem()
        return item.text().strip() if item else ""

    def _get_template_content(self, name: str) -> str:
        for n, content in self._note_templates:
            if n == name:
                return content
        return ""

    def _insert_template(self):
        if not self._note_templates:
            return
        name = self._selected_template_name()
        if not name:
            return
        content = self._get_template_content(name)
        if not content:
            self._alert.show_error("Error", f"Template '{name}' not found.")
            return

        current = self.notes_edit.toPlainText()
        if current and not current.endswith("\n"):
            current += "\n"
        current += content
        self.notes_edit.setPlainText(current)

    def _replace_with_template(self):
        if not self._note_templates:
            return
        name = self._selected_template_name()
        if not name:
            return
        content = self._get_template_content(name)
        if not content:
            self._alert.show_error("Error", f"Template '{name}' not found.")
            return
        self.notes_edit.setPlainText(content)

    def get_notes(self) -> str:
        return self.notes_edit.toPlainText()


class ProxyPoolDialog(QDialog):
    """Dialog for managing proxy pool."""

    def __init__(self, proxies: list[ProxyConfig], parent=None):
        super().__init__(parent)
        self.proxies = list(proxies)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Proxy Pool")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        from .components import InlineAlert

        self._alert = InlineAlert(self)
        layout.addWidget(self._alert)

        layout.addWidget(QLabel("Manage your proxy pool for quick rotation:"))

        # Proxy list
        self.proxy_list = QListWidget()
        self._refresh_list()
        layout.addWidget(self.proxy_list)

        # Add proxies
        layout.addWidget(QLabel("Add proxies (one per line):"))
        self.proxy_input = QTextEdit()
        self.proxy_input.setMaximumHeight(100)
        self.proxy_input.setPlaceholderText(
            "host:port\nhost:port:user:pass\nsocks5://host:port"
        )
        self.proxy_input.textChanged.connect(
            lambda: self._clear_error(self.proxy_input)
        )
        layout.addWidget(self.proxy_input)

        add_btn = QPushButton("Add Proxies")
        add_btn.clicked.connect(self._add_proxies)
        layout.addWidget(add_btn)

        # Buttons
        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _refresh_list(self):
        self.proxy_list.clear()
        for p in self.proxies:
            text = f"{p.proxy_type.value.upper()}://{p.host}:{p.port}"
            if p.username:
                text += " (auth)"
            flag = get_country_flag(p.country_code)
            if flag:
                text = f"{flag} {text}"
            item = QListWidgetItem(text)
            self.proxy_list.addItem(item)

    def _add_proxies(self):
        from .proxy_utils import parse_proxy_list

        text = self.proxy_input.toPlainText()
        new_proxies, errors = parse_proxy_list(text)
        self.proxies.extend(new_proxies)
        self._refresh_list()
        self.proxy_input.clear()

        if errors:
            self._set_error(self.proxy_input, True)
            self._alert.show_error(
                "Parse Errors", f"{len(errors)} line(s) failed to parse."
            )

    def _set_error(self, widget: QWidget, is_error: bool) -> None:
        widget.setProperty("error", "true" if is_error else "false")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _clear_error(self, widget: QWidget) -> None:
        self._set_error(widget, False)
        self._alert.hide()

    def _clear_all(self):
        self.proxies.clear()
        self._refresh_list()

    def get_proxies(self) -> list[ProxyConfig]:
        return self.proxies


class StatusEditDialog(QDialog):
    """Dialog for editing a status."""

    def __init__(self, name: str, color: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._color = color
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Status")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        form = QFormLayout()

        self.name_input = QLineEdit(self._name)
        self.name_input.setPlaceholderText("Status name...")
        form.addRow("Name:", self.name_input)

        self.color_combo = QComboBox()
        self.color_combo.addItems(["green", "red", "yellow", "blue", "gray"])
        from .components import make_combobox_searchable

        make_combobox_searchable(self.color_combo, "Search color")
        if self._color in ["green", "red", "yellow", "blue", "gray"]:
            self.color_combo.setCurrentText(self._color)
        form.addRow("Color:", self.color_combo)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def get_values(self) -> tuple[str, str]:
        """Return (name, color) tuple."""
        return self.name_input.text().strip(), self.color_combo.currentText()


class SettingsDialog(QDialog):
    """Dialog for application settings."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        from PyQt6.QtWidgets import (
            QCheckBox,
            QTabWidget,
            QWidget,
            QDoubleSpinBox,
            QListWidget,
            QListWidgetItem,
            QFileDialog,
        )

        self.setWindowTitle("Settings")
        self.setMinimumSize(650, 550)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Tab widget
        tabs = QTabWidget()

        # Browser tab
        browser_tab = QWidget()
        browser_layout = QFormLayout(browser_tab)
        browser_layout.setSpacing(12)

        self.save_tabs_checkbox = QCheckBox()
        browser_layout.addRow("Save & restore tabs:", self.save_tabs_checkbox)

        self.start_page_input = QLineEdit()
        self.start_page_input.setPlaceholderText("about:blank, https://google.com")
        browser_layout.addRow("Start page:", self.start_page_input)

        # Custom browser executable path
        browser_path_container = QHBoxLayout()
        self.browser_path_input = QLineEdit()
        self.browser_path_input.setPlaceholderText(
            "Leave empty to use bundled Camoufox"
        )
        browser_path_browse = QPushButton("Browse...")
        browser_path_browse.setFixedWidth(90)
        browser_path_browse.clicked.connect(self._browse_browser_path)
        browser_path_container.addWidget(self.browser_path_input)
        browser_path_container.addWidget(browser_path_browse)
        browser_path_widget = QWidget()
        browser_path_widget.setLayout(browser_path_container)
        browser_layout.addRow("Custom browser:", browser_path_widget)

        browser_path_help = QLabel("Path to custom AntiDetect browser executable")
        browser_path_help.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
        )
        browser_layout.addRow("", browser_path_help)

        browser_info = QLabel("Settings apply to all profiles when launching browser")
        browser_info.setWordWrap(True)
        browser_info.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; margin-top: 8px;"
        )
        browser_layout.addRow("", browser_info)

        tabs.addTab(browser_tab, "Browser")

        # Performance tab
        perf_tab = QWidget()
        perf_layout = QFormLayout(perf_tab)
        perf_layout.setSpacing(12)

        self.block_images_checkbox = QCheckBox()
        block_images_label = QLabel("Block images")
        block_images_help = QLabel("Saves bandwidth, faster page loads")
        block_images_help.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
        )
        block_images_container = QVBoxLayout()
        block_images_container.addWidget(self.block_images_checkbox)
        block_images_container.addWidget(block_images_help)
        block_images_container.setSpacing(4)
        perf_layout.addRow("Block images:", self.block_images_checkbox)
        perf_layout.addRow("", block_images_help)

        self.enable_cache_checkbox = QCheckBox()
        cache_help = QLabel("Cache pages and requests (uses more memory)")
        cache_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        perf_layout.addRow("Enable cache:", self.enable_cache_checkbox)
        perf_layout.addRow("", cache_help)

        tabs.addTab(perf_tab, "Performance")

        # Privacy tab
        privacy_tab = QWidget()
        privacy_layout = QFormLayout(privacy_tab)
        privacy_layout.setSpacing(12)

        self.humanize_spin = QDoubleSpinBox()
        self.humanize_spin.setRange(0.0, 5.0)
        self.humanize_spin.setSingleStep(0.1)
        self.humanize_spin.setDecimals(1)
        self.humanize_spin.setSuffix(" sec")
        humanize_help = QLabel("Humanize cursor movement delay (0 = disabled)")
        humanize_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        privacy_layout.addRow("Humanize cursor:", self.humanize_spin)
        privacy_layout.addRow("", humanize_help)

        tabs.addTab(privacy_tab, "Privacy")

        # Extensions tab
        ext_tab = QWidget()
        ext_layout = QVBoxLayout(ext_tab)
        ext_layout.setSpacing(12)

        exclude_label = QLabel("Exclude default extensions:")
        exclude_label.setStyleSheet(
            f"font-weight: 600; color: {COLORS['text_primary']};"
        )
        ext_layout.addWidget(exclude_label)

        self.exclude_ublock_checkbox = QCheckBox("uBlock Origin (ad blocker)")
        ext_layout.addWidget(self.exclude_ublock_checkbox)

        self.exclude_bpc_checkbox = QCheckBox("Bypass Paywalls Clean")
        ext_layout.addWidget(self.exclude_bpc_checkbox)

        ext_info = QLabel(
            "Note: Default extensions help with anti-detection and privacy"
        )
        ext_info.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; margin-top: 4px;"
        )
        ext_layout.addWidget(ext_info)

        ext_layout.addSpacing(20)

        custom_label = QLabel("Custom extensions (.xpi files):")
        custom_label.setStyleSheet(
            f"font-weight: 600; color: {COLORS['text_primary']};"
        )
        ext_layout.addWidget(custom_label)

        self.custom_addons_list = QListWidget()
        self.custom_addons_list.setMaximumHeight(120)
        ext_layout.addWidget(self.custom_addons_list)

        addons_btn_layout = QHBoxLayout()
        add_addon_btn = QPushButton("Add Extension")
        add_addon_btn.clicked.connect(self._add_addon)
        remove_addon_btn = QPushButton("Remove Selected")
        remove_addon_btn.clicked.connect(self._remove_addon)
        addons_btn_layout.addWidget(add_addon_btn)
        addons_btn_layout.addWidget(remove_addon_btn)
        addons_btn_layout.addStretch()
        ext_layout.addLayout(addons_btn_layout)

        ext_layout.addStretch()

        tabs.addTab(ext_tab, "Extensions")

        # Debug tab
        debug_tab = QWidget()
        debug_layout = QFormLayout(debug_tab)
        debug_layout.setSpacing(12)

        self.debug_checkbox = QCheckBox()
        debug_help = QLabel("Print Camoufox config to console on launch")
        debug_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        debug_layout.addRow("Debug mode:", self.debug_checkbox)
        debug_layout.addRow("", debug_help)

        tabs.addTab(debug_tab, "Debug")

        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

        self._load_settings()

    def _add_addon(self):
        """Add custom addon path."""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Extension File", "", "Firefox Extensions (*.xpi)"
        )
        if file_path:
            self.custom_addons_list.addItem(file_path)

    def _browse_browser_path(self):
        """Browse for custom browser executable."""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Browser Executable", "", "Executables (*)"
        )
        if file_path:
            self.browser_path_input.setText(file_path)

    def _remove_addon(self):
        """Remove selected addon from list."""
        current_item = self.custom_addons_list.currentItem()
        if current_item:
            self.custom_addons_list.takeItem(self.custom_addons_list.row(current_item))

    def _load_settings(self):
        """Load current settings into UI."""
        self.save_tabs_checkbox.setChecked(self.settings.save_tabs)
        self.start_page_input.setText(self.settings.start_page)
        self.browser_path_input.setText(self.settings.browser_executable_path)
        self.block_images_checkbox.setChecked(self.settings.block_images)
        self.enable_cache_checkbox.setChecked(self.settings.enable_cache)
        self.humanize_spin.setValue(self.settings.humanize)
        self.exclude_ublock_checkbox.setChecked(self.settings.exclude_ublock)
        self.exclude_bpc_checkbox.setChecked(self.settings.exclude_bpc)
        self.debug_checkbox.setChecked(self.settings.debug_mode)

        # Load custom addons
        self.custom_addons_list.clear()
        for addon_path in self.settings.custom_addons:
            self.custom_addons_list.addItem(addon_path)

    def _save(self):
        """Save settings and close."""
        self.settings.save_tabs = self.save_tabs_checkbox.isChecked()
        self.settings.start_page = self.start_page_input.text().strip() or "about:blank"
        self.settings.browser_executable_path = self.browser_path_input.text().strip()
        self.settings.block_images = self.block_images_checkbox.isChecked()
        self.settings.enable_cache = self.enable_cache_checkbox.isChecked()
        self.settings.humanize = self.humanize_spin.value()
        self.settings.exclude_ublock = self.exclude_ublock_checkbox.isChecked()
        self.settings.exclude_bpc = self.exclude_bpc_checkbox.isChecked()
        self.settings.debug_mode = self.debug_checkbox.isChecked()

        # Save custom addons
        self.settings.custom_addons = [
            self.custom_addons_list.item(i).text()
            for i in range(self.custom_addons_list.count())
        ]

        self.accept()


class ProfileDataDialog(QDialog):
    """Dialog to view profile data: fingerprint, cookies, storage, etc."""

    def __init__(self, profile: BrowserProfile, data_dir, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.data_dir = data_dir
        self._setup_ui()

    def _setup_ui(self):
        from PyQt6.QtWidgets import (
            QTabWidget,
            QTableWidget,
            QTableWidgetItem,
            QHeaderView,
        )

        self.setWindowTitle(f"Profile Data: {self.profile.name}")
        self.setMinimumSize(850, 650)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        from .components import InlineAlert

        self._alert = InlineAlert(self)

        # Header
        header = QLabel(f"Profile Data: {self.profile.name}")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {COLORS['text_primary']};"
        )
        layout.addWidget(header)

        layout.addWidget(self._alert)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background: {COLORS['bg_secondary']};
            }}
            QTabBar::tab {{
                padding: 8px 16px;
                margin-right: 4px;
                background: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background: {COLORS['bg_secondary']};
                color: {COLORS['accent']};
            }}
        """
        )

        # Tab 1: Fingerprint
        self.fingerprint_tab = self._create_fingerprint_tab()
        self.tabs.addTab(self.fingerprint_tab, "Fingerprint")

        # Tab 2: Cookies
        self.cookies_tab = self._create_cookies_tab()
        self.tabs.addTab(self.cookies_tab, "Cookies")

        # Tab 3: Storage (localStorage/IndexedDB)
        self.storage_tab = self._create_storage_tab()
        self.tabs.addTab(self.storage_tab, "Storage")

        # Tab 4: History
        self.history_tab = self._create_history_tab()
        self.tabs.addTab(self.history_tab, "History")

        # Tab 5: Cache
        self.cache_tab = self._create_cache_tab()
        self.tabs.addTab(self.cache_tab, "Cache")

        # Tab 6: Permissions
        self.permissions_tab = self._create_permissions_tab()
        self.tabs.addTab(self.permissions_tab, "Permissions")

        layout.addWidget(self.tabs)

        # Bottom buttons
        btn_layout = QHBoxLayout()

        clear_all_btn = QPushButton("Clear All Data")
        clear_all_btn.setStyleSheet(f"background: {COLORS['error']}; color: white;")
        clear_all_btn.clicked.connect(self._clear_all_data)
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_all)
        btn_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Load data for first tab
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self._load_fingerprint()

    def _create_text_display(self):
        """Create styled text display widget."""
        text_display = QTextEdit()
        text_display.setReadOnly(True)
        text_display.setStyleSheet(
            f"""
            QTextEdit {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-family: 'JetBrains Mono', 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                padding: 12px;
            }}
        """
        )
        return text_display

    def _create_fingerprint_tab(self):
        """Create fingerprint tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel(
            "Fingerprint is generated on first launch and persists for consistent identity."
        )
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(info)

        self.fingerprint_display = self._create_text_display()
        layout.addWidget(self.fingerprint_display)

        btn_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: self._copy_text(self.fingerprint_display))
        btn_layout.addWidget(copy_btn)

        regenerate_btn = QPushButton("Regenerate")
        regenerate_btn.setStyleSheet(f"background: {COLORS['warning']}; color: white;")
        regenerate_btn.clicked.connect(self._regenerate_fingerprint)
        btn_layout.addWidget(regenerate_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_cookies_tab(self):
        """Create cookies tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel(
            "Cookies stored by websites. Used for session persistence and tracking."
        )
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(info)

        self.cookies_table = QTableWidget()
        self.cookies_table.setColumnCount(5)
        self.cookies_table.setHorizontalHeaderLabels(
            ["Domain", "Name", "Value", "Expires", "Secure"]
        )
        self.cookies_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.cookies_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.cookies_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.cookies_table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                gridline-color: {COLORS['border']};
            }}
            QHeaderView::section {{
                background: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                padding: 8px;
                border: none;
            }}
        """
        )
        layout.addWidget(self.cookies_table)

        btn_layout = QHBoxLayout()

        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self._export_cookies)
        btn_layout.addWidget(export_btn)

        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self._import_cookies)
        btn_layout.addWidget(import_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"background: {COLORS['warning']}; color: white;")
        clear_btn.clicked.connect(self._clear_cookies)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_storage_tab(self):
        """Create localStorage/IndexedDB tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("localStorage and IndexedDB data stored by websites.")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(info)

        self.storage_display = self._create_text_display()
        layout.addWidget(self.storage_display)

        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"background: {COLORS['warning']}; color: white;")
        clear_btn.clicked.connect(self._clear_storage)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_history_tab(self):
        """Create browsing history tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Browsing history and bookmarks.")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(info)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["URL", "Title", "Visit Count"])
        self.history_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.history_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.history_table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                padding: 8px;
                border: none;
            }}
        """
        )
        layout.addWidget(self.history_table)

        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"background: {COLORS['warning']}; color: white;")
        clear_btn.clicked.connect(self._clear_history)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_cache_tab(self):
        """Create cache info tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Cached files from websites (images, scripts, styles, etc.)")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(info)

        self.cache_display = self._create_text_display()
        layout.addWidget(self.cache_display)

        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"background: {COLORS['warning']}; color: white;")
        clear_btn.clicked.connect(self._clear_cache)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _create_permissions_tab(self):
        """Create permissions tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        info = QLabel("Site permissions (notifications, geolocation, camera, etc.)")
        info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(info)

        self.permissions_table = QTableWidget()
        self.permissions_table.setColumnCount(3)
        self.permissions_table.setHorizontalHeaderLabels(
            ["Origin", "Permission", "Status"]
        )
        self.permissions_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.permissions_table.setStyleSheet(
            f"""
            QTableWidget {{
                background: {COLORS['bg_primary']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QHeaderView::section {{
                background: {COLORS['bg_tertiary']};
                color: {COLORS['text_primary']};
                padding: 8px;
                border: none;
            }}
        """
        )
        layout.addWidget(self.permissions_table)

        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"background: {COLORS['warning']}; color: white;")
        clear_btn.clicked.connect(self._clear_permissions)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        return widget

    def _on_tab_changed(self, index):
        """Load data when tab changes."""
        if index == 0:
            self._load_fingerprint()
        elif index == 1:
            self._load_cookies()
        elif index == 2:
            self._load_storage()
        elif index == 3:
            self._load_history()
        elif index == 4:
            self._load_cache()
        elif index == 5:
            self._load_permissions()

    def _refresh_all(self):
        """Refresh current tab."""
        self._on_tab_changed(self.tabs.currentIndex())

    def _get_profile_dir(self):
        """Get profile data directory."""
        from pathlib import Path

        return Path(self.data_dir) / self.profile.id

    def _load_fingerprint(self):
        """Load and display fingerprint data."""
        import json
        from pathlib import Path

        fingerprint_file = self._get_profile_dir() / "fingerprint.json"

        if not fingerprint_file.exists():
            self.fingerprint_display.setPlainText(
                "Fingerprint not yet generated.\n\n"
                "The fingerprint will be created on first profile launch.\n\n"
                "It will include:\n"
                "  - Navigator (User-Agent, platform, languages)\n"
                "  - Screen (resolution, color depth)\n"
                "  - WebGL (GPU vendor/renderer)\n"
                "  - Canvas (anti-aliasing settings)\n"
                "  - Fonts (spacing seed)\n"
                "  - And more"
            )
            return

        try:
            fp_data = json.loads(fingerprint_file.read_text())
            lines = self._format_fingerprint(fp_data)
            self.fingerprint_display.setPlainText("\n".join(lines))
        except Exception as e:
            self.fingerprint_display.setPlainText(f"Error loading fingerprint: {e}")

    def _format_fingerprint(self, fp_data):
        """Format fingerprint data for display."""
        lines = []
        lines.append("=" * 60)
        lines.append("FINGERPRINT CONFIGURATION")
        lines.append("=" * 60)
        lines.append("")

        if "os" in fp_data:
            lines.append(f"OS: {fp_data['os'].upper()}")
            lines.append("")

        if "webgl" in fp_data:
            lines.append("WebGL")
            lines.append("-" * 40)
            lines.append(f"  Vendor:   {fp_data['webgl'].get('vendor', 'N/A')}")
            lines.append(f"  Renderer: {fp_data['webgl'].get('renderer', 'N/A')}")
            lines.append("")

        if "canvas" in fp_data:
            lines.append("Canvas")
            lines.append("-" * 40)
            lines.append(f"  AA Offset: {fp_data['canvas'].get('aaOffset', 'N/A')}")
            lines.append("")

        if "fonts" in fp_data:
            lines.append("Fonts")
            lines.append("-" * 40)
            lines.append(
                f"  Spacing Seed: {fp_data['fonts'].get('spacing_seed', 'N/A')}"
            )
            lines.append("")

        if "history_length" in fp_data:
            lines.append("History Length: " + str(fp_data["history_length"]))
            lines.append("")

        if "fingerprint" in fp_data:
            fp = fp_data["fingerprint"]

            lines.append("Navigator")
            lines.append("-" * 40)
            for key in sorted([k for k in fp.keys() if k.startswith("navigator.")]):
                value = fp[key]
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                lines.append(f"  {key.replace('navigator.', '')}: {value}")
            lines.append("")

            lines.append("Screen")
            lines.append("-" * 40)
            for key in sorted([k for k in fp.keys() if k.startswith("screen.")]):
                lines.append(f"  {key.replace('screen.', '')}: {fp[key]}")
            lines.append("")

            lines.append("Window")
            lines.append("-" * 40)
            for key in sorted([k for k in fp.keys() if k.startswith("window.")]):
                lines.append(f"  {key.replace('window.', '')}: {fp[key]}")
            lines.append("")

        return lines

    def _load_cookies(self):
        """Load cookies from SQLite database."""
        import sqlite3
        from datetime import datetime

        cookies_db = self._get_profile_dir() / "cookies.sqlite"
        self.cookies_table.setRowCount(0)

        if not cookies_db.exists():
            self.cookies_table.setRowCount(1)
            self.cookies_table.setItem(0, 0, QTableWidgetItem("No cookies found"))
            return

        try:
            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT host, name, value, expiry, isSecure 
                FROM moz_cookies 
                ORDER BY host, name
                LIMIT 500
            """
            )
            rows = cursor.fetchall()
            conn.close()

            self.cookies_table.setRowCount(len(rows))
            for i, (host, name, value, expiry, secure) in enumerate(rows):
                self.cookies_table.setItem(i, 0, QTableWidgetItem(host))
                self.cookies_table.setItem(i, 1, QTableWidgetItem(name))
                # Truncate long values
                val_display = value[:50] + "..." if len(value) > 50 else value
                self.cookies_table.setItem(i, 2, QTableWidgetItem(val_display))
                # Format expiry
                if expiry:
                    try:
                        exp_date = datetime.fromtimestamp(expiry).strftime(
                            "%Y-%m-%d %H:%M"
                        )
                    except:
                        exp_date = str(expiry)
                else:
                    exp_date = "Session"
                self.cookies_table.setItem(i, 3, QTableWidgetItem(exp_date))
                self.cookies_table.setItem(
                    i, 4, QTableWidgetItem("Yes" if secure else "No")
                )

        except Exception as e:
            self.cookies_table.setRowCount(1)
            self.cookies_table.setItem(0, 0, QTableWidgetItem(f"Error: {e}"))

    def _load_storage(self):
        """Load localStorage info."""
        import os

        storage_dir = self._get_profile_dir() / "storage" / "default"
        lines = []
        lines.append("=" * 50)
        lines.append("LOCAL STORAGE & INDEXEDDB")
        lines.append("=" * 50)
        lines.append("")

        if not storage_dir.exists():
            lines.append("No storage data found.")
            self.storage_display.setPlainText("\n".join(lines))
            return

        try:
            total_size = 0
            sites = []

            for site_dir in storage_dir.iterdir():
                if site_dir.is_dir():
                    site_name = site_dir.name
                    # Calculate size
                    size = sum(
                        f.stat().st_size for f in site_dir.rglob("*") if f.is_file()
                    )
                    total_size += size

                    # Check for localStorage and IndexedDB
                    has_ls = (site_dir / "ls").exists()
                    has_idb = (site_dir / "idb").exists()

                    sites.append(
                        {
                            "name": site_name,
                            "size": size,
                            "localStorage": has_ls,
                            "indexedDB": has_idb,
                        }
                    )

            sites.sort(key=lambda x: x["size"], reverse=True)

            lines.append(f"Total sites: {len(sites)}")
            lines.append(f"Total size: {total_size / 1024:.1f} KB")
            lines.append("")
            lines.append("-" * 50)

            for site in sites[:50]:
                size_kb = site["size"] / 1024
                flags = []
                if site["localStorage"]:
                    flags.append("localStorage")
                if site["indexedDB"]:
                    flags.append("indexedDB")
                lines.append(f"{site['name']}")
                lines.append(
                    f"  Size: {size_kb:.1f} KB | {', '.join(flags) if flags else 'empty'}"
                )
                lines.append("")

        except Exception as e:
            lines.append(f"Error reading storage: {e}")

        self.storage_display.setPlainText("\n".join(lines))

    def _load_history(self):
        """Load browsing history."""
        import sqlite3

        places_db = self._get_profile_dir() / "places.sqlite"
        self.history_table.setRowCount(0)

        if not places_db.exists():
            self.history_table.setRowCount(1)
            self.history_table.setItem(0, 0, QTableWidgetItem("No history found"))
            return

        try:
            conn = sqlite3.connect(str(places_db))
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT url, title, visit_count 
                FROM moz_places 
                WHERE visit_count > 0
                ORDER BY visit_count DESC
                LIMIT 200
            """
            )
            rows = cursor.fetchall()
            conn.close()

            self.history_table.setRowCount(len(rows))
            for i, (url, title, count) in enumerate(rows):
                self.history_table.setItem(
                    i, 0, QTableWidgetItem(url[:80] if url else "")
                )
                self.history_table.setItem(i, 1, QTableWidgetItem(title or ""))
                self.history_table.setItem(i, 2, QTableWidgetItem(str(count)))

        except Exception as e:
            self.history_table.setRowCount(1)
            self.history_table.setItem(0, 0, QTableWidgetItem(f"Error: {e}"))

    def _load_cache(self):
        """Load cache info."""
        import os

        cache_dir = self._get_profile_dir() / "cache2"
        lines = []
        lines.append("=" * 50)
        lines.append("BROWSER CACHE")
        lines.append("=" * 50)
        lines.append("")

        if not cache_dir.exists():
            lines.append("No cache found.")
            self.cache_display.setPlainText("\n".join(lines))
            return

        try:
            total_files = 0
            total_size = 0

            for f in cache_dir.rglob("*"):
                if f.is_file():
                    total_files += 1
                    total_size += f.stat().st_size

            lines.append(f"Cache directory: {cache_dir}")
            lines.append("")
            lines.append(f"Total files: {total_files}")
            lines.append(f"Total size: {total_size / (1024*1024):.2f} MB")

        except Exception as e:
            lines.append(f"Error reading cache: {e}")

        self.cache_display.setPlainText("\n".join(lines))

    def _load_permissions(self):
        """Load site permissions."""
        import sqlite3

        perms_db = self._get_profile_dir() / "permissions.sqlite"
        self.permissions_table.setRowCount(0)

        if not perms_db.exists():
            self.permissions_table.setRowCount(1)
            self.permissions_table.setItem(
                0, 0, QTableWidgetItem("No permissions found")
            )
            return

        try:
            conn = sqlite3.connect(str(perms_db))
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT origin, type, permission 
                FROM moz_perms 
                ORDER BY origin, type
            """
            )
            rows = cursor.fetchall()
            conn.close()

            # Permission values: 1=allow, 2=deny
            perm_map = {1: "Allow", 2: "Deny", 0: "Default"}

            self.permissions_table.setRowCount(len(rows))
            for i, (origin, ptype, perm) in enumerate(rows):
                self.permissions_table.setItem(i, 0, QTableWidgetItem(origin))
                self.permissions_table.setItem(i, 1, QTableWidgetItem(ptype))
                self.permissions_table.setItem(
                    i, 2, QTableWidgetItem(perm_map.get(perm, str(perm)))
                )

        except Exception as e:
            self.permissions_table.setRowCount(1)
            self.permissions_table.setItem(0, 0, QTableWidgetItem(f"Error: {e}"))

    def _copy_text(self, text_widget):
        """Copy text widget content to clipboard."""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(text_widget.toPlainText())
        info_dialog(self, "Copied", "Content copied to clipboard!")

    def _export_cookies(self):
        """Export cookies to JSON file."""
        import sqlite3
        import json
        from PyQt6.QtWidgets import QFileDialog

        cookies_db = self._get_profile_dir() / "cookies.sqlite"
        if not cookies_db.exists():
            self._alert.show_error("No Cookies", "No cookies to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Cookies",
            f"{self.profile.name}_cookies.json",
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        try:
            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT host, name, value, path, expiry, isSecure, isHttpOnly FROM moz_cookies"
            )
            rows = cursor.fetchall()
            conn.close()

            cookies = []
            for host, name, value, path, expiry, secure, httponly in rows:
                cookies.append(
                    {
                        "domain": host,
                        "name": name,
                        "value": value,
                        "path": path or "/",
                        "expires": expiry,
                        "secure": bool(secure),
                        "httpOnly": bool(httponly),
                    }
                )

            with open(file_path, "w") as f:
                json.dump(cookies, f, indent=2)

            info_dialog(
                self, "Exported", f"Exported {len(cookies)} cookies to {file_path}"
            )

        except Exception as e:
            error_dialog(self, "Error", f"Export failed: {e}")

    def _import_cookies(self):
        """Import cookies from JSON file."""
        import sqlite3
        import json
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Cookies", "", "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        cookies_db = self._get_profile_dir() / "cookies.sqlite"

        try:
            with open(file_path, "r") as f:
                cookies = json.load(f)

            if not isinstance(cookies, list):
                raise ValueError("Invalid cookies format")

            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()

            imported = 0
            for cookie in cookies:
                try:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO moz_cookies 
                        (host, name, value, path, expiry, isSecure, isHttpOnly, sameSite, rawSameSite, schemeMap)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)
                    """,
                        (
                            cookie.get("domain", ""),
                            cookie.get("name", ""),
                            cookie.get("value", ""),
                            cookie.get("path", "/"),
                            cookie.get("expires") or cookie.get("expiry", 0),
                            1 if cookie.get("secure") else 0,
                            1 if cookie.get("httpOnly") else 0,
                        ),
                    )
                    imported += 1
                except Exception:
                    pass

            conn.commit()
            conn.close()

            info_dialog(self, "Imported", f"Imported {imported} cookies")
            self._load_cookies()

        except Exception as e:
            error_dialog(self, "Error", f"Import failed: {e}")

    def _clear_cookies(self):
        """Clear all cookies."""
        if not confirm_dialog(
            self,
            "Clear Cookies",
            "This will delete ALL cookies for this profile.\n\nYou will be logged out of all sites.\n\nContinue?",
        ):
            return

        cookies_db = self._get_profile_dir() / "cookies.sqlite"
        if cookies_db.exists():
            try:
                import sqlite3

                conn = sqlite3.connect(str(cookies_db))
                conn.execute("DELETE FROM moz_cookies")
                conn.commit()
                conn.close()
                info_dialog(self, "Cleared", "All cookies deleted.")
                self._load_cookies()
            except Exception as e:
                error_dialog(self, "Error", f"Failed to clear cookies: {e}")

    def _clear_storage(self):
        """Clear localStorage and IndexedDB."""
        import shutil

        if not confirm_dialog(
            self,
            "Clear Storage",
            "This will delete ALL localStorage and IndexedDB data.\n\nContinue?",
        ):
            return

        storage_dir = self._get_profile_dir() / "storage"
        if storage_dir.exists():
            try:
                shutil.rmtree(storage_dir)
                info_dialog(self, "Cleared", "Storage data deleted.")
                self._load_storage()
            except Exception as e:
                error_dialog(self, "Error", f"Failed to clear storage: {e}")

    def _clear_history(self):
        """Clear browsing history."""
        import sqlite3

        if not confirm_dialog(
            self,
            "Clear History",
            "This will delete browsing history.\n\nContinue?",
        ):
            return

        places_db = self._get_profile_dir() / "places.sqlite"
        if places_db.exists():
            try:
                conn = sqlite3.connect(str(places_db))
                conn.execute("DELETE FROM moz_historyvisits")
                conn.execute("UPDATE moz_places SET visit_count = 0")
                conn.commit()
                conn.close()
                info_dialog(self, "Cleared", "History cleared.")
                self._load_history()
            except Exception as e:
                error_dialog(self, "Error", f"Failed to clear history: {e}")

    def _clear_cache(self):
        """Clear browser cache."""
        import shutil

        if not confirm_dialog(
            self,
            "Clear Cache",
            "This will delete all cached files.\n\nContinue?",
        ):
            return

        cache_dir = self._get_profile_dir() / "cache2"
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                info_dialog(self, "Cleared", "Cache deleted.")
                self._load_cache()
            except Exception as e:
                error_dialog(self, "Error", f"Failed to clear cache: {e}")

    def _clear_permissions(self):
        """Clear site permissions."""
        import sqlite3

        if not confirm_dialog(
            self,
            "Clear Permissions",
            "This will reset all site permissions.\n\nContinue?",
        ):
            return

        perms_db = self._get_profile_dir() / "permissions.sqlite"
        if perms_db.exists():
            try:
                conn = sqlite3.connect(str(perms_db))
                conn.execute("DELETE FROM moz_perms")
                conn.commit()
                conn.close()
                info_dialog(self, "Cleared", "Permissions cleared.")
                self._load_permissions()
            except Exception as e:
                error_dialog(self, "Error", f"Failed to clear permissions: {e}")

    def _clear_all_data(self):
        """Clear all browser data for this profile."""
        import shutil

        if not confirm_dialog(
            self,
            "Clear All Profile Data",
            "This will delete ALL stored data for this profile:\n\n"
            "- Cookies\n"
            "- Local storage\n"
            "- Browsing history\n"
            "- Cache\n"
            "- Permissions\n\n"
            "The profile will be reset to default state.\n\n"
            "Continue?",
        ):
            return


        profile_dir = self._get_profile_dir()
        if profile_dir.exists():
            try:
                shutil.rmtree(profile_dir)
                profile_dir.mkdir(parents=True)
                info_dialog(self, "Cleared", "All profile data deleted.")
                self._refresh_all()
            except Exception as e:
                error_dialog(self, "Error", f"Failed to clear data: {e}")

    def _regenerate_fingerprint(self):
        """Delete fingerprint file so it regenerates on next launch."""
        if not confirm_dialog(
            self,
            "Regenerate Fingerprint",
            "Warning: Regenerating fingerprint while keeping cookies and storage "
            "may cause detection on sites you've previously visited.\n\n"
            "The site will see a new device with an existing session.\n\n"
            "Recommended: Clear browser data before regenerating fingerprint.\n\n"
            "Continue?",
        ):
            return

        fingerprint_file = self._get_profile_dir() / "fingerprint.json"
        if fingerprint_file.exists():
            fingerprint_file.unlink()
            self._load_fingerprint()
            info_dialog(
                self,
                "Fingerprint Deleted",
                "Fingerprint deleted. A new one will be generated on next profile launch.",
            )
