"""Modal overlay helpers for in-app dialogs."""

from PyQt6.QtCore import Qt, QEventLoop
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QInputDialog, QDialog


class ModalOverlay(QWidget):
    """Semi-transparent overlay used behind dialogs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modalOverlay")
        self.setStyleSheet("background-color: rgba(0, 0, 0, 160);")
        self.setVisible(False)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dialog: QDialog | None = None

    def set_dialog(self, dialog: QDialog) -> None:
        self.clear_dialog()
        self._dialog = dialog
        dialog.setParent(self)
        dialog.setWindowFlags(Qt.WindowType.Widget)
        self._layout.addWidget(dialog, alignment=Qt.AlignmentFlag.AlignCenter)

    def clear_dialog(self) -> None:
        if self._dialog is None:
            return
        self._layout.removeWidget(self._dialog)
        self._dialog.setParent(None)
        self._dialog = None

    def set_dimmed(self, dimmed: bool) -> None:
        opacity = "160" if dimmed else "0"
        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {opacity});")

    def show_overlay(self):
        self.setVisible(True)
        self.raise_()

    def hide_overlay(self):
        self.setVisible(False)


def _center_dialog(parent, dialog) -> None:
    if not parent:
        return
    dialog.adjustSize()
    width = dialog.width()
    height = dialog.height()
    x = max(0, (parent.width() - width) // 2)
    y = max(0, (parent.height() - height) // 2)
    dialog.move(x, y)


def _find_overlay(widget):
    current = widget
    while current is not None:
        overlay = getattr(current, "_modal_overlay", None)
        if overlay is not None:
            return overlay, current
        current = current.parentWidget()
    return None, widget.window() if widget else None


def exec_modal(parent, dialog, dim: bool = True) -> int:
    """Execute dialog with overlay.

    Falls back to normal exec if overlay unavailable.
    """
    overlay, window = _find_overlay(parent)

    if overlay is None or window is None:
        return dialog.exec()

    overlay.setGeometry(window.rect())
    overlay.set_dimmed(dim)
    overlay.set_dialog(dialog)
    overlay.show_overlay()

    loop = QEventLoop()
    dialog.finished.connect(lambda code: (setattr(dialog, "_result_code", code), loop.quit()))
    dialog.show()
    loop.exec()
    result_code = getattr(dialog, "_result_code", dialog.result())

    overlay.clear_dialog()
    overlay.hide_overlay()
    return result_code


def confirm_dialog(
    parent,
    title: str,
    text: str,
    icon=QMessageBox.Icon.Warning,
    default=QMessageBox.StandardButton.No,
    dim: bool = True,
) -> bool:
    """Show yes/no confirmation dialog with overlay."""
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    box.setDefaultButton(default)
    return exec_modal(parent, box, dim=dim) == QMessageBox.StandardButton.Yes


def info_dialog(parent, title: str, text: str, dim: bool = True) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Information)
    exec_modal(parent, box, dim=dim)


def error_dialog(parent, title: str, text: str, dim: bool = True) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Critical)
    exec_modal(parent, box, dim=dim)


def warning_dialog(parent, title: str, text: str, dim: bool = True) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Warning)
    exec_modal(parent, box, dim=dim)


def get_text_dialog(parent, title: str, label: str, value: str = ""):
    """Show text input dialog with overlay."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextValue(value)
    ok = exec_modal(parent, dialog, dim=False) == QInputDialog.DialogCode.Accepted
    return dialog.textValue(), ok


def get_item_dialog(
    parent,
    title: str,
    label: str,
    items: list[str],
    current: int = 0,
    editable: bool = False,
):
    """Show item selection dialog with overlay."""
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setComboBoxItems(items)
    dialog.setComboBoxEditable(editable)
    if 0 <= current < len(items):
        dialog.setTextValue(items[current])
    ok = exec_modal(parent, dialog, dim=False) == QInputDialog.DialogCode.Accepted
    return dialog.textValue(), ok
