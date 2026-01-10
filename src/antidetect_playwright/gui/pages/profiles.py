"""Profiles page with sidebar and table."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QScrollArea,
    QStackedWidget,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer

from ..theme import Theme, COLORS, TYPOGRAPHY, SPACING
from ..icons import get_icon
from ..widgets import (
    StatusBadge,
    TagsWidget,
    NotesWidget,
    ProxyWidget,
    ProfileNameWidget,
    FolderItem,
    AllProfilesItem,
    TagFilterWidget,
    PaginationWidget,
    EmptyPlaceholder,
)
from ..components import FloatingToolbar, CheckboxWidget, HeaderCheckbox


class ProfilesPage(QWidget):
    """Profiles page with sidebar and content area."""

    folder_selected = pyqtSignal(str)
    folder_context_menu = pyqtSignal(str, object)
    create_folder_clicked = pyqtSignal()
    search_changed = pyqtSignal(str)
    quick_create_clicked = pyqtSignal()
    create_profile_clicked = pyqtSignal()
    tag_filter_changed = pyqtSignal(str)
    page_changed = pyqtSignal(int)
    per_page_changed = pyqtSignal(int)
    profile_context_menu = pyqtSignal(object, object)

    # Batch operations signals
    batch_start = pyqtSignal(list)  # List of profile IDs
    batch_stop = pyqtSignal(list)
    batch_tag = pyqtSignal(list)
    batch_notes = pyqtSignal(list)
    batch_ping = pyqtSignal(list)
    batch_delete = pyqtSignal(list)
    selection_changed = pyqtSignal(list)  # Selected row indices

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._current_folder = ""
        self._selected_rows = []
        self._table_area: QWidget | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup page UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter for resizable sidebar
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar (folders)
        sidebar = self._create_sidebar()
        self.splitter.addWidget(sidebar)

        # Main content
        content = self._create_content()
        self.splitter.addWidget(content)

        # Set initial sizes
        self.splitter.setSizes([self.settings.sidebar_width, 1000])
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

        layout.addWidget(self.splitter)

        # Install event filter on table area for toolbar positioning
        if self._table_area:
            self._table_area.installEventFilter(self)

    def _create_sidebar(self) -> QWidget:
        """Create left sidebar with folders."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(200)
        sidebar.setMaximumWidth(280)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, SPACING.lg, 0, SPACING.lg)
        layout.setSpacing(SPACING.xs)

        # Logo/Title
        title = QLabel("ANTIDETECT")
        title.setProperty("class", "heading")
        title.setStyleSheet(
            f"padding: {SPACING.sm}px {SPACING.lg}px {SPACING.lg}px {SPACING.lg}px;"
        )
        layout.addWidget(title)

        # All Profiles
        self.all_profiles_item = AllProfilesItem(0, True)
        self.all_profiles_item.clicked.connect(lambda: self.folder_selected.emit(""))
        layout.addWidget(self.all_profiles_item)

        # Folders section
        folders_label = QLabel("FOLDERS")
        folders_label.setProperty("class", "muted")
        folders_label.setStyleSheet(
            f"padding: {SPACING.lg}px {SPACING.lg}px {SPACING.sm}px {SPACING.lg}px;"
        )
        layout.addWidget(folders_label)

        # Folders container (scrollable)
        self.folders_container = QWidget()
        self.folders_layout = QVBoxLayout(self.folders_container)
        self.folders_layout.setContentsMargins(0, 0, 0, 0)
        self.folders_layout.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidget(self.folders_container)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll, 1)

        # Add folder button with icon
        add_folder_btn = QPushButton(" New Folder")
        add_folder_btn.setIcon(get_icon("plus", 14))
        add_folder_btn.setIconSize(QSize(14, 14))
        add_folder_btn.setProperty("class", "ghost")
        add_folder_btn.setStyleSheet(
            f"""
            QPushButton {{
                color: {COLORS.accent};
                text-align: left;
                padding: {SPACING.sm}px {SPACING.lg}px;
            }}
        """
        )
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.clicked.connect(self.create_folder_clicked.emit)
        layout.addWidget(add_folder_btn)

        return sidebar

    def _create_content(self) -> QWidget:
        """Create main content area."""
        content = QFrame()
        content.setObjectName("content")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Table area with floating toolbar overlay
        table_area = QWidget()
        table_area_layout = QVBoxLayout(table_area)
        table_area_layout.setContentsMargins(0, 0, 0, 0)
        table_area_layout.setSpacing(0)

        # Container for table + overlay toolbar
        table_container_widget = QWidget()
        table_container_widget.setObjectName("tableContainerWidget")
        table_layout = QVBoxLayout(table_container_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        # Stacked widget for table/empty state
        self.content_stack = QStackedWidget()

        # Table (wrapped in container)
        self.table = self._create_table()
        self.table_container = Theme.create_table_container(self.table)
        self.content_stack.addWidget(self.table_container)

        # Header checkbox overlay (positioned over first header column)
        self._header_checkbox.setParent(self.table)
        self._header_checkbox.setFixedSize(24, 24)
        self._position_header_checkbox()
        self._header_checkbox.raise_()
        self._header_checkbox.show()

        # Reposition on scroll/resize
        self.table.horizontalHeader().sectionResized.connect(
            lambda: self._position_header_checkbox()
        )

        # Empty placeholder
        self.empty_placeholder = EmptyPlaceholder()
        self.empty_placeholder.create_clicked.connect(self.create_profile_clicked.emit)
        self.content_stack.addWidget(self.empty_placeholder)

        table_layout.addWidget(self.content_stack, 1)
        table_area_layout.addWidget(table_container_widget, 1)

        # Floating toolbar (overlay at bottom center)
        self.floating_toolbar = FloatingToolbar("profiles")
        self.floating_toolbar.setParent(table_area)
        self.floating_toolbar.start_clicked.connect(self._on_batch_start)
        self.floating_toolbar.stop_clicked.connect(self._on_batch_stop)
        self.floating_toolbar.tag_clicked.connect(self._on_batch_tag)
        self.floating_toolbar.notes_clicked.connect(self._on_batch_notes)
        self.floating_toolbar.ping_clicked.connect(self._on_batch_ping)
        self.floating_toolbar.delete_clicked.connect(self._on_batch_delete)
        self.floating_toolbar.visibility_changed.connect(
            lambda visible: self._position_toolbar() if visible else None
        )

        # Store reference to table_area for resizeEvent
        self._table_area = table_area

        layout.addWidget(table_area, 1)

        # Footer
        footer = self._create_footer()
        layout.addWidget(footer)

        return content

    def _create_header(self) -> QWidget:
        """Create header with actions and search."""
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(50)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(SPACING.lg, 0, SPACING.lg, 0)
        layout.setSpacing(SPACING.md)

        # Current folder label
        self.folder_label = QLabel("All Profiles")
        self.folder_label.setProperty("class", "subheading")
        layout.addWidget(self.folder_label)

        layout.addStretch()

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setFixedWidth(180)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input)

        # Quick profile button with icon
        quick_btn = QPushButton(" Quick")
        quick_btn.setIcon(get_icon("refresh", 14))
        quick_btn.setIconSize(QSize(14, 14))
        quick_btn.setToolTip("Create quick profile with random settings")
        quick_btn.clicked.connect(self.quick_create_clicked.emit)
        layout.addWidget(quick_btn)

        # Create profile button with icon
        create_btn = QPushButton(" New Profile")
        create_btn.setIcon(get_icon("plus", 14))
        create_btn.setIconSize(QSize(14, 14))
        create_btn.setProperty("class", "primary")
        create_btn.clicked.connect(self.create_profile_clicked.emit)
        layout.addWidget(create_btn)

        return header

    def _create_table(self) -> QTableWidget:
        """Create profiles table with checkbox column."""
        table = QTableWidget()
        table.setColumnCount(6)  # Checkbox + 5 columns
        table.setHorizontalHeaderLabels(
            ["", "Name", "Status", "Notes", "Tags", "Proxy"]
        )

        # Unified table styling first
        Theme.setup_table(table)

        # Configure columns with proper sizing
        Theme.setup_table_columns(
            table,
            [
                (0, "fixed", Theme.COL_CHECKBOX),  # Checkbox
                (1, "stretch", None),  # Name - fills space
                (2, "fixed", Theme.COL_STATUS),  # Status
                (3, "stretch", None),  # Notes - fills space
                (4, "stretch", None),  # Tags - fills space
                (5, "stretch", None),  # Proxy - fills space
            ],
        )

        # Header checkbox for select all
        self._header_checkbox = HeaderCheckbox()
        self._header_checkbox.toggled.connect(self._on_header_checkbox_toggled)

        # Position header checkbox in first column header
        # We need to use a custom approach since QHeaderView doesn't support widgets directly
        table.horizontalHeader().sectionClicked.connect(self._on_header_section_clicked)

        # Track header checkbox state
        self._header_checked = False

        # Context menu
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._on_context_menu)

        return table

    def _create_footer(self) -> QWidget:
        """Create footer with tags and pagination."""
        footer = QFrame()
        footer.setObjectName("footer")
        footer.setFixedHeight(44)

        layout = QHBoxLayout(footer)
        layout.setContentsMargins(SPACING.lg, 0, SPACING.lg, 0)
        layout.setSpacing(SPACING.md)

        # Tag filters
        self.tag_filter = TagFilterWidget([])
        self.tag_filter.tag_selected.connect(self.tag_filter_changed.emit)
        layout.addWidget(self.tag_filter)

        layout.addStretch()

        # Pagination
        self.pagination = PaginationWidget(0, 1, self.settings.items_per_page)
        self.pagination.page_changed.connect(self.page_changed.emit)
        self.pagination.per_page_changed.connect(self.per_page_changed.emit)
        layout.addWidget(self.pagination)

        return footer

    def _on_splitter_moved(self, pos: int, index: int):
        """Handle splitter moved."""
        self.settings.sidebar_width = pos

    def _on_context_menu(self, pos):
        """Forward context menu request."""
        item = self.table.itemAt(pos)
        if item:
            self.profile_context_menu.emit(item, self.table.mapToGlobal(pos))

    def set_folder_label(self, text: str):
        """Update folder label text."""
        self.folder_label.setText(text)

    def update_folders(self, folders: list, folder_counts: dict, current_folder: str):
        """Update folders list."""
        # Clear existing
        while self.folders_layout.count():
            item = self.folders_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._current_folder = current_folder

        # Update All Profiles selection state
        is_all_selected = current_folder == ""
        self.all_profiles_item.update_selected(is_all_selected)

        # Add folders
        for folder in folders:
            count = folder_counts.get(folder.id, 0)
            item = FolderItem(folder, count, current_folder == folder.id)
            item.clicked.connect(self.folder_selected.emit)
            item.context_menu_requested.connect(self.folder_context_menu.emit)
            self.folders_layout.addWidget(item)

        self.folders_layout.addStretch()

    def update_all_profiles_count(self, count: int):
        """Update all profiles count."""
        self.all_profiles_item.update_count(count)

    def update_tag_filter(self, tags: list, current_tag: str):
        """Update tag filter widget."""
        self.tag_filter.update_tags(tags, current_tag)

    def show_empty_state(self):
        """Show empty placeholder."""
        self.content_stack.setCurrentWidget(self.empty_placeholder)

    def show_table(self):
        """Show profiles table."""
        self.content_stack.setCurrentWidget(self.table_container)

    # === Checkbox and selection methods ===

    def add_checkbox_to_row(self, row: int):
        """Add checkbox widget to row's first column."""
        checkbox = CheckboxWidget()
        checkbox.toggled.connect(
            lambda checked: self._on_row_checkbox_toggled(row, checked)
        )
        self.table.setCellWidget(row, 0, checkbox)

    def _on_header_section_clicked(self, section: int):
        """Handle header section click - toggle select all for column 0."""
        if section == 0:
            # Toggle is handled by HeaderCheckbox click
            pass

    def _on_header_checkbox_toggled(self, checked: bool):
        """Handle header (select all) checkbox toggle."""
        self._header_checked = checked
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)
        self._update_selection()

    def _on_row_checkbox_toggled(self, row: int, checked: bool):
        """Handle individual row checkbox toggle."""
        self._update_selection()
        self._update_header_checkbox_state()

    def _update_header_checkbox_state(self):
        """Update header checkbox state based on row selections."""
        total = self.table.rowCount()
        if total == 0:
            self._header_checked = False
            if self._header_checkbox:
                self._header_checkbox.blockSignals(True)
                self._header_checkbox.setChecked(False)
                self._header_checkbox.blockSignals(False)
            return

        selected_count = len(self._selected_rows)
        if selected_count == total:
            self._header_checked = True
        else:
            self._header_checked = False

        if self._header_checkbox:
            self._header_checkbox.blockSignals(True)
            self._header_checkbox.setChecked(self._header_checked)
            self._header_checkbox.blockSignals(False)

    def _update_selection(self):
        """Update selected rows and toolbar."""
        selected = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget) and widget.isChecked():
                selected.append(row)

        self._selected_rows = selected
        self.floating_toolbar.update_count(len(selected))
        self.selection_changed.emit(selected)

    def get_selected_profile_ids(self) -> list[str]:
        """Get list of selected profile IDs."""
        ids = []
        for row in self._selected_rows:
            item = self.table.item(row, 1)  # Name column stores ID
            if item:
                profile_id = item.data(Qt.ItemDataRole.UserRole)
                if profile_id:
                    ids.append(profile_id)
        return ids

    def _deselect_all(self):
        """Deselect all checkboxes."""
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, CheckboxWidget):
                widget.setChecked(False)
        self._update_selection()

    # === Batch operation handlers ===

    def _on_batch_start(self):
        """Handle batch start."""
        self.batch_start.emit(self.get_selected_profile_ids())

    def _on_batch_stop(self):
        """Handle batch stop."""
        self.batch_stop.emit(self.get_selected_profile_ids())

    def _on_batch_tag(self):
        """Handle batch tag."""
        self.batch_tag.emit(self.get_selected_profile_ids())

    def _on_batch_notes(self):
        """Handle batch notes."""
        self.batch_notes.emit(self.get_selected_profile_ids())

    def _on_batch_ping(self):
        """Handle batch ping."""
        self.batch_ping.emit(self.get_selected_profile_ids())

    def _on_batch_delete(self):
        """Handle batch delete."""
        self.batch_delete.emit(self.get_selected_profile_ids())
        # Deselect all after delete
        self._deselect_all()

    # === Header checkbox positioning ===

    def _position_header_checkbox(self):
        """Position header checkbox over first column header."""
        if not self._header_checkbox or not self.table:
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
        self._do_position_toolbar()

    def _do_position_toolbar(self):
        """Actually position the toolbar."""
        if not self._table_area or not self.floating_toolbar:
            return

        self.floating_toolbar.adjustSize()
        toolbar_width = self.floating_toolbar.width()
        toolbar_height = self.floating_toolbar.height()
        area_width = self._table_area.width()
        area_height = self._table_area.height()

        x = (area_width - toolbar_width) // 2
        y = area_height - toolbar_height - SPACING.lg

        self.floating_toolbar.setGeometry(x, y, toolbar_width, toolbar_height)
