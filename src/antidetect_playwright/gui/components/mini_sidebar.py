"""Mini sidebar with icon navigation."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QPushButton,
    QSizePolicy,
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
        self._settings_button: QPushButton | None = None
        self._toggle_button: QPushButton | None = None
        self._collapsed = False
        self._setup_ui()

    def _setup_ui(self):
        """Setup sidebar UI."""
        self.setObjectName("miniSidebar")
        self.setMinimumWidth(48)
        self.setMaximumWidth(72)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

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

        self._toggle_button = self._create_toggle_button()
        layout.addWidget(self._toggle_button)

        # Settings button at bottom
        self._settings_button = self._create_settings_button()
        layout.addWidget(self._settings_button)

        self.set_collapsed(False)

    def _create_nav_button(
        self, icon_name: str, tooltip: str, page_index: int
    ) -> QPushButton:
        """Create navigation button."""
        btn = QPushButton()
        btn.setIcon(get_icon(icon_name, 20))
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip(tooltip)
        btn.setFixedHeight(40)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setCheckable(True)
        btn.setProperty("page_index", page_index)
        btn.setProperty("label", tooltip)
        btn.clicked.connect(lambda checked, idx=page_index: self._on_nav_click(idx))
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                margin: {SPACING.xs}px;
                text-align: left;
                padding-left: {SPACING.sm}px;
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

    def _create_toggle_button(self) -> QPushButton:
        """Create collapse/expand button."""
        btn = QPushButton()
        btn.setIcon(get_icon("chevron_left", 16))
        btn.setIconSize(QSize(16, 16))
        btn.setToolTip("Collapse sidebar")
        btn.setFixedHeight(36)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("label", "Collapse")
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                margin: {SPACING.xs}px;
                text-align: left;
                padding-left: {SPACING.sm}px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
            }}
        """
        )
        btn.clicked.connect(self.toggle_collapsed)
        return btn

    def _create_settings_button(self) -> QPushButton:
        """Create settings button."""
        btn = QPushButton()
        btn.setIcon(get_icon("settings", 20))
        btn.setIconSize(QSize(20, 20))
        btn.setToolTip("Settings")
        btn.setFixedHeight(40)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("label", "Settings")
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                margin: {SPACING.xs}px;
                text-align: left;
                padding-left: {SPACING.sm}px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
            }}
        """
        )
        btn.clicked.connect(self.settings_clicked.emit)
        return btn

    def set_collapsed(self, collapsed: bool) -> None:
        """Collapse/expand sidebar labels."""
        if self._collapsed == collapsed:
            return
        self._collapsed = collapsed

        width = 56 if collapsed else 180
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)

        for btn in self.nav_buttons:
            label = btn.property("label") or ""
            btn.setText("" if collapsed else f" {label}")

        if self._toggle_button is not None:
            icon = "chevron_right" if collapsed else "chevron_left"
            self._toggle_button.setIcon(get_icon(icon, 16))
            label = self._toggle_button.property("label") or ""
            self._toggle_button.setText("" if collapsed else f" {label}")
            self._toggle_button.setToolTip(
                "Expand sidebar" if collapsed else "Collapse sidebar"
            )

        if self._settings_button is not None:
            label = self._settings_button.property("label") or ""
            self._settings_button.setText("" if collapsed else f" {label}")

    def toggle_collapsed(self) -> None:
        """Toggle collapsed state."""
        self.set_collapsed(not self._collapsed)

    def _on_nav_click(self, index: int):
        """Handle navigation button click."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.page_changed.emit(index)

    def set_active_page(self, index: int):
        """Set active page by index."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
