"""Custom widgets for Dolphin-style UI."""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
    QMenu,
    QLineEdit,
    QDialog,
    QFormLayout,
    QComboBox,
    QTextEdit,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction

from .models import BrowserProfile, ProfileStatus, Folder, ProxyConfig
from .styles import COLORS, OS_ICONS
from .icons import get_icon


class EmptyPlaceholder(QWidget):
    """Placeholder widget for empty table."""

    create_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon = QLabel("[browser]")
        icon.setStyleSheet(f"font-size: 64px; color: {COLORS['accent']};")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        # Title
        title = QLabel("No profiles yet")
        title.setStyleSheet(
            f"""
            color: {COLORS['text_primary']};
            font-size: 20px;
            font-weight: 600;
        """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Create browser profile to begin")
        subtitle.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Create button
        create_btn = QPushButton("+ Create Profile")
        create_btn.setStyleSheet(
            f"""
            background-color: {COLORS['accent']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
        """
        )
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self.create_clicked.emit)
        create_btn.setFixedWidth(180)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(create_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class StatusBadge(QWidget):
    """Status badge widget."""

    def __init__(self, status: ProfileStatus, parent=None):
        super().__init__(parent)
        self.status = status
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text = self.status.value.upper()

        # Colors with subtle background
        style_map = {
            ProfileStatus.RUNNING: {
                "bg": "rgba(34, 197, 94, 0.15)",
                "border": COLORS["success"],
                "text": COLORS["success"],
            },
            ProfileStatus.STOPPED: {
                "bg": "rgba(128, 128, 128, 0.1)",
                "border": COLORS["text_muted"],
                "text": COLORS["text_muted"],
            },
            ProfileStatus.ERROR: {
                "bg": "rgba(239, 68, 68, 0.15)",
                "border": COLORS["error"],
                "text": COLORS["error"],
            },
        }
        style = style_map.get(
            self.status,
            {
                "bg": "transparent",
                "border": COLORS["text_muted"],
                "text": COLORS["text_muted"],
            },
        )

        label = QLabel(text)
        label.setMinimumHeight(22)
        label.setMaximumHeight(22)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"""
            background-color: {style['bg']};
            color: {style['text']};
            border: 1px solid {style['border']};
            border-radius: 4px;
            padding: 0 10px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
        """
        )
        layout.addWidget(label)


class TagWidget(QWidget):
    """Single tag widget."""

    clicked = pyqtSignal(str)

    def __init__(self, tag: str, parent=None):
        super().__init__(parent)
        self.tag = tag

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


        label = QLabel(tag)
        label.setMinimumHeight(20)
        label.setMaximumHeight(20)
        label.setStyleSheet(
            f"""
            background-color: transparent;
            color: white;
            border: 1px solid {COLORS['tag_bg']};
            border-radius: 4px;
            padding: 0 8px;
            font-size: 11px;
        """
        )
        label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(label)

    def mousePressEvent(self, event):
        self.clicked.emit(self.tag)


class TagsWidget(QWidget):
    """Widget for displaying multiple tags."""

    tag_clicked = pyqtSignal(str)
    edit_requested = pyqtSignal()

    def __init__(self, tags: list[str], parent=None):
        super().__init__(parent)
        self.tags = tags
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        for tag in self.tags[:3]:  # Max 3 visible
            tw = TagWidget(tag)
            tw.clicked.connect(self.tag_clicked.emit)
            layout.addWidget(tw)

        if len(self.tags) > 3:
            more = QLabel(f"+{len(self.tags) - 3}")
            more.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
            layout.addWidget(more)

        layout.addStretch()

        # Edit button with SVG icon
        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", 14))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(24, 24)
        edit_btn.setProperty("class", "icon")
        edit_btn.setToolTip("Edit tags")
        edit_btn.clicked.connect(self.edit_requested.emit)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(edit_btn)
        layout.addSpacing(6)

    def set_tags(self, tags: list[str]):
        self.tags = tags
        # Clear and rebuild
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._setup_ui()


class NotesWidget(QWidget):
    """Widget for displaying and editing notes."""

    edit_requested = pyqtSignal()

    def __init__(self, notes: str, parent=None):
        super().__init__(parent)
        self.notes = notes
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Preview
        preview = self.notes[:30] + "..." if len(self.notes) > 30 else self.notes
        if not preview:
            preview = "—"

        label = QLabel(preview)
        label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(label)

        layout.addStretch()

        # Edit button with SVG icon
        edit_btn = QPushButton()

        edit_btn.setIcon(get_icon("edit", 14))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(24, 24)
        edit_btn.setProperty("class", "icon")
        edit_btn.setToolTip("Edit notes")
        edit_btn.clicked.connect(self.edit_requested.emit)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(edit_btn)
        layout.addSpacing(6)


