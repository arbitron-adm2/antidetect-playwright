"""Proxy management page with full table view."""

import asyncio
import logging
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QLineEdit,
    QMessageBox,
    QMenu,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer

from ..theme import Theme, COLORS, TYPOGRAPHY, SPACING
from ..icons import get_icon
from ..models import ProxyConfig
from ..proxy_utils import parse_proxy_list, ping_proxy, detect_proxy_geo
from ..components import FloatingToolbar, CheckboxWidget, HeaderCheckbox, InlineAlert


class ProxyPage(QWidget):
    """Proxy management page with table."""

    proxy_pool_changed = pyqtSignal(list)

    # Batch operation signals
    batch_ping = pyqtSignal(list)  # List of proxy indices
    batch_delete = pyqtSignal(list)
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proxies: list[ProxyConfig] = []
        self._selected_rows = []
        self._header_checked = False
        self._table_area: QWidget | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup page UI."""
        self.setObjectName("proxyPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xl, SPACING.xl, SPACING.xl, SPACING.xl)
        layout.setSpacing(SPACING.lg)

        # Header
        header_layout = QHBoxLayout()

        header = QLabel("Proxy Pool")
        header.setProperty("class", "heading")
        header_layout.addWidget(header)

        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Description
        desc = QLabel("Manage proxy pool for quick rotation and auto-assignment.")
        desc.setProperty("class", "secondary")
        layout.addWidget(desc)

        self._alert = InlineAlert(self)
        layout.addWidget(self._alert)

        # Table area with overlay toolbar
        table_area = QWidget()
        table_area_layout = QVBoxLayout(table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Proxy table
        self.table = self._create_table()
        table_container = Theme.create_table_container(self.table)
        table_area_layout.addWidget(table_container, 1)

        # Header checkbox overlay (positioned over first header column)
        self._header_checkbox = HeaderCheckbox()
        self._header_checkbox.toggled.connect(self._on_header_checkbox_toggled)
        self._header_checkbox.setParent(self.table)
        self._header_checkbox.setFixedSize(24, 24)
        self._position_header_checkbox()
        self._header_checkbox.raise_()
        self._header_checkbox.show()

        # Reposition on resize
        self.table.horizontalHeader().sectionResized.connect(
            lambda: self._position_header_checkbox()
        )

        # Floating toolbar (overlay at bottom center)
        self.floating_toolbar = FloatingToolbar("proxy")
        self.floating_toolbar.setParent(table_area)
        self.floating_toolbar.ping_clicked.connect(self._on_batch_ping)
        self.floating_toolbar.delete_clicked.connect(self._on_batch_delete)
        self.floating_toolbar.visibility_changed.connect(
            lambda visible: self._position_toolbar() if visible else None
        )

        # Store reference for positioning
        self._table_area = table_area
        table_area.installEventFilter(self)

        layout.addWidget(table_area, 1)

        # Add section
        add_frame = QFrame()
        add_frame.setObjectName("addProxyFrame")
        add_layout = QVBoxLayout(add_frame)
        add_layout.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        add_layout.setSpacing(SPACING.sm)

        add_label = QLabel("Add Proxies (one per line)")
        add_label.setProperty("class", "subheading")
        add_layout.addWidget(add_label)

        hint = QLabel("Format: host:port, host:port:user:pass, or socks5://host:port")
        hint.setProperty("class", "muted")
        add_layout.addWidget(hint)

        self.proxy_input = QTextEdit()
        self.proxy_input.setPlaceholderText(
            "185.123.45.67:8080\n"
            "proxy.example.com:3128:username:password\n"
            "socks5://192.168.1.1:1080"
        )
        self.proxy_input.setMaximumHeight(100)
        add_layout.addWidget(self.proxy_input)

        add_btn_layout = QHBoxLayout()
        self.proxy_input.textChanged.connect(lambda: self._clear_error(self.proxy_input))
        add_btn_layout.addStretch()

        add_btn = QPushButton(" Add Proxies")
        add_btn.setIcon(get_icon("plus", 14))
        add_btn.setIconSize(QSize(14, 14))
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self._add_proxies)
        add_btn_layout.addWidget(add_btn)

        add_layout.addLayout(add_btn_layout)

        layout.addWidget(add_frame)

    def _create_table(self) -> QTableWidget:
        """Create proxy table with checkbox column."""
        table = QTableWidget()
        table.setColumnCount(8)  # Checkbox + 7 columns
        table.setHorizontalHeaderLabels(
            ["", "Type", "Host", "Port", "Auth", "Country", "Ping", "Actions"]
        )

        # Unified table styling first
        Theme.setup_table(table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "fixed", 70),  # Type
                (2, "stretch", None),  # Host - fills space
                (3, "fixed", 70),  # Port
                (4, "fixed", 60),  # Auth
                (5, "fixed", 80),  # Country
                (6, "fixed", 80),  # Ping
                (7, "fixed", Theme.COL_ACTIONS_LG),  # Actions (menu + 3 buttons)
            ],
        )

        # Click on header column 0 toggles select all
        table.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)

        # Context menu (row-wide)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_context_menu)

        return table

    def _on_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        self._show_row_context_menu(row, self.table.mapToGlobal(pos))

    def _show_row_context_menu(self, row: int, global_pos):
        if row < 0 or row >= len(self.proxies):
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        edit_action.triggered.connect(lambda: self._edit_proxy(row))
        ping_action = menu.addAction("Ping")
        ping_action.triggered.connect(lambda: self._ping_proxy_clicked(row))
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_proxy(row))
        menu.exec(global_pos)

    def update_proxies(self, proxies: list[ProxyConfig]):
        """Update proxy list and refresh table."""
        self.proxies = list(proxies)
        self._refresh_table(preserve_selection=True)

    def _refresh_table(self, preserve_selection: bool = True):
        """Refresh proxy table."""
        previous_selected = set(self._selected_rows) if preserve_selection else set()
        self._selected_rows = []
        self.table.setRowCount(len(self.proxies))

        for row, proxy in enumerate(self.proxies):
            # Checkbox
            self.add_checkbox_to_row(row, checked=row in previous_selected)

            # Type
            type_item = QTableWidgetItem(proxy.proxy_type.value.upper())
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, type_item)

            # Host
            host_item = QTableWidgetItem(proxy.host)
            self.table.setItem(row, 2, host_item)

            # Port
            port_item = QTableWidgetItem(str(proxy.port))
            port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, port_item)

            # Auth
            auth_text = "Yes" if proxy.username else "No"
            auth_item = QTableWidgetItem(auth_text)
            auth_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, auth_item)

            # Country - SVG globe icon
            country_code = proxy.country_code.upper() if proxy.country_code else ""
            country_item = QTableWidgetItem(country_code)
            country_item.setIcon(get_icon("proxy", 14))
            country_item.setToolTip(country_code if country_code else "Unknown")
            country_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, country_item)

            # Ping
            if proxy.ping_ms > 0:
                ping_text = f"{proxy.ping_ms}ms"
            else:
                ping_text = "—"
            ping_item = QTableWidgetItem(ping_text)
            ping_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, ping_item)

            # Actions
            actions_widget = self._create_actions_widget(row)
            self.table.setCellWidget(row, 7, actions_widget)

        self._update_selection()
        self._update_header_state()

    def _create_actions_widget(self, row: int) -> QWidget:
        """Create actions widget for row."""
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

        menu_btn = QPushButton("⋯")
        menu_btn.setFixedSize(btn_size, btn_size)
        menu_btn.setProperty("class", "icon")
        menu_btn.setToolTip("Menu")
        menu_btn.clicked.connect(
            lambda checked=False, r=row, w=menu_btn: self._show_row_context_menu(
                r, w.mapToGlobal(w.rect().bottomLeft())
            )
        )
        layout.addWidget(menu_btn)

        # Edit button
        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", 14))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(btn_size, btn_size)
        edit_btn.setProperty("class", "icon")
        edit_btn.setToolTip("Edit")
        edit_btn.clicked.connect(lambda checked, r=row: self._edit_proxy(r))
        layout.addWidget(edit_btn)

        # Ping button
        ping_btn = QPushButton()
        ping_btn.setIcon(get_icon("ping", 14))
        ping_btn.setIconSize(QSize(14, 14))
        ping_btn.setFixedSize(btn_size, btn_size)
        ping_btn.setProperty("class", "icon")
        ping_btn.setToolTip("Ping")
        ping_btn.clicked.connect(lambda checked, r=row: self._ping_proxy_clicked(r))
        layout.addWidget(ping_btn)

        # Delete button
        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", 14))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(btn_size, btn_size)
        del_btn.setProperty("class", "icon")
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self._delete_proxy(row))
        layout.addWidget(del_btn)

        layout.addStretch()
        return widget

    def _add_proxies(self):
        """Add proxies from input."""
        text = self.proxy_input.toPlainText().strip()
        if not text:
            return

        new_proxies, errors = parse_proxy_list(text)
        if new_proxies:
            self.proxies.extend(new_proxies)
            self._refresh_table()
            self.proxy_input.clear()
            self.proxy_pool_changed.emit(self.proxies)

        if errors:
            self._set_error(self.proxy_input, True)
            self._alert.show_error("Parse Errors", f"{len(errors)} line(s) failed to parse.")

    def _delete_proxy(self, row: int):
        """Delete proxy at row."""
        if 0 <= row < len(self.proxies):
            del self.proxies[row]
            self._refresh_table()
            self.proxy_pool_changed.emit(self.proxies)

    def _edit_proxy(self, row: int):
        """Edit proxy at row."""
        if 0 <= row < len(self.proxies):
            proxy = self.proxies[row]
            current = proxy.host
            current += f":{proxy.port}"
            if proxy.username and proxy.password:
                current += f":{proxy.username}:{proxy.password}"

            from PyQt6.QtWidgets import QInputDialog

            new_value, ok = QInputDialog.getText(
                self,
                "Edit Proxy",
                "Format: host:port or host:port:user:pass",
                text=current,
            )
            if ok and new_value:
                parsed, errors = parse_proxy_list(new_value)
                if parsed:
                    self.proxies[row] = parsed[0]
                    self._refresh_table()
                    self.proxy_pool_changed.emit(self.proxies)
                if errors:
                    self._alert.show_error("Parse Errors", f"{len(errors)} line(s) failed to parse.")

    def _set_error(self, widget: QWidget, is_error: bool) -> None:
        widget.setProperty("error", "true" if is_error else "false")
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _clear_error(self, widget: QWidget) -> None:
        self._set_error(widget, False)
        self._alert.hide()

    def _ping_proxy_clicked(self, row: int):
        """Handle ping button click - wrapper for async call."""
        self._spawn_task(self._ping_proxy_async(row), context=f"ping_proxy(row={row})")

    async def _ping_proxy_async(self, row: int):
        """Ping single proxy (async implementation)."""
        if 0 <= row < len(self.proxies):
            proxy = self.proxies[row]
            ping_ms = await ping_proxy(proxy)
            if ping_ms > 0:
                proxy.ping_ms = ping_ms
                # Also detect geo if not set
                if not proxy.country_code:
                    geo = await detect_proxy_geo(proxy)
                    if geo:
                        proxy.country_code = geo.get("country_code", "")
                        proxy.country_name = geo.get("country_name", "")
            self._refresh_table()
            self.proxy_pool_changed.emit(self.proxies)

    def _ping_all_clicked(self):
        """Handle ping all button click - wrapper for async call."""
        self._spawn_task(self._ping_all_async(), context="ping_all_proxies")

    def _spawn_task(self, coro, context: str) -> None:
        """Run coroutine in the background and log exceptions."""
        logger = logging.getLogger(__name__)
        try:
            task = asyncio.create_task(coro)
        except RuntimeError as e:
            logger.warning("Cannot start task (%s): %s", context, e)
            return

        def _done(t: asyncio.Task) -> None:
            try:
                exc = t.exception()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.warning("Task exception retrieval failed (%s): %s", context, e)
                return
            if exc is not None:
                logger.exception("Background task failed (%s)", context, exc_info=exc)

        task.add_done_callback(_done)

    async def _ping_all_async(self):
        """Ping all proxies concurrently."""
        if not self.proxies:
            return

        async def ping_one(proxy: ProxyConfig) -> None:
            ping_ms = await ping_proxy(proxy)
            if ping_ms > 0:
                proxy.ping_ms = ping_ms
                if not proxy.country_code:
                    geo = await detect_proxy_geo(proxy)
                    if geo:
                        proxy.country_code = geo.get("country_code", "")
                        proxy.country_name = geo.get("country_name", "")

        # Ping all concurrently with limit
        tasks = [ping_one(p) for p in self.proxies]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._refresh_table()
        self.proxy_pool_changed.emit(self.proxies)

    def _clear_all(self):
        """Clear all proxies."""
        if not self.proxies:
            return

        reply = QMessageBox.question(
            self,
            "Clear Proxy Pool",
            "Remove all proxies from the pool?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.proxies.clear()
            self._refresh_table()
            self.proxy_pool_changed.emit(self.proxies)

    def get_proxies(self) -> list[ProxyConfig]:
        """Get current proxy list."""
        return self.proxies

    # --- Checkbox / Selection methods ---

    def add_checkbox_to_row(self, row: int, checked: bool = False) -> None:
        """Add checkbox widget to row."""
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
        if checked:
            checkbox.blockSignals(True)
            checkbox.setChecked(True)
            checkbox.blockSignals(False)
            self._selected_rows.append(row)
        self.table.setCellWidget(row, 0, checkbox)

    def _on_header_section_clicked(self, section: int) -> None:
        """Handle header section click - pass through (HeaderCheckbox handles toggle)."""
        pass  # HeaderCheckbox overlay handles this now

    def _on_header_checkbox_toggled(self, checked: bool) -> None:
        """Handle header checkbox toggle."""
        self._header_checked = checked
        self._toggle_all_checkboxes(checked)

    def _toggle_all_checkboxes(self, checked: bool) -> None:
        """Set all checkboxes to checked state."""
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
        self._update_header_state()

    def _on_row_checkbox_toggled(self, row: int, checked: bool) -> None:
        """Handle row checkbox toggle."""
        if checked:
            if row not in self._selected_rows:
                self._selected_rows.append(row)
        else:
            if row in self._selected_rows:
                self._selected_rows.remove(row)
        self._update_selection()
        self._update_header_state()

    def _update_header_state(self) -> None:
        """Update header checkbox state based on selections."""
        total = self.table.rowCount()
        if total > 0 and len(self._selected_rows) == total:
            self._header_checked = True
        else:
            self._header_checked = False

        # Sync HeaderCheckbox widget
        if hasattr(self, "_header_checkbox") and self._header_checkbox:
            self._header_checkbox.blockSignals(True)
            self._header_checkbox.setChecked(self._header_checked)
            self._header_checkbox.blockSignals(False)

    def _update_selection(self) -> None:
        """Update selection state and toolbar."""
        count = len(self._selected_rows)
        self.floating_toolbar.update_count(count)
        self.selection_changed.emit(count)

    def get_selected_proxy_indices(self) -> list[int]:
        """Get selected proxy row indices."""
        return sorted(self._selected_rows, reverse=True)

    def _deselect_all(self) -> None:
        """Deselect all rows."""
        self._toggle_all_checkboxes(False)

    def _on_batch_ping(self) -> None:
        """Handle batch ping button."""
        indices = self.get_selected_proxy_indices()
        if indices:
            self.batch_ping.emit(indices)

    def _on_batch_delete(self) -> None:
        """Handle batch delete button."""
        indices = self.get_selected_proxy_indices()
        if indices:
            self.batch_delete.emit(indices)

    # === Header checkbox positioning ===

    def _position_header_checkbox(self):
        """Position header checkbox over first column header."""
        if (
            not hasattr(self, "_header_checkbox")
            or not self._header_checkbox
            or not self.table
        ):
            return
        Theme.position_header_checkbox(self.table, self._header_checkbox)

    # === Toolbar positioning ===

    def eventFilter(self, obj, event):
        """Handle events for toolbar positioning."""
        if obj == self._table_area and event.type() == QEvent.Type.Resize:
            self._position_toolbar()
        return super().eventFilter(obj, event)

    def _position_toolbar(self):
        """Position floating toolbar at bottom center of table area."""
        if not self._table_area or not self.floating_toolbar:
            return

        # Defer positioning to ensure layout is complete
        QTimer.singleShot(0, self._do_position_toolbar)

    def _do_position_toolbar(self):
        """Actually position the toolbar."""
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
