"""Modern popup system - inline modals instead of separate windows."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsOpacityEffect,
    QFrame,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QPainter, QColor

from .styles import COLORS


class PopupOverlay(QWidget):
    """Semi-transparent overlay that covers the main window."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet(
            f"background-color: rgba(0, 0, 0, 0.5);"  # Semi-transparent black
        )

    def mousePressEvent(self, event):
        """Click outside popup to close."""
        self.clicked.emit()
        event.accept()


class PopupContainer(QFrame):
    """Container for popup content with rounded corners."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PopupContainer")
        
        # Set size policy to allow container to grow based on content
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        self.setStyleSheet(
            f"""
            #PopupContainer {{
                background-color: {COLORS['bg_secondary']};
                border: 2px solid {COLORS['border']};
                border-radius: 12px;
            }}
        """
        )
        # Don't use drop shadow - causes QPainter issues
        # Instead rely on overlay darkening for depth perception


class Popup(QWidget):
    """Base popup widget - shows centered over parent window.
    
    Usage:
        popup = Popup(parent_window)
        popup.set_content(your_widget)
        popup.show_animated()
    """

    closed = pyqtSignal(bool)  # True if accepted, False if rejected

    def __init__(self, parent=None, close_on_overlay_click=True):
        super().__init__(parent)
        self._close_on_overlay = close_on_overlay_click
        self._result = False
        
        # Fill parent
        self.setGeometry(parent.rect() if parent else self.geometry())
        
        # Create overlay
        self._overlay = PopupOverlay(self)
        self._overlay.setGeometry(self.rect())
        if self._close_on_overlay:
            self._overlay.clicked.connect(self.reject)
        
        # Create container for content
        self._container = PopupContainer(self)
        
        # Layout for container - IMPORTANT: proper margins
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 0, 0, 0)  # No extra margins - content has its own
        self._layout.setSpacing(0)  # No spacing - content controls spacing
        
        # Initially hidden
        self.hide()
        
        # Animation
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)

    def set_content(self, widget: QWidget):
        """Set popup content widget."""
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add widget with stretch to fill available space
        self._layout.addWidget(widget, 1)  # stretch=1
        
        # Force layout update
        widget.adjustSize()
        self._container.adjustSize()
        self._layout.activate()
        
        # Center in parent
        self._center_container()

    def _center_container(self):
        """Center container in popup."""
        parent_rect = self.rect()
        
        # Force layout to recalculate sizes
        if self._container.layout():
            self._container.layout().activate()
            
        # Get the main widget inside container (the one with actual content)
        main_widget = None
        if self._container.layout() and self._container.layout().count() > 0:
            item = self._container.layout().itemAt(0)
            if item and item.widget():
                main_widget = item.widget()
        
        if main_widget:
            # Use main widget size hint - it knows its content
            main_widget.adjustSize()
            main_size = main_widget.sizeHint()
            main_min_size = main_widget.minimumSizeHint()
            
            # Use the larger of sizeHint, minimumSizeHint, and minimumWidth/Height
            content_width = max(
                main_size.width(),
                main_min_size.width(),
                main_widget.minimumWidth() if main_widget.minimumWidth() > 0 else 0
            )
            content_height = max(
                main_size.height(),
                main_min_size.height(),
                main_widget.minimumHeight() if main_widget.minimumHeight() > 0 else 0
            )
        else:
            # Fallback to container size
            content_size = self._container.sizeHint()
            content_width = content_size.width()
            content_height = content_size.height()
        
        # Add some padding for borders and margins
        content_width += 10  # Border + shadow padding
        content_height += 10
        
        # Limit to 90% of parent width/height with some padding
        max_width = int(parent_rect.width() * 0.9)
        max_height = int(parent_rect.height() * 0.9)
        
        # Use content size but don't exceed max
        width = min(content_width, max_width)
        height = min(content_height, max_height)
        
        # Ensure minimum size for usability
        width = max(width, 450)  # Increased from 400 to prevent horizontal clipping
        height = max(height, 200)
        
        x = (parent_rect.width() - width) // 2
        y = (parent_rect.height() - height) // 2
        
        self._container.setGeometry(x, y, width, height)

    def resizeEvent(self, event):
        """Resize overlay and recenter container."""
        super().resizeEvent(event)
        self._overlay.setGeometry(self.rect())
        self._center_container()

    def show_animated(self):
        """Show popup with fade-in animation."""
        self.show()
        self.raise_()
        
        # Make sure container and overlay are visible
        self._overlay.show()
        self._overlay.raise_()
        self._container.show()
        self._container.raise_()
        
        # Fade in animation
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim.start()
        
        # Store animation to prevent garbage collection
        self._anim = anim

    def close_animated(self):
        """Close popup with fade-out animation."""
        anim = QPropertyAnimation(self._opacity, b"opacity")
        anim.setDuration(150)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)
        anim.finished.connect(self.hide)
        anim.finished.connect(lambda: self.closed.emit(self._result))
        anim.start()
        
        self._anim = anim

    def accept(self):
        """Accept and close popup."""
        self._result = True
        self.close_animated()

    def reject(self):
        """Reject and close popup."""
        self._result = False
        self.close_animated()

    def exec(self) -> bool:
        """Show popup modally and return result.
        
        Returns:
            True if accepted, False if rejected
        """
        from PyQt6.QtCore import QEventLoop
        
        self._result = False
        loop = QEventLoop()
        
        def on_closed(result):
            self._result = result
            loop.quit()
        
        self.closed.connect(on_closed)
        self.show_animated()
        loop.exec()
        
        return self._result


class PopupDialog(Popup):
    """Popup with title, content area, and action buttons.
    
    Replaces QDialog with an inline popup.
    """

    def __init__(self, parent=None, title="", close_on_overlay=True):
        super().__init__(parent, close_on_overlay)
        self._title = title
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI structure."""
        # Main widget
        main = QWidget()
        main.setMinimumWidth(500)  # Minimum popup width
        layout = QVBoxLayout(main)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Title
        if self._title:
            title_layout = QHBoxLayout()
            title_label = QLabel(self._title)
            title_label.setStyleSheet(
                f"""
                font-size: 18px;
                font-weight: 600;
                color: {COLORS['text_primary']};
            """
            )
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            
            # Close button
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(32, 32)
            close_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    border-radius: 16px;
                    color: {COLORS['text_muted']};
                    font-size: 20px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_hover']};
                    color: {COLORS['text_primary']};
                }}
            """
            )
            close_btn.clicked.connect(self.reject)
            title_layout.addWidget(close_btn)
            
            layout.addLayout(title_layout)
            
            # Divider
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setStyleSheet(f"background-color: {COLORS['border']};")
            divider.setFixedHeight(1)
            layout.addWidget(divider)
        
        # Content area (will be filled by set_dialog_content)
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(12)
        layout.addLayout(self._content_layout)  # Content should determine its own size
        
        # Button area
        self._button_layout = QHBoxLayout()
        self._button_layout.setSpacing(8)
        layout.addLayout(self._button_layout)
        
        self.set_content(main)

    def set_dialog_content(self, widget: QWidget):
        """Set content between title and buttons."""
        # Clear existing content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add the content widget
        self._content_layout.addWidget(widget)
        
        # Force the widget and container to update their sizes
        widget.adjustSize()
        widget.updateGeometry()
        
        # Update the main widget that contains everything
        if self._container.layout():
            self._container.layout().activate()
        
        # Recenter container with new content
        self._center_container()

    def add_button(self, text: str, callback=None, primary=False) -> QPushButton:
        """Add button to bottom button area.
        
        Args:
            text: Button text
            callback: Optional callback (if None, closes dialog)
            primary: If True, styles as primary button
        
        Returns:
            The created button
        """
        btn = QPushButton(text)
        btn.setMinimumHeight(36)  # Better click target
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if primary:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_hover']};
                }}
                QPushButton:pressed {{
                    background-color: #4338ca;
                }}
            """
            )
        else:
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {COLORS['bg_tertiary']};
                    color: {COLORS['text_primary']};
                    border: 1px solid {COLORS['border']};
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['bg_hover']};
                    border-color: {COLORS['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['bg_secondary']};
                }}
            """
            )
        
        if callback:
            btn.clicked.connect(callback)
        else:
            btn.clicked.connect(self.reject)
        
        self._button_layout.addWidget(btn)
        
        # Recalculate container size after adding buttons
        self._center_container()
        
        return btn

    def add_spacer(self):
        """Add stretch spacer to button layout (push buttons to right)."""
        self._button_layout.addStretch()


def show_popup_dialog(parent, title: str, content_widget: QWidget, 
                      buttons=None) -> bool:
    """Helper to quickly show a popup dialog.
    
    Args:
        parent: Parent window
        title: Dialog title
        content_widget: Content widget
        buttons: List of (text, callback, is_primary) tuples
                 Default: [("Cancel", None, False), ("OK", None, True)]
    
    Returns:
        True if accepted, False otherwise
    """
    dialog = PopupDialog(parent, title)
    dialog.set_dialog_content(content_widget)
    
    if buttons is None:
        buttons = [("Cancel", None, False), ("OK", None, True)]
    
    dialog.add_spacer()
    for text, callback, primary in buttons:
        if callback:
            dialog.add_button(text, callback, primary)
        elif primary:
            dialog.add_button(text, dialog.accept, primary)
        else:
            dialog.add_button(text, dialog.reject, primary)
    
    return dialog.exec()