class ProxyWidget(QWidget):
    """Widget for displaying proxy with country flag."""

    def __init__(self, proxy: ProxyConfig, parent=None):
        super().__init__(parent)
        self.proxy = proxy
        self._setup_ui()

    def _get_flag_emoji(self, country_code: str) -> str:
        """Convert country code to flag emoji."""
        if not country_code or len(country_code) != 2:
            return "🌐"
        # Convert country code to regional indicator symbols
        return "".join(chr(127397 + ord(c)) for c in country_code.upper())

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Country flag emoji
        if self.proxy and self.proxy.country_code:
            flag = self._get_flag_emoji(self.proxy.country_code)
            flag_label = QLabel(flag)
            flag_label.setStyleSheet("font-size: 16px;")
            layout.addWidget(flag_label)
        else:
            # Proxy icon when no country code
            icon_btn = QPushButton()
            icon_btn.setEnabled(False)
            icon_btn.setIcon(get_icon("proxy", 14))
            icon_btn.setIconSize(QSize(14, 14))
            icon_btn.setFixedSize(18, 18)
            icon_btn.setStyleSheet(
                "QPushButton { background: transparent; border: none; padding: 0px; }"
            )
            layout.addWidget(icon_btn)

        # IP/Host
        ip_text = self.proxy.display_string() if self.proxy else "Direct"
        ip_label = QLabel(ip_text)
        ip_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
        layout.addWidget(ip_label)

        # Ping indicator
        if self.proxy and self.proxy.ping_ms > 0:
            ping_color = (
                COLORS["success"]
                if self.proxy.ping_ms < 200
                else (
                    COLORS["warning"] if self.proxy.ping_ms < 500 else COLORS["error"]
                )
            )
            ping_label = QLabel(f"{self.proxy.ping_ms}ms")
            ping_label.setStyleSheet(f"color: {ping_color}; font-size: 11px;")
            layout.addWidget(ping_label)

        layout.addStretch()


class ProfileNameWidget(QWidget):
    """Widget for profile name with OS icon and start/stop button."""

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, profile: BrowserProfile, parent=None):
        super().__init__(parent)
        self.profile = profile
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # OS icon - use SVG
        os_type = self.profile.os_type
        if os_type == "windows":
            icon_name = "windows"
        elif os_type == "macos":
            icon_name = "apple"
        else:
            icon_name = "linux"

        icon_btn = QPushButton()
        icon_btn.setIcon(get_icon(icon_name, 16))
        icon_btn.setIconSize(QSize(16, 16))
        icon_btn.setFixedSize(20, 20)
        icon_btn.setStyleSheet("background: transparent; border: none;")
        icon_btn.setEnabled(False)
        layout.addWidget(icon_btn)

        # Name
        name_label = QLabel(self.profile.name)
        name_label.setStyleSheet(
            f"""
            color: {COLORS['text_primary']};
            font-size: 13px;
            font-weight: 500;
        """
        )
        layout.addWidget(name_label)

        layout.addStretch()

        # Start/Stop button with icon
        btn = QPushButton()
        btn.setFixedSize(72, 24)

        if self.profile.status == ProfileStatus.RUNNING:
            btn.setIcon(get_icon("stop", 14))
            btn.setIconSize(QSize(14, 14))
            btn.setText("STOP")
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(239, 68, 68, 0.1);
                    color: {COLORS['error']};
                    border: 1px solid {COLORS['error']};
                    border-radius: 4px;
                    padding: 0 10px 0 6px;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background-color: rgba(239, 68, 68, 0.25);
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['error']};
                    color: white;
                }}
            """
            )
            btn.setToolTip("Stop browser")
            btn.clicked.connect(self.stop_requested.emit)
        else:
            btn.setIcon(get_icon("play", 14))
            btn.setIconSize(QSize(14, 14))
            btn.setText("START")
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: rgba(34, 197, 94, 0.1);
                    color: {COLORS['success']};
                    border: 1px solid {COLORS['success']};
                    border-radius: 4px;
                    padding: 0 10px 0 6px;
                    font-size: 10px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }}
                QPushButton:hover {{
                    background-color: rgba(34, 197, 94, 0.25);
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['success']};
                    color: white;
                }}
            """
            )
            btn.setToolTip("Start browser")
            btn.clicked.connect(self.start_requested.emit)

        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn)
        layout.addSpacing(6)


