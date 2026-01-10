"""Dialogs for profile, folder, proxy and tag editing."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QTextEdit,
    QPushButton,
    QLabel,
    QGroupBox,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt

from .models import BrowserProfile, Folder, ProxyConfig, ProxyType
from .styles import COLORS
from .proxy_utils import parse_proxy_string


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
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        self.setWindowTitle("New Profile" if self.is_new else "Edit Profile")
        self.setMinimumWidth(450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Name
        name_group = QGroupBox("Profile")
        name_layout = QFormLayout(name_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter profile name...")
        name_layout.addRow("Name:", self.name_input)

        self.os_combo = QComboBox()
        self.os_combo.addItems(["macOS", "Windows", "Linux"])
        name_layout.addRow("OS:", self.os_combo)

        layout.addWidget(name_group)

        # Proxy
        proxy_group = QGroupBox("Proxy (Optional)")
        proxy_layout = QVBoxLayout(proxy_group)

        # Quick paste
        paste_layout = QHBoxLayout()
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText(
            "host:port or host:port:user:pass or socks5://..."
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
        else:
            QMessageBox.warning(self, "Parse Error", "Could not parse proxy string")

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
            QMessageBox.information(
                self,
                "Empty Pool",
                "Proxy pool is empty. Add proxies in the Proxy page first.",
            )
            return

        # Create selection dialog
        items = []
        for proxy in proxy_pool.proxies:
            auth = f" (auth: {proxy.username})" if proxy.username else ""
            items.append(
                f"{proxy.proxy_type.value.upper()}://{proxy.host}:{proxy.port}{auth}"
            )

        item, ok = QInputDialog.getItem(
            self, "Select Proxy from Pool", "Choose proxy:", items, 0, False
        )

        if ok and item:
            # Get index and set proxy
            idx = items.index(item)
            self.profile.proxy = proxy_pool.proxies[idx]
            self._update_proxy_info()

    def _clear_proxy(self):
        self.profile.proxy = ProxyConfig()
        self._update_proxy_info()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Profile name is required")
            return

        self.profile.name = name

        os_map = {0: "macos", 1: "windows", 2: "linux"}
        self.profile.os_type = os_map.get(self.os_combo.currentIndex(), "macos")

        self.accept()

    def get_profile(self) -> BrowserProfile:
        return self.profile


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
        self.name_input.setPlaceholderText("Profile name...")
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

        # Name
        layout.addWidget(QLabel("Folder Name:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter folder name...")
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
            QMessageBox.warning(self, "Error", "Folder name is required")
            return

        self.folder.name = name
        self.folder.color = self.color_combo.currentData()
        self.accept()

    def get_folder(self) -> Folder:
        return self.folder


class TagsEditDialog(QDialog):
    """Dialog for editing profile tags."""

    def __init__(self, current_tags: list[str], all_tags: list[str], parent=None):
        super().__init__(parent)
        self.current_tags = list(current_tags)
        self.all_tags = all_tags
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Tags")
        self.setMinimumSize(400, 350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Current tags
        layout.addWidget(QLabel("Current tags:"))
        self.tags_list = QListWidget()
        self.tags_list.itemClicked.connect(self._remove_tag)
        self._refresh_tags_list()
        layout.addWidget(self.tags_list)

        # Add new tag
        add_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("New tag...")
        self.new_tag_input.returnPressed.connect(self._add_tag)
        add_layout.addWidget(self.new_tag_input)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_tag)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

        # Existing tags
        if self.all_tags:
            layout.addWidget(QLabel("Available tags:"))
            avail_layout = QHBoxLayout()
            for tag in self.all_tags[:8]:
                if tag not in self.current_tags:
                    btn = QPushButton(tag)
                    btn.setStyleSheet(
                        f"""
                        background-color: {COLORS['tag_bg']};
                        color: {COLORS['tag_text']};
                        border: none;
                        padding: 4px 8px;
                        font-size: 11px;
                    """
                    )
                    btn.clicked.connect(lambda _, t=tag: self._add_existing_tag(t))
                    avail_layout.addWidget(btn)
            avail_layout.addStretch()
            layout.addLayout(avail_layout)

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
            item = QListWidgetItem(f"[x] {tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.tags_list.addItem(item)

    def _add_tag(self):
        tag = self.new_tag_input.text().strip()
        if tag and tag not in self.current_tags:
            self.current_tags.append(tag)
            self._refresh_tags_list()
            self.new_tag_input.clear()

    def _add_existing_tag(self, tag: str):
        if tag not in self.current_tags:
            self.current_tags.append(tag)
            self._refresh_tags_list()

    def _remove_tag(self, item: QListWidgetItem):
        tag = item.data(Qt.ItemDataRole.UserRole)
        if tag in self.current_tags:
            self.current_tags.remove(tag)
            self._refresh_tags_list()

    def get_tags(self) -> list[str]:
        return self.current_tags


class NotesEditDialog(QDialog):
    """Dialog for editing profile notes."""

    def __init__(self, notes: str, parent=None):
        super().__init__(parent)
        self.notes = notes
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Notes")
        self.setMinimumSize(450, 300)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Add notes about this profile...")
        self.notes_edit.setText(self.notes)
        layout.addWidget(self.notes_edit)

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
                text += f" (auth)"
            item = QListWidgetItem(text)
            self.proxy_list.addItem(item)

    def _add_proxies(self):
        from .proxy_utils import parse_proxy_list

        text = self.proxy_input.toPlainText()
        new_proxies = parse_proxy_list(text)
        self.proxies.extend(new_proxies)
        self._refresh_list()
        self.proxy_input.clear()

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
