"""Unified theme system for consistent UI/UX."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Colors:
    """Color palette."""

    # Background
    bg_primary: str = "#1a1a1a"
    bg_secondary: str = "#161616"
    bg_tertiary: str = "#232323"
    bg_hover: str = "#2a2a2a"
    bg_selected: str = "#3a3a3a"

    # Accent
    accent: str = "#888888"
    accent_hover: str = "#a0a0a0"
    accent_light: str = "#707070"

    # Status
    success: str = "#4ade80"
    warning: str = "#fbbf24"
    error: str = "#f87171"
    info: str = "#60a5fa"

    # Text
    text_primary: str = "#ffffff"
    text_secondary: str = "#9ca3af"
    text_muted: str = "#6b7280"

    # Border
    border: str = "#2e2e2e"
    border_light: str = "#3e3e3e"

    # Tags
    tag_bg: str = "#2a2a2a"
    tag_text: str = "#d1d5db"


@dataclass(frozen=True, slots=True)
class Typography:
    """Typography settings."""

    font_family: str = (
        "system-ui, Segoe UI, SF Pro Text, -apple-system, sans-serif"
    )
    font_size_xs: int = 10
    font_size_sm: int = 11
    font_size_base: int = 13
    font_size_lg: int = 15
    font_size_xl: int = 18
    font_size_xxl: int = 22


@dataclass(frozen=True, slots=True)
class Spacing:
    """Spacing values."""

    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True, slots=True)
class BorderRadius:
    """Border radius values."""

    none: int = 0
    sm: int = 4  # Only for buttons and labels/badges
    full: int = 9999


class Theme:
    """Unified theme with colors, typography, and spacing."""

    colors: ClassVar[Colors] = Colors()
    typography: ClassVar[Typography] = Typography()
    spacing: ClassVar[Spacing] = Spacing()
    radius: ClassVar[BorderRadius] = BorderRadius()

    # Table constants
    TABLE_ROW_HEIGHT: ClassVar[int] = 40  # Enough for 28px buttons + padding
    TABLE_ROW_HEIGHT_COMPACT: ClassVar[int] = 32

    # Column width constants (min-width approach)
    COL_CHECKBOX: ClassVar[int] = 36  # Checkbox column (18px checkbox + padding)
    COL_ACTIONS_SM: ClassVar[int] = 80  # 1-2 buttons
    COL_ACTIONS_MD: ClassVar[int] = 120  # 2-3 buttons
    COL_ACTIONS_LG: ClassVar[int] = 180  # 4+ buttons
    COL_DATE: ClassVar[int] = 150  # Date/time column
    COL_STATUS: ClassVar[int] = 100  # Status column

    # Button constants for table cells
    BTN_ICON_SIZE: ClassVar[int] = 24  # Icon button size in table

    @staticmethod
    def setup_table(table) -> None:
        """Apply unified table styling.

        Call after setting columns and headers.
        Sets: selection behavior, grid, vertical header, alternating colors,
        focus policy, frame shape.
        """
        from PyQt6.QtWidgets import QAbstractItemView, QFrame, QHeaderView
        from PyQt6.QtCore import Qt

        # Disable editing
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Selection
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # Appearance
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

        # Remove cell padding that causes checkbox misalignment
        current_style = table.styleSheet() or ""
        table.setStyleSheet(
            current_style
            + """
            QTableWidget, QTableView {
                gridline-color: transparent;
            }
            QTableWidget::item, QTableView::item {
                padding: 0px 8px;
                margin: 0px;
            }
            QTableWidget::item:first-child, QTableView::item:first-child {
                padding: 0px;
            }
        """
        )

        # Row height - set default for all rows
        v_header = table.verticalHeader()
        v_header.setVisible(False)
        v_header.setDefaultSectionSize(Theme.TABLE_ROW_HEIGHT)
        v_header.setMinimumSectionSize(Theme.TABLE_ROW_HEIGHT)

        # Frame
        table.setFrameShape(QFrame.Shape.NoFrame)

        # Focus
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Header styling
        header = table.horizontalHeader()
        header.setHighlightSections(False)
        header.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        header.setFixedHeight(Theme.TABLE_ROW_HEIGHT)

    @staticmethod
    def apply_table_density(table, compact: bool) -> None:
        """Apply compact/comfortable density to a table."""
        height = Theme.TABLE_ROW_HEIGHT_COMPACT if compact else Theme.TABLE_ROW_HEIGHT
        v_header = table.verticalHeader()
        v_header.setDefaultSectionSize(height)
        v_header.setMinimumSectionSize(height)
        header = table.horizontalHeader()
        header.setFixedHeight(height)

    @staticmethod
    def setup_table_columns(
        table,
        column_configs: list[tuple[int, str, int | None]],
        stretch_column: int | None = None,
    ) -> None:
        """Configure table columns with proper sizing.

        Args:
            table: QTableWidget instance
            column_configs: List of (column_index, mode, width) tuples
                mode: "fixed" | "auto" | "stretch"
                width: Column width (required for "fixed", optional for "auto")
            stretch_column: Index of column that should stretch to fill space
                           (alternative to specifying "stretch" in configs)

        Example:
            Theme.setup_table_columns(table, [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "stretch", None),               # Name - fills space
                (2, "fixed", Theme.COL_DATE),       # Date
                (3, "fixed", Theme.COL_ACTIONS_MD), # Actions
            ])
        """
        from PyQt6.QtWidgets import QHeaderView

        header = table.horizontalHeader()

        for col_index, mode, width in column_configs:
            if mode == "fixed":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Fixed)
                if width:
                    table.setColumnWidth(col_index, width)
            elif mode == "stretch":
                header.setSectionResizeMode(col_index, QHeaderView.ResizeMode.Stretch)
            elif mode == "auto":
                header.setSectionResizeMode(
                    col_index, QHeaderView.ResizeMode.ResizeToContents
                )
                if width:
                    # Set minimum width via column width (ResizeToContents respects this)
                    table.setColumnWidth(col_index, width)

        # Handle stretch_column shortcut
        if stretch_column is not None:
            header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)

    @staticmethod
    def position_header_checkbox(table, checkbox, column: int = 0) -> None:
        """Position a header checkbox widget over a table column.

        Args:
            table: QTableWidget instance
            checkbox: Widget to position (typically HeaderCheckbox)
            column: Column index to position over (default 0)
        """
        if not checkbox or not table:
            return
        header = table.horizontalHeader()

        # Calculate x position (account for vertical header if visible)
        x = 0
        if table.verticalHeader().isVisible():
            x = table.verticalHeader().width()

        # Add offset for columns before target
        for col in range(column):
            x += header.sectionSize(col)

        # Center checkbox in column
        col_width = header.sectionSize(column)
        checkbox_width = checkbox.width()
        x += (col_width - checkbox_width) // 2

        # Center vertically in header
        header_height = header.height()
        checkbox_height = checkbox.height()
        y = (header_height - checkbox_height) // 2

        checkbox.setGeometry(x, y, checkbox_width, checkbox_height)
        checkbox.raise_()

    @classmethod
    def create_table_container(cls, table) -> "QFrame":
        """Wrap table in styled container with rounded corners.

        Returns QFrame containing the table. Add the frame to your layout
        instead of the table directly.
        """
        from PyQt6.QtWidgets import QFrame, QVBoxLayout

        c = cls.colors

        container = QFrame()
        container.setObjectName("tableContainer")
        container.setStyleSheet(
            f"""
            QFrame#tableContainer {{
                background-color: {c.bg_secondary};
                border: 1px solid {c.border};
                border-radius: 0;
            }}
        """
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(table)

        return container

    @classmethod
    def get_stylesheet(cls) -> str:
        """Generate complete application stylesheet."""
        c = cls.colors
        t = cls.typography
        s = cls.spacing
        r = cls.radius

        down_arrow_svg = (
            "data:image/svg+xml;utf8,"
            "<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24'>"
            f"<path fill='{c.text_secondary.replace('#', '%23')}' d='M7 10l5 5 5-5z'/>"
            "</svg>"
        )

        return f"""
        /* === BASE STYLES === */
        QMainWindow {{
            background-color: {c.bg_primary};
        }}

        QWidget {{
            background-color: transparent;
            color: {c.text_primary};
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
        }}

        /* === BUTTONS === */
        QPushButton {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r.sm}px;
            padding: {s.sm}px {s.lg}px;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
            font-weight: 500;
        }}

        QPushButton:hover {{
            background-color: {c.bg_hover};
            border-color: {c.border_light};
        }}

        QPushButton:pressed {{
            background-color: {c.bg_selected};
        }}

        QPushButton:disabled {{
            background-color: {c.bg_secondary};
            color: {c.text_muted};
        }}

        QPushButton[class="primary"] {{
            background-color: {c.accent};
            border-color: {c.accent};
            color: white;
        }}

        QPushButton[class="primary"]:hover {{
            background-color: {c.accent_hover};
        }}

        QPushButton[class="success"] {{
            background-color: {c.success};
            border-color: {c.success};
            color: white;
        }}

        QPushButton[class="success"]:hover {{
            background-color: #16a34a;
        }}

        QPushButton[class="danger"] {{
            background-color: {c.error};
            border-color: {c.error};
            color: white;
        }}

        QPushButton[class="danger"]:hover {{
            background-color: #dc2626;
        }}

        QPushButton[class="ghost"] {{
            background-color: transparent;
            border: none;
        }}

        QPushButton[class="ghost"]:hover {{
            background-color: {c.bg_hover};
        }}

        QPushButton[class="icon"] {{
            padding: 2px;
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
            border: 1px solid {c.border};
            background-color: {c.bg_secondary};
            border-radius: 4px;
        }}

        QPushButton[class="icon"]:hover {{
            background-color: {c.bg_hover};
            border-color: {c.border_light};
        }}

        QPushButton[class="icon"]:pressed {{
            background-color: {c.accent};
            border-color: {c.accent};
        }}

        /* === INPUTS === */
        QLineEdit {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.sm}px {s.md}px;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
            selection-background-color: {c.accent};
        }}

        QLineEdit:focus {{
            border-color: {c.accent};
        }}

        QLineEdit[error="true"] {{
            border-color: {c.error};
        }}

        QLineEdit:disabled {{
            background-color: {c.bg_secondary};
            color: {c.text_muted};
        }}

        QTextEdit {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.sm}px;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
            selection-background-color: {c.accent};
        }}

        QTextEdit:focus {{
            border-color: {c.accent};
        }}

        QTextEdit[error="true"] {{
            border-color: {c.error};
        }}

        /* === COMBOBOX === */
        QComboBox {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.sm}px {s.md}px;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
            min-width: 80px;
        }}

        QComboBox:hover {{
            border-color: {c.border_light};
        }}

        QComboBox:focus {{
            border-color: {c.accent};
        }}

        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid {c.border};
            background: {c.bg_secondary};
        }}

        QComboBox::drop-down:hover {{
            background: {c.bg_hover};
        }}

        QComboBox::down-arrow {{
            image: url("{down_arrow_svg}");
            width: 12px;
            height: 12px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c.bg_tertiary};
            border: 1px solid {c.border};
            border-radius: 0;
            selection-background-color: {c.accent};
            font-family: {t.font_family};
        }}

        /* === INLINE ALERT === */
        QFrame#inlineAlert {{
            background-color: {c.bg_secondary};
            border: 1px solid {c.error};
            border-radius: {r.sm}px;
        }}

        QLabel#inlineAlertTitle {{
            color: {c.error};
            font-weight: 700;
        }}

        QLabel#inlineAlertMessage {{
            color: {c.error};
        }}

        /* === SPINBOX === */
        QSpinBox {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.sm}px {s.md}px;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
        }}

        QSpinBox:focus {{
            border-color: {c.accent};
        }}

        /* === TABLE === */
        QTableWidget {{
            background-color: {c.bg_secondary};
            alternate-background-color: {c.bg_tertiary};
            border: 1px solid {c.border};
            border-radius: 0;
            gridline-color: transparent;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
            outline: none;
        }}

        QTableWidget::item {{
            padding: {s.sm}px {s.md}px;
            border: none;
            border-bottom: 1px solid {c.border};
        }}

        QTableWidget::item:selected {{
            background-color: {c.bg_selected};
            color: {c.text_primary};
        }}

        QTableWidget::item:hover:!selected {{
            background-color: {c.bg_hover};
        }}

        QTableWidget::item:focus {{
            outline: none;
            border: none;
        }}

        QHeaderView {{
            background-color: transparent;
        }}

        QHeaderView::section {{
            background-color: {c.bg_tertiary};
            color: {c.text_secondary};
            border: none;
            border-bottom: 1px solid {c.border};
            border-right: 1px solid {c.border};
            padding: {s.md}px {s.md}px;
            font-family: {t.font_family};
            font-size: {t.font_size_sm}px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        QHeaderView::section:last {{
            border-right: none;
        }}

        QHeaderView::section:first {{
            border-top-left-radius: 0;
        }}

        QHeaderView::section:only-one {{
            border-top-left-radius: 0;
            border-top-right-radius: 0;
        }}

        /* Table corner button */
        QTableCornerButton::section {{
            background-color: {c.bg_tertiary};
            border: none;
            border-bottom: 1px solid {c.border};
        }}

        /* Scrollbar inside table */
        QTableWidget QScrollBar:vertical {{
            background-color: {c.bg_secondary};
            width: 8px;
            border-radius: 4px;
            margin: 0;
        }}

        QTableWidget QScrollBar::handle:vertical {{
            background-color: {c.border_light};
            border-radius: 4px;
            min-height: 30px;
        }}

        QTableWidget QScrollBar::handle:vertical:hover {{
            background-color: {c.text_muted};
        }}

        QTableWidget QScrollBar::add-line:vertical,
        QTableWidget QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        /* === CARDS / PANELS === */
        QFrame[class="card"] {{
            background-color: {c.bg_secondary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.lg}px;
        }}

        QFrame[class="panel"] {{
            background-color: {c.bg_tertiary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.md}px;
        }}

        QFrame#addProxyFrame {{
            background-color: {c.bg_secondary};
            border: 1px solid {c.border};
            border-radius: 0;
        }}

        /* === LABELS === */
        QLabel {{
            color: {c.text_primary};
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
        }}

        QLabel[class="heading"] {{
            font-size: {t.font_size_xl}px;
            font-weight: 600;
        }}

        QLabel[class="subheading"] {{
            font-size: {t.font_size_lg}px;
            font-weight: 500;
        }}

        QLabel[class="muted"] {{
            color: {c.text_muted};
            font-size: {t.font_size_sm}px;
        }}

        QLabel[class="secondary"] {{
            color: {c.text_secondary};
        }}

        /* === STATUS BADGES === */
        QLabel[class="badge"] {{
            border-radius: {r.sm}px;
            padding: {s.xs}px {s.sm}px;
            font-size: {t.font_size_sm}px;
            font-weight: 600;
        }}

        QLabel[class="badge-success"] {{
            background-color: {c.success};
            color: white;
            border-radius: {r.sm}px;
            padding: {s.xs}px {s.sm}px;
            font-size: {t.font_size_sm}px;
            font-weight: 600;
        }}

        QLabel[class="badge-error"] {{
            background-color: {c.error};
            color: white;
            border-radius: {r.sm}px;
            padding: {s.xs}px {s.sm}px;
            font-size: {t.font_size_sm}px;
            font-weight: 600;
        }}

        QLabel[class="badge-muted"] {{
            background-color: {c.text_muted};
            color: white;
            border-radius: {r.sm}px;
            padding: {s.xs}px {s.sm}px;
            font-size: {t.font_size_sm}px;
            font-weight: 600;
        }}

        /* === TAGS === */
        QLabel[class="tag"] {{
            background-color: {c.tag_bg};
            color: {c.tag_text};
            border-radius: {r.sm}px;
            padding: 2px {s.sm}px;
            font-size: {t.font_size_sm}px;
        }}

        /* === SCROLLBAR === */
        QScrollBar:vertical {{
            background-color: {c.bg_primary};
            width: 8px;
            border-radius: {r.sm}px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {c.border_light};
            border-radius: {r.sm}px;
            min-height: 40px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {c.text_muted};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}

        QScrollBar:horizontal {{
            background-color: {c.bg_primary};
            height: 8px;
            border-radius: {r.sm}px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {c.border_light};
            border-radius: {r.sm}px;
            min-width: 40px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {c.text_muted};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}

        /* === CHECKBOX === */
        QCheckBox {{
            color: {c.text_primary};
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
            spacing: {s.sm}px;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {r.sm}px;
            border: 1px solid {c.border};
            background-color: {c.bg_tertiary};
        }}

        QCheckBox::indicator:checked {{
            background-color: {c.accent};
            border-color: {c.accent};
        }}

        QCheckBox::indicator:hover {{
            border-color: {c.border_light};
        }}

        /* === GROUPBOX === */
        QGroupBox {{
            border: 1px solid {c.border};
            border-radius: 0;
            margin-top: {s.md}px;
            padding-top: {s.md}px;
            font-family: {t.font_family};
        }}

        QGroupBox::title {{
            color: {c.text_secondary};
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: {s.md}px;
            padding: 0 {s.xs}px;
        }}

        /* === MENU === */
        QMenu {{
            background-color: {c.bg_tertiary};
            border: 1px solid {c.border};
            border-radius: 0;
            padding: {s.xs}px;
            font-family: {t.font_family};
        }}

        QMenu::item {{
            padding: {s.sm}px {s.xl}px;
            border-radius: {r.sm}px;
        }}

        QMenu::item:selected {{
            background-color: {c.accent};
        }}

        QMenu::separator {{
            height: 1px;
            background-color: {c.border};
            margin: {s.xs}px {s.sm}px;
        }}

        /* === DIALOG === */
        QDialog {{
            background-color: {c.bg_tertiary};
        }}

        /* === TOOLTIP === */
        QToolTip {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
            border: 1px solid {c.border};
            border-radius: {r.sm}px;
            padding: {s.xs}px {s.sm}px;
            font-family: {t.font_family};
            font-size: {t.font_size_sm}px;
        }}

        /* === SIDEBAR === */
        #sidebar {{
            background-color: {c.bg_secondary};
            border-right: 1px solid {c.border};
        }}

        #miniSidebar {{
            background-color: {c.bg_tertiary};
            border-right: 1px solid {c.border};
        }}

        /* === HEADER === */
        #header {{
            background-color: {c.bg_tertiary};
            border-bottom: 1px solid {c.border};
        }}

        /* === FOOTER === */
        #footer {{
            background-color: {c.bg_secondary};
            border-top: 1px solid {c.border};
        }}

        /* === SPLITTER === */
        QSplitter::handle {{
            background-color: {c.border};
        }}

        QSplitter::handle:horizontal {{
            width: 1px;
        }}

        QSplitter::handle:vertical {{
            height: 1px;
        }}

        /* === TAB WIDGET === */
        QTabWidget::pane {{
            border: 1px solid {c.border};
            border-radius: 0;
            background-color: {c.bg_tertiary};
        }}

        QTabBar::tab {{
            background-color: {c.bg_secondary};
            color: {c.text_secondary};
            border: 1px solid {c.border};
            border-bottom: none;
            border-top-left-radius: 0;
            border-top-right-radius: 0;
            padding: {s.sm}px {s.lg}px;
            font-family: {t.font_family};
            font-size: {t.font_size_base}px;
        }}

        QTabBar::tab:selected {{
            background-color: {c.bg_tertiary};
            color: {c.text_primary};
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {c.bg_hover};
        }}
        """


# Convenience access
COLORS = Theme.colors
TYPOGRAPHY = Theme.typography
SPACING = Theme.spacing
RADIUS = Theme.radius
