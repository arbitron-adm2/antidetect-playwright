"""Mini sidebar with icon navigation."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from ..theme import Theme, COLORS, SPACING
from ..icons import get_icon


class MiniSidebar(QWidget):
    """Mini sidebar with icon navigation."""

    page_changed = pyqtSignal(int)
    settings_clicked = pyqtSignal()

    NAV_ITEMS = [
        ("user", "Profiles", 0),
        ("proxy", "Proxy", 1),
        ("tag", "Tags & Notes", 2),
        ("trash", "Trash", 3),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nav_buttons: list[QPushButton] = []
        self._setup_ui()

    def _setup_ui(self):
        """Setup sidebar UI."""
        self.setObjectName("miniSidebar")
        self.setFixedWidth(56)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, SPACING.sm, 0, SPACING.sm)
        layout.setSpacing(SPACING.xs)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Navigation buttons
        for icon_name, tooltip, page_index in self.NAV_ITEMS:
            btn = self._create_nav_button(icon_name, tooltip, page_index)
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Set first button as active
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        layout.addStretch()

        # Settings button at bottom
        settings_btn = self._create_settings_button()
        layout.addWidget(settings_btn)

    def _create_nav_button(
        self, icon_name: str, tooltip: str, page_index: int
    ) -> QPushButton:
        """Create navigation button."""
        btn = QPushButton()
        btn.setIcon(get_icon(icon_name, 20))
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip(tooltip)
        btn.setFixedSize(48, 48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setProperty("page_index", page_index)
        btn.clicked.connect(lambda checked, idx=page_index: self._on_nav_click(idx))
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                margin: {SPACING.xs}px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
            }}
            QPushButton:checked {{
                background: {COLORS.accent};
            }}
        """
        )
        return btn

    def _create_settings_button(self) -> QPushButton:
        """Create settings button."""
        btn = QPushButton()
        btn.setIcon(get_icon("settings", 20))
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip("Settings")
        btn.setFixedSize(48, 48)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                margin: {SPACING.xs}px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
            }}
        """
        )
        btn.clicked.connect(self.settings_clicked.emit)
        return btn

    def _on_nav_click(self, index: int):
        """Handle navigation button click."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

    def set_active_page(self, index: int):
        """Set active page by index."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