class FolderItem(QFrame):
    """Folder item in sidebar."""

    clicked = pyqtSignal(str)  # folder_id
    context_menu_requested = pyqtSignal(str, object)  # folder_id, QPoint

    def __init__(self, folder: Folder, count: int, selected: bool = False, parent=None):
        super().__init__(parent)
        self.folder = folder
        self.count = count
        self.selected = selected
        self._setup_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self):
        bg = "rgba(128, 128, 128, 0.15)" if self.selected else "transparent"
        border = (
            f"1px solid {self.folder.color}"
            if not self.selected
            else f"1px solid {COLORS['accent']}"
        )
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
                margin: 1px 8px;
            }}
            QFrame:hover {{
                background-color: {COLORS['bg_hover'] if not self.selected else 'rgba(128, 128, 128, 0.15)'};
                border: 1px solid {self.folder.color};
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Folder icon with color
        folder_btn = QPushButton()
        folder_btn.setIcon(get_icon("folder", 14, self.folder.color))
        folder_btn.setIconSize(QSize(14, 14))
        folder_btn.setFixedSize(16, 16)
        folder_btn.setStyleSheet("background: transparent; border: none;")
        folder_btn.setEnabled(False)
        layout.addWidget(folder_btn)

        # Name
        name_label = QLabel(self.folder.name)
        name_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 12px; background: transparent; border: none;"
        )
        layout.addWidget(name_label, 1)

        # Count
        count_label = QLabel(str(self.count))
        count_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent; border: none;"
        )
        layout.addWidget(count_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.folder.id)
        elif event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(
                self.folder.id, event.globalPosition().toPoint()
            )


class AllProfilesItem(QFrame):
    """'All Profiles' item in sidebar."""

    clicked = pyqtSignal()

    def __init__(self, count: int, selected: bool = False, parent=None):
        super().__init__(parent)
        self.count = count
        self.selected = selected
        self.count_label = None
        self._setup_ui()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_ui(self):
        bg = "rgba(128, 128, 128, 0.15)" if self.selected else "transparent"
        border = (
            f"1px solid {COLORS['accent']}"
            if self.selected
            else "1px solid transparent"
        )
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
                margin: 2px 8px;
            }}
            QFrame:hover {{
                background-color: {COLORS['bg_hover'] if not self.selected else 'rgba(128, 128, 128, 0.15)'};
                border: 1px solid {COLORS['text_muted']};
            }}
        """
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Name - выровнено влево как FOLDERS
        name_label = QLabel("All Profiles")
        name_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 12px; font-weight: 500; background: transparent; border: none;"
        )
        layout.addWidget(name_label, 1)  # stretch factor 1

        # Count
        self.count_label = QLabel(str(self.count))
        self.count_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; background: transparent; border: none;"
        )
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.count_label)

    def update_count(self, count: int):
        """Update profile count."""
        self.count = count
        if self.count_label:
            self.count_label.setText(str(count))

    def update_selected(self, selected: bool):
        """Update selected state."""
        self.selected = selected
        bg = "rgba(128, 128, 128, 0.15)" if self.selected else "transparent"
        border = (
            f"1px solid {COLORS['accent']}"
            if self.selected
            else "1px solid transparent"
        )
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
                margin: 2px 8px;
            }}
            QFrame:hover {{
                background-color: {COLORS['bg_hover'] if not self.selected else 'rgba(128, 128, 128, 0.15)'};
                border: 1px solid {COLORS['text_muted']};
            }}
        """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class TagFilterWidget(QWidget):
    """Widget for tag filter buttons in footer."""

    tag_selected = pyqtSignal(str)  # Empty string = no filter

    def __init__(self, tags: list[str], selected: str = "", parent=None):
        super().__init__(parent)
        self.tags = tags
        self.selected = selected
        self._setup_ui()

    def _setup_ui(self):
        # Get or create layout
        if self.layout() is None:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)
        else:
            layout = self.layout()

        # All tags button (reset filter)
        all_btn = QPushButton("All")
        all_btn.setCheckable(True)
        all_btn.setChecked(self.selected == "")
        all_btn.setStyleSheet(self._get_button_style(self.selected == ""))
        all_btn.clicked.connect(lambda: self._on_tag_clicked(""))
        all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(all_btn)

        # Tag buttons
        for tag in self.tags[:10]:  # Max 10 tags
            btn = QPushButton(tag)
            btn.setCheckable(True)
            btn.setChecked(self.selected == tag)
            btn.setStyleSheet(self._get_button_style(self.selected == tag))
            btn.clicked.connect(lambda checked, t=tag: self._on_tag_clicked(t))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(btn)

        layout.addStretch()

    def _on_tag_clicked(self, tag: str):
        """Handle tag button click."""
        self.selected = tag
        self.tag_selected.emit(tag)
        # Rebuild UI to update button styles
        self.update_tags(self.tags, self.selected)

    def update_tags(self, tags: list[str], selected: str = ""):
        """Update tags and rebuild widget."""
        self.tags = tags
        self.selected = selected
        # Clear layout
        while self.layout().count():
            item = self.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._setup_ui()

    def _get_button_style(self, selected: bool) -> str:
        if selected:
            return f"""
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 12px;
            """
        return f"""
            background-color: {COLORS['bg_tertiary']};
            color: {COLORS['text_secondary']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 12px;
        """


