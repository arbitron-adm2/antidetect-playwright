"""Table models for GUI views."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class SimpleTableModel(QAbstractTableModel):
    """Lightweight table model for simple row data."""

    def __init__(self, headers: list[str], parent=None):
        super().__init__(parent)
        self._headers = list(headers)
        self._rows: list[list[Any]] = []
        self._payloads: list[Any] = []
        self._alignments: dict[int, Qt.AlignmentFlag] = {}

    def set_rows(self, rows: list[list[Any]], payloads: list[Any] | None = None) -> None:
        """Replace table rows."""
        self.beginResetModel()
        self._rows = list(rows)
        if payloads is None:
            self._payloads = [None for _ in self._rows]
        else:
            self._payloads = list(payloads)
        self.endResetModel()

    def set_alignments(self, alignments: dict[int, Qt.AlignmentFlag]) -> None:
        """Set per-column text alignments."""
        self._alignments = dict(alignments)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._rows) or col >= len(self._headers):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            value = self._rows[row][col]
            if value is None:
                return ""
            return str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in self._alignments:
                return self._alignments[col]
        if role == Qt.ItemDataRole.UserRole:
            return self._payloads[row] if row < len(self._payloads) else None
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None

    def payload_at(self, row: int) -> Any:
        """Return payload object for a row."""
        if 0 <= row < len(self._payloads):
            return self._payloads[row]
        return None
