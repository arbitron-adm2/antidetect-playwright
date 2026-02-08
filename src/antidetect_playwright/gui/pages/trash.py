"""Trash page for deleted profiles."""

from PyQt6.QtGui import QPixmap

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QTableView,
    QMessageBox,
    QGridLayout,
    QStackedWidget,
    QMenu,
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize

from ..theme import Theme, COLORS, SPACING
from ..icons import get_icon, ICON_TRASH, svg_icon
from ..components import FloatingToolbar, HeaderCheckbox, CheckboxWidget
from ..modal import confirm_dialog
from ..table_models import SimpleTableModel


class TrashPage(QWidget):
    """Trash page for deleted profiles."""

    restore_requested = pyqtSignal(list)  # List of profile IDs to restore
    permanent_delete_requested = pyqtSignal(
        list
    )  # List of profile IDs to permanently delete
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._deleted_profiles: list[dict] = []  # List of {id, name, deleted_at}
        self._selected_rows: list[int] = []
        self._header_checked = False
        # Removed _compact_mode - no longer hiding columns on resize
        self._setup_ui()

    def _setup_ui(self):
        """Setup page UI."""
        self.setObjectName("trashPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xl, SPACING.xl, SPACING.xl, SPACING.xl)
        layout.setSpacing(SPACING.lg)

        # Header
        header_layout = QHBoxLayout()

        header = QLabel("Trash")
        header.setProperty("class", "heading")
        header_layout.addWidget(header)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        desc = QLabel(
            "Deleted profiles are moved here. You can restore or permanently delete them."
        )
        desc.setProperty("class", "secondary")
        layout.addWidget(desc)

        # Content stack (table or empty placeholder)
        self.content_stack = QStackedWidget()

        # Table area
        table_area = QWidget()
        table_area_layout = QGridLayout(table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Table
        self.table = self._create_table()
        table_container = Theme.create_table_container(self.table)
        table_area_layout.addWidget(table_container, 0, 0)

        # Header checkbox overlay
        self._header_checkbox = HeaderCheckbox()
        self._header_checkbox.toggled.connect(self._on_header_checkbox_toggled)
        self._header_checkbox.setParent(self.table)
        self._header_checkbox.setFixedSize(24, 24)
        self._position_header_checkbox()
        self._header_checkbox.raise_()
        self._header_checkbox.show()

        self.table.horizontalHeader().sectionResized.connect(
            lambda: self._position_header_checkbox()
        )

        # Floating toolbar container
        toolbar_container = QWidget()
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(0, 0, 0, SPACING.md)
        toolbar_layout.setSpacing(0)
        toolbar_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.floating_toolbar = FloatingToolbar("trash")
        self.floating_toolbar.restore_clicked.connect(self._on_batch_restore)
        self.floating_toolbar.delete_clicked.connect(self._on_batch_delete)
        toolbar_layout.addWidget(self.floating_toolbar)
        table_area_layout.addWidget(
            toolbar_container,
            0,
            0,
            alignment=Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignBottom,
        )

        self.content_stack.addWidget(table_area)

        # Empty placeholder with icon
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.addStretch()

        # Trash icon in circle
        icon_container = QWidget()
        icon_container.setFixedSize(80, 80)
        icon_container.setStyleSheet(f"""
            background-color: {COLORS.bg_tertiary};
            border-radius: 40px;
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon_label = QLabel()
        icon = svg_icon(ICON_TRASH, 32, COLORS.text_muted)
        icon_label.setPixmap(icon.pixmap(32, 32))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        icon_wrapper = QHBoxLayout()
        icon_wrapper.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_wrapper.addWidget(icon_container)
        empty_layout.addLayout(icon_wrapper)
        
        empty_layout.addSpacing(SPACING.md)

        self.empty_label = QLabel("Trash is empty")
        self.empty_label.setProperty("class", "subheading")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_label)
        
        empty_subtitle = QLabel("Deleted profiles will appear here")
        empty_subtitle.setProperty("class", "muted")
        empty_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_subtitle)

        empty_layout.addStretch()
        self.content_stack.addWidget(empty_widget)

        layout.addWidget(self.content_stack, 1)

        # Start with empty state
        self.content_stack.setCurrentIndex(1)

    def _create_table(self) -> QTableView:
        """Create trash table."""
        table = QTableView()

        headers = ["", "Name", "Deleted At", "Actions"]
        self.table_model = SimpleTableModel(headers, self)
        self.table_model.set_alignments({2: Qt.AlignmentFlag.AlignCenter})
        table.setModel(self.table_model)

        # Apply unified styling first
        Theme.setup_table(table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "stretch", None),  # Name - fills space
                (2, "fixed", Theme.COL_DATE),  # Deleted At
                (3, "fixed", Theme.COL_ACTIONS_SM),  # Actions (menu only)
            ],
        )

        table.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)

        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_context_menu)

        return table

    # Removed resizeEvent and _apply_responsive_columns
    # Table columns are now configured once with proper sizing modes
    # The Stretch mode ensures table scales correctly without hiding columns

    def _on_context_menu(self, pos):
        index = self.table.indexAt(pos)
        row = index.row()
        if row < 0:
            return
        self._show_row_context_menu(row, self.table.mapToGlobal(pos))

    def _show_row_context_menu(self, row: int, global_pos):
        if row < 0 or row >= len(self._deleted_profiles):
            return
        menu = QMenu(self)
        
        restore_action = menu.addAction(get_icon("restore", 14), "Restore")
        restore_action.triggered.connect(lambda: self._restore_profile(row))
        
        menu.addSeparator()
        
        delete_action = menu.addAction(get_icon("trash", 14), "Delete permanently")
        delete_action.triggered.connect(lambda: self._permanent_delete(row))
        
        menu.exec(global_pos)

    def update_deleted_profiles(self, profiles: list[dict]):
        """Update list of deleted profiles."""
        self._deleted_profiles = list(profiles)
        self._refresh_table()

    def _refresh_table(self):
        """Refresh trash table."""
        self._selected_rows.clear()
        self.floating_toolbar.update_count(0)

        if not self._deleted_profiles:
            self.table_model.set_rows([])
            self.content_stack.setCurrentIndex(1)  # Empty placeholder
            return

        self.content_stack.setCurrentIndex(0)  # Table

        rows: list[list[str]] = []
        payloads: list[str | None] = []
        for profile in self._deleted_profiles:
            deleted_at = profile.get("deleted_at", "")
            deleted_text = str(deleted_at)[:19] if deleted_at else "—"
            rows.append(["", profile.get("name", "Unknown"), deleted_text, ""])
            payloads.append(profile.get("id"))

        self.table_model.set_rows(rows, payloads)

        for row in range(len(self._deleted_profiles)):
            # Checkbox
            self._add_checkbox_to_row(row)

            # Actions
            actions = self._create_actions_widget(row)
            self.table.setIndexWidget(self.table_model.index(row, 3), actions)

    def _add_checkbox_to_row(self, row: int):
        """Add checkbox to row."""
        checkbox = CheckboxWidget()
        checkbox.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        checkbox.customContextMenuRequested.connect(
            lambda pos, r=row, w=checkbox: self._show_row_context_menu(
                r, w.mapToGlobal(pos)
            )
        )
        checkbox.toggled.connect(
            lambda checked, r=row: self._on_row_checkbox_toggled(r, checked)
        )
        self.table.setIndexWidget(self.table_model.index(row, 0), checkbox)

    def _create_actions_widget(self, row: int) -> QWidget:
        """Create actions widget for row with single menu button."""
        widget = QWidget()
        widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda _pos, r=row, w=widget: self._show_row_context_menu(
                r, w.mapToGlobal(w.rect().bottomLeft())
            )
        )
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_size = Theme.BTN_ICON_SIZE

        # Single menu button with vertical dots
        menu_btn = QPushButton()
        menu_btn.setIcon(get_icon("more", 14))
        menu_btn.setIconSize(QSize(14, 14))
        menu_btn.setFixedSize(btn_size, btn_size)
        menu_btn.setProperty("class", "icon")
        menu_btn.setToolTip("Actions")
        menu_btn.clicked.connect(
            lambda checked=False, r=row, w=menu_btn: self._show_row_context_menu(
                r, w.mapToGlobal(w.rect().bottomLeft())
            )
        )
        layout.addWidget(menu_btn)

        layout.addStretch()
        return widget

    def _restore_profile(self, row: int):
        """Restore single profile."""
        if 0 <= row < len(self._deleted_profiles):
            profile_id = self._deleted_profiles[row].get("id")
            if profile_id:
                self.restore_requested.emit([profile_id])

    def _permanent_delete(self, row: int):
        """Permanently delete single profile."""
        if 0 <= row < len(self._deleted_profiles):
            profile_id = self._deleted_profiles[row].get("id")
            if profile_id:
                if confirm_dialog(
                    self,
                    "Confirm Delete",
                    "This action cannot be undone. Delete permanently?",
                ):
                    self.permanent_delete_requested.emit([profile_id])

    def _on_empty_trash(self):
        """Handle empty trash button."""
        if not self._deleted_profiles:
            return
        if confirm_dialog(
            self,
            "Empty Trash",
            f"Permanently delete {len(self._deleted_profiles)} profile(s)? This cannot be undone.",
        ):
            self.permanent_delete_requested.emit(
                [p["id"] for p in self._deleted_profiles]
            )

    # === Selection handling ===

    def _on_header_section_clicked(self, section: int):
        """Handle header click."""
        pass  # HeaderCheckbox handles this

    def _on_header_checkbox_toggled(self, checked: bool):
        """Handle header checkbox toggle."""
        self._header_checked = checked
        self._toggle_all_checkboxes(checked)

    def _toggle_all_checkboxes(self, checked: bool):
        """Toggle all checkboxes and sync header."""
        for row in range(self.table_model.rowCount()):
            widget = self.table.indexWidget(self.table_model.index(row, 0))
            if isinstance(widget, CheckboxWidget):
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

        if checked:
            self._selected_rows = list(range(self.table_model.rowCount()))
        else:
            self._selected_rows.clear()

        # Sync header checkbox state
        self._header_checked = checked
        if self._header_checkbox:
            self._header_checkbox.blockSignals(True)
            self._header_checkbox.setChecked(checked)
            self._header_checkbox.blockSignals(False)

        self._update_selection()

    def _on_row_checkbox_toggled(self, row: int, checked: bool):
        """Handle row checkbox toggle."""
        if checked:
            if row not in self._selected_rows:
                self._selected_rows.append(row)
        else:
            if row in self._selected_rows:
                self._selected_rows.remove(row)
        self._update_selection()
        self._update_header_state()

    def _update_header_state(self):
        """Update header checkbox state."""
        total = self.table_model.rowCount()
        if total > 0 and len(self._selected_rows) == total:
            self._header_checked = True
        else:
            self._header_checked = False

        if self._header_checkbox:
            self._header_checkbox.blockSignals(True)
            self._header_checkbox.setChecked(self._header_checked)
            self._header_checkbox.blockSignals(False)

    def _update_selection(self):
        """Update selection state."""
        count = len(self._selected_rows)
        self.floating_toolbar.update_count(count)
        self.selection_changed.emit(count)

    def get_selected_profile_ids(self) -> list[str]:
        """Get selected profile IDs."""
        ids: list[str] = []
        for row in sorted(self._selected_rows):
            profile_id = self.table_model.payload_at(row)
            if profile_id:
                ids.append(profile_id)
        return ids

    def _on_batch_restore(self):
        """Handle batch restore."""
        ids = self.get_selected_profile_ids()
        if ids:
            self.restore_requested.emit(ids)
            self._toggle_all_checkboxes(False)

    def _on_batch_delete(self):
        """Handle batch delete."""
        ids = self.get_selected_profile_ids()
        if ids:
            if confirm_dialog(
                self,
                "Confirm Delete",
                "Delete selected profiles permanently?",
            ):
                self.permanent_delete_requested.emit(ids)
                self._toggle_all_checkboxes(False)

    # === Positioning ===

    def _position_header_checkbox(self):
        """Position header checkbox."""
        if not self._header_checkbox or not self.table:
            return
        Theme.position_header_checkbox(self.table, self._header_checkbox)



    def set_empty(self, is_empty: bool):
        """Toggle empty state visibility."""
        if is_empty:
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_stack.setCurrentIndex(0)
