"""Modal popup helpers - modern inline popups instead of QMessageBox."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox
from PyQt6.QtCore import Qt

from .popup import PopupDialog
from .styles import COLORS


def confirm_dialog(
    parent,
    title: str,
    text: str,
    icon=None,  # Ignored, kept for compatibility
    default=None,  # Ignored, kept for compatibility
    dim: bool = True,  # Ignored, kept for compatibility
) -> bool:
    """Show yes/no confirmation popup.
    
    Args:
        parent: Parent widget
        title: Popup title
        text: Confirmation message
        icon: Ignored (for compatibility)
        default: Ignored (for compatibility)
        dim: Ignored (for compatibility)
    
    Returns:
        True if confirmed, False otherwise
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Message
    message = QLabel(text)
    message.setWordWrap(True)
    message.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px;")
    layout.addWidget(message)
    
    # Create popup
    popup = PopupDialog(parent, f"⚠️ {title}")
    popup.set_dialog_content(content)
    
    # Buttons
    popup.add_spacer()
    popup.add_button("No", popup.reject, False)
    popup.add_button("Yes", popup.accept, True)
    
    return popup.exec()


def info_dialog(parent, title: str, text: str, dim: bool = True) -> None:
    """Show information popup.
    
    Args:
        parent: Parent widget
        title: Popup title
        text: Information message
        dim: Ignored (for compatibility)
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Message
    message = QLabel(text)
    message.setWordWrap(True)
    message.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px;")
    layout.addWidget(message)
    
    # Create popup
    popup = PopupDialog(parent, f"ℹ️ {title}")
    popup.set_dialog_content(content)
    
    # Button
    popup.add_spacer()
    popup.add_button("OK", popup.accept, True)
    
    popup.exec()


def error_dialog(parent, title: str, text: str, dim: bool = True) -> None:
    """Show error popup.
    
    Args:
        parent: Parent widget
        title: Popup title
        text: Error message
        dim: Ignored (for compatibility)
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Message
    message = QLabel(text)
    message.setWordWrap(True)
    message.setStyleSheet(f"color: {COLORS['error']}; font-size: 14px; font-weight: 600;")
    layout.addWidget(message)
    
    # Create popup
    popup = PopupDialog(parent, f"❌ {title}")
    popup.set_dialog_content(content)
    
    # Button
    popup.add_spacer()
    popup.add_button("OK", popup.accept, True)
    
    popup.exec()


def warning_dialog(parent, title: str, text: str, dim: bool = True) -> None:
    """Show warning popup.
    
    Args:
        parent: Parent widget
        title: Popup title
        text: Warning message
        dim: Ignored (for compatibility)
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Message
    message = QLabel(text)
    message.setWordWrap(True)
    message.setStyleSheet(f"color: {COLORS['warning']}; font-size: 14px; font-weight: 600;")
    layout.addWidget(message)
    
    # Create popup
    popup = PopupDialog(parent, f"⚠️ {title}")
    popup.set_dialog_content(content)
    
    # Button
    popup.add_spacer()
    popup.add_button("OK", popup.accept, True)
    
    popup.exec()


def get_text_dialog(parent, title: str, label: str, value: str = "") -> tuple[str, bool]:
    """Show text input popup.
    
    Args:
        parent: Parent widget
        title: Popup title
        label: Input label
        value: Default value
    
    Returns:
        Tuple of (text, ok) where ok is True if accepted
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Label
    label_widget = QLabel(label)
    label_widget.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px;")
    layout.addWidget(label_widget)
    
    # Input
    text_input = QLineEdit()
    text_input.setText(value)
    text_input.setPlaceholderText("Enter text...")
    layout.addWidget(text_input)
    
    # Create popup
    popup = PopupDialog(parent, title)
    popup.set_dialog_content(content)
    
    # Result storage
    result_text = value
    
    def on_accept():
        nonlocal result_text
        result_text = text_input.text()
        popup.accept()
    
    # Enter key accepts
    text_input.returnPressed.connect(on_accept)
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("OK", on_accept, True)
    
    ok = popup.exec()
    return (result_text, ok)


def get_item_dialog(
    parent,
    title: str,
    label: str,
    items: list[str],
    current: int = 0,
    editable: bool = False,
) -> tuple[str, bool]:
    """Show item selection popup.
    
    Args:
        parent: Parent widget
        title: Popup title
        label: Selection label
        items: List of items to choose from
        current: Index of current item
        editable: Whether combo box is editable
    
    Returns:
        Tuple of (selected_item, ok) where ok is True if accepted
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Label
    label_widget = QLabel(label)
    label_widget.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px;")
    layout.addWidget(label_widget)
    
    # Combo box
    combo = QComboBox()
    combo.addItems(items)
    combo.setEditable(editable)
    if 0 <= current < len(items):
        combo.setCurrentIndex(current)
    layout.addWidget(combo)
    
    # Create popup
    popup = PopupDialog(parent, title)
    popup.set_dialog_content(content)
    
    # Result storage
    result_item = items[current] if 0 <= current < len(items) else ""
    
    def on_accept():
        nonlocal result_item
        result_item = combo.currentText()
        popup.accept()
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("OK", on_accept, True)
    
    ok = popup.exec()
    return (result_item, ok)


# Legacy compatibility - keep old ModalOverlay for backward compatibility
from PyQt6.QtCore import QEventLoop
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QDialog


class ModalOverlay(QWidget):
    """Legacy modal overlay - deprecated, use popup.py instead."""

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


def exec_modal(parent, dialog, dim: bool = True) -> int:
    """Legacy exec_modal - deprecated, use PopupDialog instead."""
    # Fallback to regular exec
    return dialog.exec()
