"""Selectable table with checkboxes for batch operations."""

from PyQt6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
    QCheckBox,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ..theme import Theme, COLORS


class CheckboxWidget(QWidget):
    """Centered checkbox widget for table cells."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Remove all padding for checkbox column
        self.setContentsMargins(0, 0, 0, 0)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet(
            f"""
            QCheckBox {{
                spacing: 0px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS.text_muted};
                border-radius: 4px;
                background: {COLORS.bg_tertiary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS.accent};
                background: {COLORS.bg_hover};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS.accent};
                border-color: {COLORS.accent};
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }}
        """
        )
        self.checkbox.toggled.connect(self.toggled.emit)
        layout.addWidget(self.checkbox)
        layout.addStretch()

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)


class HeaderCheckbox(QWidget):
    """Header checkbox for select all."""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Match table header background
        self.setAutoFillBackground(True)
        self.setStyleSheet(f"background: {COLORS.bg_tertiary};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )

        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet(
            f"""
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {COLORS.text_muted};
                border-radius: 4px;
                background: {COLORS.bg_tertiary};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS.accent};
                background: {COLORS.bg_hover};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS.accent};
                border-color: {COLORS.accent};
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }}
            QCheckBox::indicator:indeterminate {{
                background-color: {COLORS.accent};
                border-color: {COLORS.accent};
            }}
        """
        )
        self.checkbox.toggled.connect(self.toggled.emit)
        layout.addWidget(self.checkbox)

    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)

    def setTristate(self, tristate: bool):
        self.checkbox.setTristate(tristate)

    def setCheckState(self, state: Qt.CheckState):
        self.checkbox.setCheckState(state)


class SelectableTable(QTableWidget):
    """Table with checkbox column for selection.

    Emits selection_changed signal when selection changes.
    First column (index 0) is always the checkbox column.
    """

    selection_changed = pyqtSignal(list)  # List of selected row indices

    def __init__(self, parent=None):
        super().__init__(parent)
        self._header_checkbox = None
        self._updating_selection = False

    def setup_with_columns(self, columns: list[str]):
        """Setup table with checkbox + given columns.

        Args:
            columns: List of column headers (checkbox will be prepended)
        """
        # Add checkbox column first
        all_columns = [""] + columns
        self.setColumnCount(len(all_columns))
        self.setHorizontalHeaderLabels(all_columns)

        # Setup header checkbox
        self._header_checkbox = HeaderCheckbox()
        self._header_checkbox.toggled.connect(self._on_header_toggled)
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 40)
        self.setCellWidget(
            -1, 0, self._header_checkbox
        )  # Won't work - need custom header

        # Apply unified styling
        Theme.setup_table(self)

    def add_checkbox_to_row(self, row: int):
        """Add checkbox widget to row's first column."""
        checkbox = CheckboxWidget()
        checkbox.toggled.connect(lambda checked: self._on_row_toggled(row, checked))
        self.setCellWidget(row, 0, checkbox)

    def get_selected_rows(self) -> list[int]:
        """Get list of selected row indices."""
        selected = []
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget) and widget.isChecked():
                selected.append(row)
        return selected

    def select_all(self):
        """Select all rows."""
        self._updating_selection = True
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.setChecked(True)
        self._updating_selection = False
        self._emit_selection_changed()

    def deselect_all(self):
        """Deselect all rows."""
        self._updating_selection = True
        for row in range(self.rowCount()):
            widget = self.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.setChecked(False)
        self._updating_selection = False
        self._emit_selection_changed()

    def _on_header_toggled(self, checked: bool):
        """Handle header checkbox toggle."""
        if checked:
            self.select_all()
        else:
            self.deselect_all()

    def _on_row_toggled(self, row: int, checked: bool):
        """Handle row checkbox toggle."""
        if not self._updating_selection:
            self._emit_selection_changed()

    def _emit_selection_changed(self):
        """Emit selection changed signal."""
        selected = self.get_selected_rows()
        self.selection_changed.emit(selected)

    def get_row_data(self, row: int, data_column: int = 1) -> str | None:
        """Get data from specific row and column.

        Args:
            row: Row index
            data_column: Column index (0 is checkbox, so usually 1+)
        """
        item = self.item(row, data_column)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
