"""Inline, non-modal alert widget with TTL auto-hide."""

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QWidget

from ..theme import Theme


@dataclass(frozen=True, slots=True)
class InlineAlertContent:
    title: str
    message: str


class InlineAlert(QFrame):
    """Red bordered inline alert that auto-hides after configured TTL."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.setObjectName("inlineAlert")
        self.setVisible(False)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self._title = QLabel("")
        self._title.setObjectName("inlineAlertTitle")
        self._title.setWordWrap(False)

        self._message = QLabel("")
        self._message.setObjectName("inlineAlertMessage")
        self._message.setWordWrap(True)

        layout.addWidget(self._title)
        layout.addWidget(self._message, 1)

    def show_error(self, title: str, message: str) -> None:
        self._title.setText(title.strip())
        self._message.setText(message.strip())
        self.setStyleSheet("")  # Reset to default error style
        self._start_ttl_and_show()

    def show_success(self, title: str, message: str) -> None:
        self._title.setText(title.strip())
        self._message.setText(message.strip())
        # Apply success style (green border)
        self.setStyleSheet(
            """
            #inlineAlert {
                border: 1px solid #22c55e;
                border-radius: 4px;
                background: rgba(34, 197, 94, 0.1);
            }
            #inlineAlertTitle {
                color: #22c55e;
                font-weight: 600;
            }
            #inlineAlertMessage {
                color: #22c55e;
            }
            """
        )
        self._start_ttl_and_show()

    def hide(self) -> None:
        self._timer.stop()
        super().hide()

    def _start_ttl_and_show(self) -> None:
        ttl_ms = self._get_ttl_ms()
        self.setVisible(True)
        self.raise_()
        self._timer.start(ttl_ms)

    @staticmethod
    def _get_ttl_ms() -> int:
        app = QApplication.instance()
        if app is None:
            raise RuntimeError("QApplication instance is required")

        ttl = app.property("inline_alert_ttl_ms")
        if ttl is None:
            raise RuntimeError(
                "Missing required QApplication property: inline_alert_ttl_ms"
            )

        try:
            ttl_int = int(ttl)
        except (TypeError, ValueError) as e:
            raise RuntimeError(f"Invalid inline_alert_ttl_ms value: {ttl!r}") from e

        if ttl_int <= 0:
            raise RuntimeError("inline_alert_ttl_ms must be > 0")

        return ttl_int
