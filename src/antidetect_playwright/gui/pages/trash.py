"""Trash page for deleted profiles."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QStackedWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer

from ..theme import Theme, COLORS, SPACING
from ..icons import get_icon
from ..components import FloatingToolbar, CheckboxWidget, HeaderCheckbox


class TrashPage(QWidget):
    """Trash page for deleted profiles."""

    restore_requested = pyqtSignal(list)  # List of profile IDs to restore
    permanent_delete_requested = pyqtSignal(
        list
    )  # List of profile IDs to permanently delete
    empty_trash_requested = pyqtSignal()
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._deleted_profiles: list[dict] = []  # List of {id, name, deleted_at}
        self._selected_rows: list[int] = []
        self._header_checked = False
        self._table_area: QWidget | None = None
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

        # Empty trash button
        empty_btn = QPushButton(" Empty Trash")
        empty_btn.setIcon(get_icon("trash", 14))
        empty_btn.setIconSize(QSize(14, 14))
        empty_btn.setProperty("class", "danger")
        empty_btn.clicked.connect(self._on_empty_trash)
        header_layout.addWidget(empty_btn)

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
        self._table_area = QWidget()
        table_area_layout = QVBoxLayout(self._table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Table
        self.table = self._create_table()
        table_container = Theme.create_table_container(self.table)
        table_area_layout.addWidget(table_container, 1)

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

        # Floating toolbar
        self.floating_toolbar = FloatingToolbar("trash")
        self.floating_toolbar.setParent(self._table_area)
        self.floating_toolbar.restore_clicked.connect(self._on_batch_restore)
        self.floating_toolbar.delete_clicked.connect(self._on_batch_delete)
        self.floating_toolbar.visibility_changed.connect(
            lambda visible: self._position_toolbar() if visible else None
        )

        self._table_area.installEventFilter(self)
        self.content_stack.addWidget(self._table_area)

        # Empty placeholder
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.addStretch()

        self.empty_label = QLabel("Trash is empty")
        self.empty_label.setProperty("class", "muted")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_label)

        empty_layout.addStretch()
        self.content_stack.addWidget(empty_widget)

        layout.addWidget(self.content_stack, 1)

        # Start with empty state
        self.content_stack.setCurrentIndex(1)

    def _create_table(self) -> QTableWidget:
        """Create trash table."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["", "Name", "Deleted At", "Actions"])

        # Apply unified styling first
        Theme.setup_table(table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "stretch", None),  # Name - fills space
                (2, "fixed", Theme.COL_DATE),  # Deleted At
                (3, "fixed", Theme.COL_ACTIONS_SM),  # Actions (2 buttons)
            ],
        )

        table.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)

        return table

    def update_deleted_profiles(self, profiles: list[dict]):
        """Update list of deleted profiles."""
        self._deleted_profiles = list(profiles)
        self._refresh_table()

    def _refresh_table(self):
        """Refresh trash table."""
        self._selected_rows.clear()
        self.floating_toolbar.update_count(0)

        if not self._deleted_profiles:
            self.content_stack.setCurrentIndex(1)  # Empty placeholder
            return

        self.content_stack.setCurrentIndex(0)  # Table
        self.table.setRowCount(len(self._deleted_profiles))

        for row, profile in enumerate(self._deleted_profiles):
            # Checkbox
            self._add_checkbox_to_row(row)

            # Name
            name_item = QTableWidgetItem(profile.get("name", "Unknown"))
            self.table.setItem(row, 1, name_item)

            # Deleted At
            deleted_at = profile.get("deleted_at", "")
            if deleted_at:
                deleted_item = QTableWidgetItem(str(deleted_at)[:19])
            else:
                deleted_item = QTableWidgetItem("—")
            deleted_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, deleted_item)

            # Actions
            actions = self._create_actions_widget(row)
            self.table.setCellWidget(row, 3, actions)

    def _add_checkbox_to_row(self, row: int):
        """Add checkbox to row."""
        checkbox = CheckboxWidget()
        checkbox.toggled.connect(
            lambda checked, r=row: self._on_row_checkbox_toggled(r, checked)
        )
        self.table.setCellWidget(row, 0, checkbox)

    def _create_actions_widget(self, row: int) -> QWidget:
        """Create actions widget for row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_size = Theme.BTN_ICON_SIZE

        # Restore button
        restore_btn = QPushButton()
        restore_btn.setIcon(get_icon("restore", 14))
        restore_btn.setIconSize(QSize(14, 14))
        restore_btn.setFixedSize(btn_size, btn_size)
        restore_btn.setProperty("class", "icon")
        restore_btn.setToolTip("Restore")
        restore_btn.clicked.connect(lambda: self._restore_profile(row))
        layout.addWidget(restore_btn)

        # Permanent delete button
        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", 14))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(btn_size, btn_size)
        del_btn.setProperty("class", "icon")
        del_btn.setToolTip("Delete permanently")
        del_btn.clicked.connect(lambda: self._permanent_delete(row))
        layout.addWidget(del_btn)

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
                reply = QMessageBox.question(
                    self,
                    "Confirm Delete",
                    "This action cannot be undone. Delete permanently?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.permanent_delete_requested.emit([profile_id])

    def _on_empty_trash(self):
        """Handle empty trash button."""
        if not self._deleted_profiles:
            return
        reply = QMessageBox.question(
            self,
            "Empty Trash",
            f"Permanently delete {len(self._deleted_profiles)} profile(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.empty_trash_requested.emit()

    # === Selection handling ===

    def _on_header_section_clicked(self, section: int):
        """Handle header click."""
        pass  # HeaderCheckbox handles this

    def _on_header_checkbox_toggled(self, checked: bool):
        """Handle header checkbox toggle."""
        self._header_checked = checked
        self._toggle_all_checkboxes(checked)

    def _toggle_all_checkboxes(self, checked: bool):
        """Toggle all checkboxes."""
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

        if checked:
            self._selected_rows = list(range(self.table.rowCount()))
        else:
            self._selected_rows.clear()
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
        total = self.table.rowCount()
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
        return [
            self._deleted_profiles[row].get("id")
            for row in sorted(self._selected_rows)
            if row < len(self._deleted_profiles)
            and self._deleted_profiles[row].get("id")
        ]

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
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Permanently delete {len(ids)} profile(s)? This cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.permanent_delete_requested.emit(ids)
                self._toggle_all_checkboxes(False)

    # === Positioning ===

    def _position_header_checkbox(self):
        """Position header checkbox."""
        if not self._header_checkbox or not self.table:
            return
        Theme.position_header_checkbox(self.table, self._header_checkbox)

    def eventFilter(self, obj, event):
        """Handle events for toolbar positioning."""
        if obj == self._table_area and event.type() == QEvent.Type.Resize:
            self._position_toolbar()
        return super().eventFilter(obj, event)

    def _position_toolbar(self):
        """Position floating toolbar."""
        QTimer.singleShot(0, self._do_position_toolbar)

    def _do_position_toolbar(self):
        """Actually position toolbar."""
        if not self._table_area or not self.floating_toolbar:
            return
        if not self.floating_toolbar.isVisible():
            return

        self.floating_toolbar.adjustSize()
        toolbar_width = self.floating_toolbar.width()
        area_width = self._table_area.width()
        area_height = self._table_area.height()

        x = (area_width - toolbar_width) // 2
        y = area_height - self.floating_toolbar.height() - SPACING.lg

        self.floating_toolbar.move(x, y)
        self.floating_toolbar.raise_()

    def set_empty(self, is_empty: bool):
        """Toggle empty state visibility."""
        if is_empty:
            self.content_stack.setCurrentIndex(1)
        else:
            self.content_stack.setCurrentIndex(0)