class PaginationWidget(QWidget):
    """Pagination controls."""

    page_changed = pyqtSignal(int)
    per_page_changed = pyqtSignal(int)

    def __init__(self, total: int, page: int, per_page: int, parent=None):
        super().__init__(parent)
        self.total = total
        self.page = page
        self.per_page = per_page
        self.info_label = None
        self.page_label = None
        self.prev_btn = None
        self.next_btn = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Items per page label
        per_page_label = QLabel("Per page:")
        per_page_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )
        layout.addWidget(per_page_label)

        # Items per page combo
        per_page_combo = QComboBox()
        per_page_combo.addItems(["10", "25", "50", "100"])
        per_page_combo.setCurrentText(str(self.per_page))
        per_page_combo.setFixedWidth(60)
        per_page_combo.currentTextChanged.connect(
            lambda t: self.per_page_changed.emit(int(t)) if t.isdigit() else None
        )
        layout.addWidget(per_page_combo)

        # Spacer
        layout.addSpacing(16)

        # Page info
        total_pages = max(1, (self.total + self.per_page - 1) // self.per_page)
        start = (self.page - 1) * self.per_page + 1 if self.total > 0 else 0
        end = min(self.page * self.per_page, self.total)

        self.info_label = QLabel(f"{start}-{end} of {self.total}")
        self.info_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 12px;"
        )
        layout.addWidget(self.info_label)

        # Spacer
        layout.addSpacing(8)

        # Navigation prev with SVG icon
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(get_icon("chevron_left", 14))
        self.prev_btn.setIconSize(QSize(14, 14))
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['border']};
            }}
            QPushButton:disabled {{
                background: transparent;
            }}
        """
        )
        self.prev_btn.setEnabled(self.page > 1)
        self.prev_btn.clicked.connect(lambda: self.page_changed.emit(self.page - 1))
        layout.addWidget(self.prev_btn)

        # Page indicator
        self.page_label = QLabel(f"{self.page}/{total_pages}")
        self.page_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 12px;"
        )
        self.page_label.setMinimumWidth(45)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.page_label)

        # Navigation next with SVG icon
        self.next_btn = QPushButton()
        self.next_btn.setIcon(get_icon("chevron_right", 14))
        self.next_btn.setIconSize(QSize(14, 14))
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['bg_tertiary']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {COLORS['border']};
            }}
            QPushButton:disabled {{
                background: transparent;
            }}
        """
        )
        self.next_btn.setEnabled(self.page < total_pages)
        self.next_btn.clicked.connect(lambda: self.page_changed.emit(self.page + 1))
        layout.addWidget(self.next_btn)

    def update_data(self, total: int, page: int, per_page: int):
        """Update pagination state."""
        self.total = total
        self.page = page
        self.per_page = per_page

        total_pages = max(1, (self.total + self.per_page - 1) // self.per_page)
        start = (self.page - 1) * self.per_page + 1 if self.total > 0 else 0
        end = min(self.page * self.per_page, self.total)

        if self.info_label:
            self.info_label.setText(f"{start}-{end} of {self.total}")
        if self.page_label:
            self.page_label.setText(f"{self.page}/{total_pages}")
        if self.prev_btn:
            self.prev_btn.setEnabled(self.page > 1)
        if self.next_btn:
            self.next_btn.setEnabled(self.page < total_pages)
