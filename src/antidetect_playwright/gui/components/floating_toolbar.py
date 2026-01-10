"""Floating toolbar for batch operations on selected items."""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor

from ..theme import COLORS, SPACING, TYPOGRAPHY, RADIUS
from ..icons import get_icon


class FloatingToolbar(QFrame):
    """Contextual floating toolbar for batch operations.

    Appears centered at bottom when items are selected.
    Shows count and action buttons.
    """

    # Signals for batch operations
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    tag_clicked = pyqtSignal()
    notes_clicked = pyqtSignal()
    ping_clicked = pyqtSignal()
    delete_clicked = pyqtSignal()
    restore_clicked = pyqtSignal()
    visibility_changed = pyqtSignal(bool)  # Emitted when toolbar shows/hides

    def __init__(self, toolbar_type: str = "profiles", parent=None):
        """Initialize toolbar.

        Args:
            toolbar_type: One of 'profiles', 'proxy', 'tags', 'trash'
        """
        super().__init__(parent)
        self.toolbar_type = toolbar_type
        self._count = 0
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        """Setup toolbar UI."""
        self.setObjectName("floatingToolbar")
        self.setFixedHeight(44)

        # Styling
        self.setStyleSheet(
            f"QFrame#floatingToolbar {{ "
            f"background-color: {COLORS.bg_tertiary}; "
            f"border: 1px solid {COLORS.border}; "
            f"border-radius: {RADIUS.sm}px; "
            f"}}"
        )

        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING.md, SPACING.xs, SPACING.md, SPACING.xs)
        layout.setSpacing(SPACING.sm)

        # Count label
        self.count_label = QLabel("0 selected")
        self.count_label.setStyleSheet(
            f"color: {COLORS.text_primary}; "
            f"font-size: {TYPOGRAPHY.font_size_base}px; "
            f"font-weight: 600; "
            f"padding: 0 {SPACING.sm}px; "
            f"background: transparent; "
            f"border: none;"
        )
        layout.addWidget(self.count_label)

        # Separator line
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background-color: {COLORS.border_light}; border: none;")
        layout.addWidget(sep)

        # Action buttons based on type
        if self.toolbar_type == "profiles":
            self._add_profiles_actions(layout)
        elif self.toolbar_type == "proxy":
            self._add_proxy_actions(layout)
        elif self.toolbar_type == "tags":
            self._add_tags_actions(layout)
        elif self.toolbar_type == "trash":
            self._add_trash_actions(layout)

    def _add_profiles_actions(self, layout):
        """Add profile-specific action buttons."""
        # Start
        start_btn = self._create_button("play", "Start", primary=True)
        start_btn.clicked.connect(self.start_clicked.emit)
        layout.addWidget(start_btn)

        # Stop
        stop_btn = self._create_button("stop", "Stop")
        stop_btn.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(stop_btn)

        # Separator
        self._add_separator(layout)

        # Tag
        tag_btn = self._create_button("tag", "Tags")
        tag_btn.clicked.connect(self.tag_clicked.emit)
        layout.addWidget(tag_btn)

        # Notes
        notes_btn = self._create_button("edit", "Notes")
        notes_btn.clicked.connect(self.notes_clicked.emit)
        layout.addWidget(notes_btn)

        # Separator
        self._add_separator(layout)

        # Ping
        ping_btn = self._create_button("ping", "Ping")
        ping_btn.clicked.connect(self.ping_clicked.emit)
        layout.addWidget(ping_btn)

        # Separator
        self._add_separator(layout)

        # Delete
        delete_btn = self._create_button("trash", "Delete", danger=True)
        delete_btn.clicked.connect(self.delete_clicked.emit)
        layout.addWidget(delete_btn)

    def _add_proxy_actions(self, layout):
        """Add proxy-specific action buttons."""
        # Ping
        ping_btn = self._create_button("ping", "Ping", primary=True)
        ping_btn.clicked.connect(self.ping_clicked.emit)
        layout.addWidget(ping_btn)

        # Separator
        self._add_separator(layout)

        # Delete
        delete_btn = self._create_button("trash", "Delete", danger=True)
        delete_btn.clicked.connect(self.delete_clicked.emit)
        layout.addWidget(delete_btn)

    def _add_tags_actions(self, layout):
        """Add tags/notes/statuses action buttons."""
        # Delete
        delete_btn = self._create_button("trash", "Delete", danger=True)
        delete_btn.clicked.connect(self.delete_clicked.emit)
        layout.addWidget(delete_btn)

    def _add_trash_actions(self, layout):
        """Add trash page action buttons."""
        # Restore
        restore_btn = self._create_button("restore", "Restore", primary=True)
        restore_btn.clicked.connect(self.restore_clicked.emit)
        layout.addWidget(restore_btn)

        # Separator
        self._add_separator(layout)

        # Delete permanently
        delete_btn = self._create_button("trash", "Delete", danger=True)
        delete_btn.clicked.connect(self.delete_clicked.emit)
        layout.addWidget(delete_btn)

    def _add_separator(self, layout):
        """Add visual separator."""
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background-color: {COLORS.border_light}; border: none;")
        layout.addWidget(sep)

    def _create_button(
        self, icon_name: str, text: str, primary: bool = False, danger: bool = False
    ) -> QPushButton:
        """Create styled action button with icon and text."""
        btn = QPushButton(f" {text}")
        btn.setIcon(get_icon(icon_name, 14))
        btn.setIconSize(QSize(14, 14))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(32)

        if danger:
            bg = "transparent"
            bg_hover = COLORS.error
            text_color = COLORS.error
            text_hover = COLORS.text_primary
        elif primary:
            bg = COLORS.accent
            bg_hover = COLORS.accent_hover
            text_color = COLORS.text_primary
            text_hover = COLORS.text_primary
        else:
            bg = "transparent"
            bg_hover = COLORS.bg_hover
            text_color = COLORS.text_secondary
            text_hover = COLORS.text_primary

        btn.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {bg}; "
            f"color: {text_color}; "
            f"border: none; "
            f"border-radius: {RADIUS.sm}px; "
            f"padding: 0 {SPACING.sm}px; "
            f"font-size: {TYPOGRAPHY.font_size_sm}px; "
            f"font-weight: 500; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {bg_hover}; "
            f"color: {text_hover}; "
            f"}}"
        )
        return btn

    def update_count(self, count: int):
        """Update selected count and show/hide toolbar."""
        self._count = count
        self.count_label.setText(f"{count} selected")

        if count > 0:
            # Emit signal FIRST so parent can position before showing
            self.adjustSize()
            self.visibility_changed.emit(True)
            # Now show after positioning
            self.show()
            self.raise_()
        else:
            self.hide()
            self.visibility_changed.emit(False)

    @property
    def selected_count(self) -> int:
        """Get current selected count."""
        return self._count
