"""Tags, notes and statuses management page with tables."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QTabWidget,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer

from ..theme import Theme, COLORS, TYPOGRAPHY, SPACING
from ..icons import get_icon
from ..models import ProfileStatus
from ..components import FloatingToolbar, CheckboxWidget, HeaderCheckbox
from ..dialogs import StatusEditDialog


class TagsPage(QWidget):
    """Tags, notes and statuses management page."""

    tag_created = pyqtSignal(str)
    tag_deleted = pyqtSignal(str)
    tag_renamed = pyqtSignal(str, str)
    status_created = pyqtSignal(str, str)
    status_renamed = pyqtSignal(str, str, str)  # old_name, new_name, color
    note_template_created = pyqtSignal(str, str)

    # Batch signals
    batch_delete_tags = pyqtSignal(list)  # list of tag names
    batch_delete_statuses = pyqtSignal(list)  # list of status names
    batch_delete_templates = pyqtSignal(list)  # list of template names
    selection_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tags: list[str] = []
        self.statuses: list[tuple[str, str]] = []  # (name, color)
        self.note_templates: list[tuple[str, str]] = []  # (name, template)

        # Selection tracking per table
        self._selected_tags: list[int] = []
        self._selected_statuses: list[int] = []
        self._selected_templates: list[int] = []

        # Table areas for toolbar positioning
        self._tags_table_area: QWidget | None = None
        self._statuses_table_area: QWidget | None = None
        self._templates_table_area: QWidget | None = None

        self._setup_ui()
        self._refresh_statuses_table()

    def _setup_ui(self):
        """Setup page UI."""
        self.setObjectName("tagsPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.xl, SPACING.xl, SPACING.xl, SPACING.xl)
        layout.setSpacing(SPACING.lg)

        # Header
        header = QLabel("Labels Management")
        header.setProperty("class", "heading")
        layout.addWidget(header)

        desc = QLabel(
            "Create and manage tags, statuses, and note templates for profiles."
        )
        desc.setProperty("class", "secondary")
        layout.addWidget(desc)

        # Tab widget for Tags / Statuses / Notes
        self.tabs = QTabWidget()

        # Tags tab
        tags_tab = self._create_tags_tab()
        self.tabs.addTab(tags_tab, "Tags")

        # Statuses tab
        statuses_tab = self._create_statuses_tab()
        self.tabs.addTab(statuses_tab, "Statuses")

        # Note templates tab
        notes_tab = self._create_notes_tab()
        self.tabs.addTab(notes_tab, "Note Templates")

        layout.addWidget(self.tabs, 1)

    def _create_tags_tab(self) -> QWidget:
        """Create tags management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, SPACING.lg, 0, 0)
        layout.setSpacing(SPACING.md)

        # Add tag section
        add_layout = QHBoxLayout()

        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Tag name")
        self.tag_input.returnPressed.connect(self._add_tag)
        add_layout.addWidget(self.tag_input)

        add_btn = QPushButton(" Add Tag")
        add_btn.setIcon(get_icon("plus", 14))
        add_btn.setIconSize(QSize(14, 14))
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self._add_tag)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

        # Table area with overlay toolbar
        table_area = QWidget()
        table_area_layout = QVBoxLayout(table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Tags table with checkbox column
        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(4)  # Checkbox + 3
        self.tags_table.setHorizontalHeaderLabels(
            ["", "Tag Name", "Profiles", "Actions"]
        )

        # Unified table styling first
        Theme.setup_table(self.tags_table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            self.tags_table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "stretch", None),  # Name - fills space
                (2, "fixed", 80),  # Profiles
                (3, "fixed", Theme.COL_ACTIONS_MD),  # Actions
            ],
        )

        # Header section click for select all
        self.tags_table.horizontalHeader().sectionClicked.connect(
            self._on_tags_header_clicked
        )
        self._tags_header_checked = False

        # Wrap in container with rounded corners
        table_container = Theme.create_table_container(self.tags_table)
        table_area_layout.addWidget(table_container, 1)

        # Header checkbox overlay (positioned over first header column)
        self._tags_header_checkbox = HeaderCheckbox()
        self._tags_header_checkbox.toggled.connect(
            self._on_tags_header_checkbox_toggled
        )
        self._tags_header_checkbox.setParent(self.tags_table)
        self._tags_header_checkbox.setFixedSize(24, 24)
        self._position_tags_header_checkbox()
        self._tags_header_checkbox.raise_()
        self._tags_header_checkbox.show()

        # Reposition on resize
        self.tags_table.horizontalHeader().sectionResized.connect(
            lambda: self._position_tags_header_checkbox()
        )

        # Floating toolbar (overlay at bottom center)
        self.tags_toolbar = FloatingToolbar("tags")
        self.tags_toolbar.setParent(table_area)
        self.tags_toolbar.delete_clicked.connect(self._on_batch_delete_tags)
        self.tags_toolbar.visibility_changed.connect(
            lambda visible: self._position_tags_toolbar() if visible else None
        )

        # Store reference for positioning
        self._tags_table_area = table_area
        table_area.installEventFilter(self)

        layout.addWidget(table_area, 1)

        return widget

    def _create_statuses_tab(self) -> QWidget:
        """Create statuses management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, SPACING.lg, 0, 0)
        layout.setSpacing(SPACING.md)

        # Add status section
        add_layout = QHBoxLayout()

        self.status_name_input = QLineEdit()
        self.status_name_input.setPlaceholderText("Status name")
        add_layout.addWidget(self.status_name_input)

        self.status_color_combo = QComboBox()
        self.status_color_combo.addItems(["Green", "Yellow", "Red", "Blue", "Gray"])
        self.status_color_combo.setFixedWidth(100)
        add_layout.addWidget(self.status_color_combo)

        add_btn = QPushButton(" Add Status")
        add_btn.setIcon(get_icon("plus", 14))
        add_btn.setIconSize(QSize(14, 14))
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self._add_status)
        add_layout.addWidget(add_btn)

        layout.addLayout(add_layout)

        # Table area with overlay toolbar
        table_area = QWidget()
        table_area_layout = QVBoxLayout(table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Statuses table with checkbox column
        self.statuses_table = QTableWidget()
        self.statuses_table.setColumnCount(4)  # Checkbox + 3
        self.statuses_table.setHorizontalHeaderLabels(
            ["", "Status Name", "Color", "Actions"]
        )

        # Unified table styling first
        Theme.setup_table(self.statuses_table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            self.statuses_table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "stretch", None),  # Name - fills space
                (2, "fixed", Theme.COL_STATUS),  # Color
                (3, "fixed", Theme.COL_ACTIONS_MD),  # Actions
            ],
        )

        # Header section click for select all
        self.statuses_table.horizontalHeader().sectionClicked.connect(
            self._on_statuses_header_clicked
        )
        self._statuses_header_checked = False

        # Wrap in container with rounded corners
        table_container = Theme.create_table_container(self.statuses_table)
        table_area_layout.addWidget(table_container, 1)

        # Header checkbox overlay (positioned over first header column)
        self._statuses_header_checkbox = HeaderCheckbox()
        self._statuses_header_checkbox.toggled.connect(
            self._on_statuses_header_checkbox_toggled
        )
        self._statuses_header_checkbox.setParent(self.statuses_table)
        self._statuses_header_checkbox.setFixedSize(24, 24)
        self._position_statuses_header_checkbox()
        self._statuses_header_checkbox.raise_()
        self._statuses_header_checkbox.show()

        # Reposition on resize
        self.statuses_table.horizontalHeader().sectionResized.connect(
            lambda: self._position_statuses_header_checkbox()
        )

        # Floating toolbar (overlay at bottom center)
        self.statuses_toolbar = FloatingToolbar("tags")
        self.statuses_toolbar.setParent(table_area)
        self.statuses_toolbar.delete_clicked.connect(self._on_batch_delete_statuses)
        self.statuses_toolbar.visibility_changed.connect(
            lambda visible: self._position_statuses_toolbar() if visible else None
        )

        # Store reference for positioning
        self._statuses_table_area = table_area
        table_area.installEventFilter(self)

        layout.addWidget(table_area, 1)

        # Default statuses info
        info = QLabel("Default statuses: Running, Stopped, Error (cannot be deleted)")
        info.setProperty("class", "muted")
        layout.addWidget(info)

        return widget

    def _create_notes_tab(self) -> QWidget:
        """Create note templates tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, SPACING.lg, 0, 0)
        layout.setSpacing(SPACING.md)

        # Add template section
        add_layout = QVBoxLayout()

        name_layout = QHBoxLayout()
        name_label = QLabel("Template Name:")
        name_label.setFixedWidth(120)
        name_layout.addWidget(name_label)

        self.template_name_input = QLineEdit()
        self.template_name_input.setPlaceholderText(
            "e.g., Account Info, Login Details..."
        )
        name_layout.addWidget(self.template_name_input)
        add_layout.addLayout(name_layout)

        self.template_content_input = QTextEdit()
        self.template_content_input.setPlaceholderText(
            "Template content with placeholders:\n"
            "Email: {email}\n"
            "Password: {password}\n"
            "Created: {date}"
        )
        self.template_content_input.setMaximumHeight(100)
        add_layout.addWidget(self.template_content_input)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        add_btn = QPushButton(" Add Template")
        add_btn.setIcon(get_icon("plus", 14))
        add_btn.setIconSize(QSize(14, 14))
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self._add_note_template)
        btn_layout.addWidget(add_btn)

        add_layout.addLayout(btn_layout)
        layout.addLayout(add_layout)

        # Table area with overlay toolbar
        table_area = QWidget()
        table_area_layout = QVBoxLayout(table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Templates table with checkbox column
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(4)  # Checkbox + 3
        self.templates_table.setHorizontalHeaderLabels(
            ["", "Template Name", "Preview", "Actions"]
        )

        # Unified table styling first
        Theme.setup_table(self.templates_table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            self.templates_table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "fixed", 150),  # Name
                (2, "stretch", None),  # Preview - fills space
                (3, "fixed", Theme.COL_ACTIONS_MD),  # Actions
            ],
        )

        # Header section click for select all
        self.templates_table.horizontalHeader().sectionClicked.connect(
            self._on_templates_header_clicked
        )
        self._templates_header_checked = False

        # Wrap in container with rounded corners
        table_container = Theme.create_table_container(self.templates_table)
        table_area_layout.addWidget(table_container, 1)

        # Header checkbox overlay (positioned over first header column)
        self._templates_header_checkbox = HeaderCheckbox()
        self._templates_header_checkbox.toggled.connect(
            self._on_templates_header_checkbox_toggled
        )
        self._templates_header_checkbox.setParent(self.templates_table)
        self._templates_header_checkbox.setFixedSize(24, 24)
        self._position_templates_header_checkbox()
        self._templates_header_checkbox.raise_()
        self._templates_header_checkbox.show()

        # Reposition on resize
        self.templates_table.horizontalHeader().sectionResized.connect(
            lambda: self._position_templates_header_checkbox()
        )

        # Floating toolbar (overlay at bottom center)
        self.templates_toolbar = FloatingToolbar("tags")
        self.templates_toolbar.setParent(table_area)
        self.templates_toolbar.delete_clicked.connect(self._on_batch_delete_templates)
        self.templates_toolbar.visibility_changed.connect(
            lambda visible: self._position_templates_toolbar() if visible else None
        )

        # Store reference for positioning
        self._templates_table_area = table_area
        table_area.installEventFilter(self)

        layout.addWidget(table_area, 1)

        return widget

    def update_tags(self, tags: list[str], tag_counts: dict[str, int] | None = None):
        """Update tags table."""
        self.tags = list(tags)
        self._selected_tags.clear()
        self.tags_toolbar.update_count(0)
        tag_counts = tag_counts or {}

        self.tags_table.setRowCount(len(self.tags))

        for row, tag in enumerate(self.tags):
            # Checkbox
            self._add_checkbox_to_tags_table(row)

            # Name
            name_item = QTableWidgetItem(tag)
            self.tags_table.setItem(row, 1, name_item)

            # Count
            count = tag_counts.get(tag, 0)
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_table.setItem(row, 2, count_item)

            # Actions
            actions = self._create_tag_actions(row, tag)
            self.tags_table.setCellWidget(row, 3, actions)

    def update_statuses(self, statuses: list[tuple[str, str]]):
        """Update statuses table."""
        self.statuses = list(statuses)
        self._refresh_statuses_table()

    def update_note_templates(self, templates: list[tuple[str, str]]):
        """Update note templates table."""
        self.note_templates = list(templates)
        self._refresh_templates_table()

    def _create_tag_actions(self, row: int, tag: str) -> QWidget:
        """Create actions widget for tag row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_size = Theme.BTN_ICON_SIZE

        # Rename
        rename_btn = QPushButton()
        rename_btn.setIcon(get_icon("edit", 14))
        rename_btn.setIconSize(QSize(14, 14))
        rename_btn.setFixedSize(btn_size, btn_size)
        rename_btn.setProperty("class", "icon")
        rename_btn.setToolTip("Rename")
        rename_btn.clicked.connect(lambda: self._rename_tag(tag))
        layout.addWidget(rename_btn)

        # Delete
        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", 14))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(btn_size, btn_size)
        del_btn.setProperty("class", "icon")
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self._delete_tag(tag))
        layout.addWidget(del_btn)

        layout.addStretch()
        return widget

    def _add_tag(self):
        """Add new tag."""
        name = self.tag_input.text().strip()
        if not name:
            return
        if name in self.tags:
            QMessageBox.warning(self, "Duplicate", f"Tag '{name}' already exists.")
            return

        self.tags.append(name)
        self.tag_input.clear()
        self.update_tags(self.tags)
        self.tag_created.emit(name)

    def _rename_tag(self, old_name: str):
        """Rename tag."""
        new_name, ok = QInputDialog.getText(
            self, "Rename Tag", "New name:", text=old_name
        )
        if ok and new_name and new_name != old_name:
            if new_name in self.tags:
                QMessageBox.warning(
                    self, "Duplicate", f"Tag '{new_name}' already exists."
                )
                return
            idx = self.tags.index(old_name)
            self.tags[idx] = new_name
            self.update_tags(self.tags)
            self.tag_renamed.emit(old_name, new_name)

    def _delete_tag(self, tag: str):
        """Delete tag."""
        reply = QMessageBox.question(
            self,
            "Delete Tag",
            f"Delete tag '{tag}'? It will be removed from all profiles.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tags.remove(tag)
            self.update_tags(self.tags)
            self.tag_deleted.emit(tag)

    def _add_status(self):
        """Add new status."""
        name = self.status_name_input.text().strip()
        if not name:
            return
        color = self.status_color_combo.currentText().lower()

        self.statuses.append((name, color))
        self.status_name_input.clear()
        self._refresh_statuses_table()
        self.status_created.emit(name, color)

    def _refresh_statuses_table(self):
        """Refresh statuses table."""
        self._selected_statuses.clear()
        self.statuses_toolbar.update_count(0)

        # Add default statuses
        all_statuses = [
            ("Running", "green"),
            ("Stopped", "gray"),
            ("Error", "red"),
        ] + self.statuses

        self.statuses_table.setRowCount(len(all_statuses))

        for row, (name, color) in enumerate(all_statuses):
            # Checkbox (disabled for default statuses)
            self._add_checkbox_to_statuses_table(row, enabled=(row >= 3))

            # Name
            name_item = QTableWidgetItem(name)
            self.statuses_table.setItem(row, 1, name_item)

            # Color badge
            color_label = QLabel(color.capitalize())
            color_map = {
                "green": COLORS.success,
                "red": COLORS.error,
                "yellow": COLORS.warning,
                "blue": COLORS.info,
                "gray": COLORS.text_muted,
            }
            bg = color_map.get(color, COLORS.text_muted)
            color_label.setStyleSheet(
                f"background: {bg}; color: white; padding: 2px 8px; border-radius: 4px;"
            )
            color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.statuses_table.setCellWidget(row, 2, color_label)

            # Actions (only for custom statuses)
            if row >= 3:
                actions = self._create_status_actions(row - 3)
                self.statuses_table.setCellWidget(row, 3, actions)
            else:
                self.statuses_table.setCellWidget(row, 3, QWidget())

    def _create_status_actions(self, idx: int) -> QWidget:
        """Create actions for custom status."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_size = Theme.BTN_ICON_SIZE

        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", 14))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(btn_size, btn_size)
        edit_btn.setProperty("class", "icon")
        edit_btn.setToolTip("Edit")
        edit_btn.clicked.connect(lambda: self._edit_status(idx))
        layout.addWidget(edit_btn)

        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", 14))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(btn_size, btn_size)
        del_btn.setProperty("class", "icon")
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self._delete_status(idx))
        layout.addWidget(del_btn)

        layout.addStretch()
        return widget

    def _edit_status(self, idx: int):
        """Edit custom status."""
        if 0 <= idx < len(self.statuses):
            name, color = self.statuses[idx]
            dialog = StatusEditDialog(name, color, self)
            if dialog.exec():
                new_name, new_color = dialog.get_values()
                if new_name:
                    old_name = name
                    self.statuses[idx] = (new_name, new_color)
                    self._refresh_statuses_table()
                    self.status_renamed.emit(old_name, new_name, new_color)

    def _delete_status(self, idx: int):
        """Delete custom status."""
        if 0 <= idx < len(self.statuses):
            del self.statuses[idx]
            self._refresh_statuses_table()

    def _add_note_template(self):
        """Add note template."""
        name = self.template_name_input.text().strip()
        content = self.template_content_input.toPlainText().strip()
        if not name or not content:
            return

        self.note_templates.append((name, content))
        self.template_name_input.clear()
        self.template_content_input.clear()
        self._refresh_templates_table()
        self.note_template_created.emit(name, content)

    def _refresh_templates_table(self):
        """Refresh templates table."""
        self._selected_templates.clear()
        self.templates_toolbar.update_count(0)

        self.templates_table.setRowCount(len(self.note_templates))

        for row, (name, content) in enumerate(self.note_templates):
            # Checkbox
            self._add_checkbox_to_templates_table(row)

            # Name
            name_item = QTableWidgetItem(name)
            self.templates_table.setItem(row, 1, name_item)

            # Preview
            preview = content[:50] + "..." if len(content) > 50 else content
            preview = preview.replace("\n", " ")
            preview_item = QTableWidgetItem(preview)
            self.templates_table.setItem(row, 2, preview_item)

            # Actions
            actions = self._create_template_actions(row)
            self.templates_table.setCellWidget(row, 3, actions)

    def _create_template_actions(self, idx: int) -> QWidget:
        """Create actions for template."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_size = Theme.BTN_ICON_SIZE

        # Edit
        edit_btn = QPushButton()
        edit_btn.setIcon(get_icon("edit", 14))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(btn_size, btn_size)
        edit_btn.setProperty("class", "icon")
        edit_btn.setToolTip("Edit")
        edit_btn.clicked.connect(lambda: self._edit_template(idx))
        layout.addWidget(edit_btn)

        # Delete
        del_btn = QPushButton()
        del_btn.setIcon(get_icon("trash", 14))
        del_btn.setIconSize(QSize(14, 14))
        del_btn.setFixedSize(btn_size, btn_size)
        del_btn.setProperty("class", "icon")
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self._delete_template(idx))
        layout.addWidget(del_btn)

        layout.addStretch()
        return widget

    def _edit_template(self, idx: int):
        """Edit template."""
        if 0 <= idx < len(self.note_templates):
            name, content = self.note_templates[idx]
            self.template_name_input.setText(name)
            self.template_content_input.setText(content)
            del self.note_templates[idx]
            self._refresh_templates_table()

    def _delete_template(self, idx: int):
        """Delete template."""
        if 0 <= idx < len(self.note_templates):
            del self.note_templates[idx]
            self._refresh_templates_table()

    def get_note_templates(self) -> list[tuple[str, str]]:
        """Get note templates list."""
        return self.note_templates

    # --- Checkbox / Selection methods ---

    def _add_checkbox_to_tags_table(self, row: int) -> None:
        """Add checkbox widget to tags table row."""
        checkbox = CheckboxWidget()
        checkbox.toggled.connect(
            lambda checked, r=row: self._on_tag_checkbox_toggled(r, checked)
        )
        self.tags_table.setCellWidget(row, 0, checkbox)

    def _on_tag_checkbox_toggled(self, row: int, checked: bool) -> None:
        """Handle tag row checkbox toggle."""
        if checked:
            if row not in self._selected_tags:
                self._selected_tags.append(row)
        else:
            if row in self._selected_tags:
                self._selected_tags.remove(row)
        self.tags_toolbar.update_count(len(self._selected_tags))
        self._update_tags_header_state()

    def _update_tags_header_state(self) -> None:
        """Update header checkbox state based on selections."""
        total = self.tags_table.rowCount()
        if total > 0 and len(self._selected_tags) == total:
            self._tags_header_checked = True
        else:
            self._tags_header_checked = False

        if hasattr(self, "_tags_header_checkbox") and self._tags_header_checkbox:
            self._tags_header_checkbox.blockSignals(True)
            self._tags_header_checkbox.setChecked(self._tags_header_checked)
            self._tags_header_checkbox.blockSignals(False)

    def _deselect_all_tags(self) -> None:
        """Deselect all tags."""
        self._toggle_all_tags(False)

    def _toggle_all_tags(self, checked: bool) -> None:
        """Toggle all tag checkboxes."""
        for row in range(self.tags_table.rowCount()):
            widget = self.tags_table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)
        if checked:
            self._selected_tags = list(range(self.tags_table.rowCount()))
        else:
            self._selected_tags.clear()
        self.tags_toolbar.update_count(len(self._selected_tags))

    def _on_tags_header_clicked(self, section: int) -> None:
        """Handle header section click for tags table - pass through (HeaderCheckbox handles toggle)."""
        pass  # HeaderCheckbox overlay handles this now

    def _on_tags_header_checkbox_toggled(self, checked: bool) -> None:
        """Handle header checkbox toggle for tags table."""
        self._tags_header_checked = checked
        self._toggle_all_tags(checked)

    def _on_batch_delete_tags(self) -> None:
        """Handle batch delete tags."""
        if not self._selected_tags:
            return
        tag_names = [
            self.tags[i]
            for i in sorted(self._selected_tags, reverse=True)
            if i < len(self.tags)
        ]
        if tag_names:
            self.batch_delete_tags.emit(tag_names)
            # Deselect all after delete
            self._toggle_all_tags(False)

    def _add_checkbox_to_statuses_table(self, row: int, enabled: bool = True) -> None:
        """Add checkbox widget to statuses table row."""
        checkbox = CheckboxWidget()
        checkbox.setEnabled(enabled)
        checkbox.toggled.connect(
            lambda checked, r=row: self._on_status_checkbox_toggled(r, checked)
        )
        self.statuses_table.setCellWidget(row, 0, checkbox)

    def _on_status_checkbox_toggled(self, row: int, checked: bool) -> None:
        """Handle status row checkbox toggle."""
        if checked:
            if row not in self._selected_statuses:
                self._selected_statuses.append(row)
        else:
            if row in self._selected_statuses:
                self._selected_statuses.remove(row)
        self.statuses_toolbar.update_count(len(self._selected_statuses))
        self._update_statuses_header_state()

    def _update_statuses_header_state(self) -> None:
        """Update header checkbox state based on selections."""
        # Count only enabled (custom) rows
        enabled_count = sum(
            1
            for row in range(self.statuses_table.rowCount())
            if isinstance(self.statuses_table.cellWidget(row, 0), CheckboxWidget)
            and self.statuses_table.cellWidget(row, 0).isEnabled()
        )
        if enabled_count > 0 and len(self._selected_statuses) == enabled_count:
            self._statuses_header_checked = True
        else:
            self._statuses_header_checked = False

        if (
            hasattr(self, "_statuses_header_checkbox")
            and self._statuses_header_checkbox
        ):
            self._statuses_header_checkbox.blockSignals(True)
            self._statuses_header_checkbox.setChecked(self._statuses_header_checked)
            self._statuses_header_checkbox.blockSignals(False)

    def _deselect_all_statuses(self) -> None:
        """Deselect all statuses."""
        self._toggle_all_statuses(False)

    def _toggle_all_statuses(self, checked: bool) -> None:
        """Toggle all status checkboxes (only enabled ones)."""
        selected = []
        for row in range(self.statuses_table.rowCount()):
            widget = self.statuses_table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget) and widget.isEnabled():
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)
                if checked:
                    selected.append(row)
        if checked:
            self._selected_statuses = selected
        else:
            self._selected_statuses.clear()
        self.statuses_toolbar.update_count(len(self._selected_statuses))

    def _on_statuses_header_clicked(self, section: int) -> None:
        """Handle header section click for statuses table - pass through (HeaderCheckbox handles toggle)."""
        pass  # HeaderCheckbox overlay handles this now

    def _on_statuses_header_checkbox_toggled(self, checked: bool) -> None:
        """Handle header checkbox toggle for statuses table."""
        self._statuses_header_checked = checked
        self._toggle_all_statuses(checked)

    def _on_batch_delete_statuses(self) -> None:
        """Handle batch delete statuses."""
        if not self._selected_statuses:
            return
        # Only custom statuses (row >= 3)
        custom_rows = [
            r - 3 for r in sorted(self._selected_statuses, reverse=True) if r >= 3
        ]
        status_names = [
            self.statuses[i][0] for i in custom_rows if i < len(self.statuses)
        ]
        if status_names:
            self.batch_delete_statuses.emit(status_names)
            # Deselect all after delete
            self._toggle_all_statuses(False)

    def _add_checkbox_to_templates_table(self, row: int) -> None:
        """Add checkbox widget to templates table row."""
        checkbox = CheckboxWidget()
        checkbox.toggled.connect(
            lambda checked, r=row: self._on_template_checkbox_toggled(r, checked)
        )
        self.templates_table.setCellWidget(row, 0, checkbox)

    def _on_template_checkbox_toggled(self, row: int, checked: bool) -> None:
        """Handle template row checkbox toggle."""
        if checked:
            if row not in self._selected_templates:
                self._selected_templates.append(row)
        else:
            if row in self._selected_templates:
                self._selected_templates.remove(row)
        self.templates_toolbar.update_count(len(self._selected_templates))
        self._update_templates_header_state()

    def _update_templates_header_state(self) -> None:
        """Update header checkbox state based on selections."""
        total = self.templates_table.rowCount()
        if total > 0 and len(self._selected_templates) == total:
            self._templates_header_checked = True
        else:
            self._templates_header_checked = False

        if (
            hasattr(self, "_templates_header_checkbox")
            and self._templates_header_checkbox
        ):
            self._templates_header_checkbox.blockSignals(True)
            self._templates_header_checkbox.setChecked(self._templates_header_checked)
            self._templates_header_checkbox.blockSignals(False)

    def _deselect_all_templates(self) -> None:
        """Deselect all templates."""
        self._toggle_all_templates(False)

    def _toggle_all_templates(self, checked: bool) -> None:
        """Toggle all template checkboxes."""
        for row in range(self.templates_table.rowCount()):
            widget = self.templates_table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)
        if checked:
            self._selected_templates = list(range(self.templates_table.rowCount()))
        else:
            self._selected_templates.clear()
        self.templates_toolbar.update_count(len(self._selected_templates))

    def _on_templates_header_clicked(self, section: int) -> None:
        """Handle header section click for templates table - pass through (HeaderCheckbox handles toggle)."""
        pass  # HeaderCheckbox overlay handles this now

    def _on_templates_header_checkbox_toggled(self, checked: bool) -> None:
        """Handle header checkbox toggle for templates table."""
        self._templates_header_checked = checked
        self._toggle_all_templates(checked)

    def _on_batch_delete_templates(self) -> None:
        """Handle batch delete templates."""
        if not self._selected_templates:
            return
        template_names = [
            self.note_templates[i][0]
            for i in sorted(self._selected_templates, reverse=True)
            if i < len(self.note_templates)
        ]
        if template_names:
            self.batch_delete_templates.emit(template_names)
            # Deselect all after delete
            self._toggle_all_templates(False)

    # === Toolbar positioning ===

    def eventFilter(self, obj, event):
        """Handle events for toolbar positioning."""
        if event.type() == QEvent.Type.Resize:
            if obj == self._tags_table_area:
                self._position_tags_toolbar()
            elif obj == self._statuses_table_area:
                self._position_statuses_toolbar()
            elif obj == self._templates_table_area:
                self._position_templates_toolbar()
        return super().eventFilter(obj, event)

    # === Header checkbox positioning ===

    def _position_tags_header_checkbox(self):
        """Position header checkbox over first column of tags table."""
        if (
            not hasattr(self, "_tags_header_checkbox")
            or not self._tags_header_checkbox
            or not self.tags_table
        ):
            return
        Theme.position_header_checkbox(self.tags_table, self._tags_header_checkbox)

    def _position_statuses_header_checkbox(self):
        """Position header checkbox over first column of statuses table."""
        if (
            not hasattr(self, "_statuses_header_checkbox")
            or not self._statuses_header_checkbox
            or not self.statuses_table
        ):
            return
        Theme.position_header_checkbox(
            self.statuses_table, self._statuses_header_checkbox
        )

    def _position_templates_header_checkbox(self):
        """Position header checkbox over first column of templates table."""
        if (
            not hasattr(self, "_templates_header_checkbox")
            or not self._templates_header_checkbox
            or not self.templates_table
        ):
            return
        Theme.position_header_checkbox(
            self.templates_table, self._templates_header_checkbox
        )

    def _position_tags_toolbar(self):
        """Position tags toolbar at bottom center."""
        QTimer.singleShot(
            0,
            lambda: self._do_position_toolbar(self._tags_table_area, self.tags_toolbar),
        )

    def _position_statuses_toolbar(self):
        """Position statuses toolbar at bottom center."""
        QTimer.singleShot(
            0,
            lambda: self._do_position_toolbar(
                self._statuses_table_area, self.statuses_toolbar
            ),
        )

    def _position_templates_toolbar(self):
        """Position templates toolbar at bottom center."""
        QTimer.singleShot(
            0,
            lambda: self._do_position_toolbar(
                self._templates_table_area, self.templates_toolbar
            ),
        )

    def _do_position_toolbar(
        self, table_area: QWidget | None, toolbar: FloatingToolbar | None
    ):
        """Actually position toolbar at bottom center of table area."""
        if not table_area or not toolbar:
            return
        if not toolbar.isVisible():
            return

        toolbar.adjustSize()
        toolbar_width = toolbar.width()
        area_width = table_area.width()
        area_height = table_area.height()

        x = (area_width - toolbar_width) // 2
        y = area_height - toolbar.height() - SPACING.lg

        toolbar.move(x, y)
        toolbar.raise_()
