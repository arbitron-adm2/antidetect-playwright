"""ComboBox helpers: searchable dropdown behavior."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QCompleter


def make_combobox_searchable(combo: QComboBox, placeholder: str) -> None:
    """Turn a QComboBox into a searchable dropdown.

    Implementation uses editable combo + completer filtering.
    It does NOT allow inserting new values.
    """

    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

    line_edit = combo.lineEdit()
    if line_edit is None:
        return

    line_edit.setPlaceholderText(placeholder)

    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.setCompleter(completer)
