"""Popup-based dialogs - modern inline modals replacing QDialog."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QLabel,
    QGroupBox,
)
from PyQt6.QtGui import QPixmap, QIcon, QColor

from .popup import PopupDialog
from .models import BrowserProfile, Folder
from .styles import COLORS, get_country_flag


def show_quick_profile_popup(parent) -> BrowserProfile | None:
    """Show quick profile creation popup.
    
    Returns:
        BrowserProfile if created, None if cancelled
    """
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    layout.addWidget(QLabel("Create a new profile with auto-configured fingerprint:"))
    
    name_input = QLineEdit()
    name_input.setPlaceholderText("Profile name")
    layout.addWidget(name_input)
    
    # Create popup
    popup = PopupDialog(parent, "Quick Profile")
    popup.set_dialog_content(content)
    
    # Result storage
    profile = None
    
    def on_create():
        name = name_input.text().strip()
        if not name:
            return
        nonlocal profile
        profile = BrowserProfile()
        profile.name = name
        popup.accept()
    
    # Enter key creates
    name_input.returnPressed.connect(on_create)
    
    # Add buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Create", on_create, True)
    
    # Show and return result
    if popup.exec():
        return profile
    return None


def show_folder_popup(parent, folder: Folder | None = None) -> Folder | None:
    """Show folder create/edit popup.
    
    Args:
        parent: Parent widget
        folder: Existing folder to edit, or None to create new
    
    Returns:
        Folder if saved, None if cancelled
    """
    from .components import InlineAlert, make_combobox_searchable
    
    # Prepare folder
    if folder is None:
        folder = Folder()
        is_new = True
    else:
        is_new = False
    
    # Content
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(16)
    
    # Alert
    alert = InlineAlert(content)
    layout.addWidget(alert)
    
    # Form
    form = QFormLayout()
    form.setSpacing(8)
    
    # Name
    name_input = QLineEdit()
    name_input.setPlaceholderText("Folder name")
    if not is_new and folder.name != "New Folder":
        name_input.setText(folder.name)
    form.addRow("Name:", name_input)
    
    # Color
    COLORS_LIST = [
        ("#6366f1", "Indigo"),
        ("#ec4899", "Pink"),
        ("#22c55e", "Green"),
        ("#f59e0b", "Orange"),
        ("#3b82f6", "Blue"),
        ("#8b5cf6", "Purple"),
        ("#14b8a6", "Teal"),
        ("#f43f5e", "Rose"),
    ]
    
    color_combo = QComboBox()
    for color, name in COLORS_LIST:
        # Create colored icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(color))
        icon = QIcon(pixmap)
        color_combo.addItem(icon, name, color)
    
    # Set current color
    if not is_new:
        for i, (color, _) in enumerate(COLORS_LIST):
            if color == folder.color:
                color_combo.setCurrentIndex(i)
                break
    
    make_combobox_searchable(color_combo, "Search color")
    form.addRow("Color:", color_combo)
    
    layout.addLayout(form)
    
    # Create popup
    title = "New Folder" if is_new else "Edit Folder"
    popup = PopupDialog(parent, title)
    popup.set_dialog_content(content)
    
    # Result
    result_folder = None
    
    def on_save():
        name = name_input.text().strip()
        if not name:
            alert.show_error("Error", "Folder name is required")
            return
        
        folder.name = name
        folder.color = color_combo.currentData()
        
        nonlocal result_folder
        result_folder = folder
        popup.accept()
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Save", on_save, True)
    
    if popup.exec():
        return result_folder
    return None


def show_status_edit_popup(parent, name: str, color: str) -> tuple[str, str] | None:
    """Show status edit popup.
    
    Args:
        parent: Parent widget
        name: Current status name
        color: Current color (green/red/yellow/blue/gray)
    
    Returns:
        Tuple of (name, color) if saved, None if cancelled
    """
    from .components import make_combobox_searchable
    
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(16)
    
    # Form
    form = QFormLayout()
    form.setSpacing(8)
    
    name_input = QLineEdit(name)
    name_input.setPlaceholderText("Status name...")
    form.addRow("Name:", name_input)
    
    color_combo = QComboBox()
    color_combo.addItems(["green", "red", "yellow", "blue", "gray"])
    if color in ["green", "red", "yellow", "blue", "gray"]:
        color_combo.setCurrentText(color)
    make_combobox_searchable(color_combo, "Search color")
    form.addRow("Color:", color_combo)
    
    layout.addLayout(form)
    
    # Create popup
    popup = PopupDialog(parent, "Edit Status")
    popup.set_dialog_content(content)
    
    # Result
    result = None
    
    def on_save():
        nonlocal result
        result = (name_input.text().strip(), color_combo.currentText())
        popup.accept()
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Save", on_save, True)
    
    if popup.exec():
        return result
    return None


def show_tags_edit_popup(parent, current_tags: list[str], all_tags: list[str]) -> list[str] | None:
    """Show tags edit popup.
    
    Args:
        parent: Parent widget
        current_tags: Currently assigned tags
        all_tags: All available tags
    
    Returns:
        Updated tag list if saved, None if cancelled
    """
    from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QPushButton, QTextEdit
    from PyQt6.QtCore import Qt
    from .components import InlineAlert
    
    # Work with copies
    tags = list(current_tags)
    available = [t for t in all_tags if t not in tags]
    
    # Content
    content = QWidget()
    content.setMinimumWidth(550)  # Wider for tags list
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    alert = InlineAlert(content)
    layout.addWidget(alert)
    
    # Add from pool section
    if available:
        layout.addWidget(QLabel("Add from pool:"))
        
        available_search = QLineEdit()
        available_search.setPlaceholderText("Search tags")
        layout.addWidget(available_search)
        
        available_list = QListWidget()
        available_list.addItems(available)
        available_list.setMaximumHeight(100)
        layout.addWidget(available_list)
        
        def filter_available(text: str):
            text_lower = text.lower()
            for i in range(available_list.count()):
                item = available_list.item(i)
                item.setHidden(text_lower not in item.text().lower())
        
        available_search.textChanged.connect(filter_available)
        
        def add_from_pool():
            item = available_list.currentItem()
            if not item:
                return
            tag = item.text()
            if tag in tags:
                alert.show_error("Duplicate", f"Tag '{tag}' already added.")
                return
            tags.append(tag)
            available.remove(tag)
            refresh_tags_list()
            refresh_available_list()
        
        def refresh_available_list():
            available_list.clear()
            available_list.addItems(available)
            filter_available(available_search.text())
        
        available_list.itemDoubleClicked.connect(lambda: add_from_pool())
        
        add_pool_btn = QPushButton("Add")
        add_pool_btn.setStyleSheet(f"background: {COLORS['accent']}; color: white;")
        add_pool_btn.clicked.connect(add_from_pool)
        layout.addWidget(add_pool_btn)
    else:
        available_search = None
        available_list = None
        add_from_pool = None
        refresh_available_list = None
    
    # Add custom tag section
    layout.addWidget(QLabel("Add custom tag:"))
    
    custom_layout = QHBoxLayout()
    custom_input = QLineEdit()
    custom_input.setPlaceholderText("Enter new tag name...")
    custom_layout.addWidget(custom_input, 1)
    
    def add_custom():
        tag = custom_input.text().strip()
        if not tag:
            return
        if tag in tags:
            alert.show_error("Duplicate", f"Tag '{tag}' already added.")
            return
        tags.append(tag)
        if tag in available:
            available.remove(tag)
        refresh_tags_list()
        if refresh_available_list:
            refresh_available_list()
        custom_input.clear()
    
    custom_input.returnPressed.connect(add_custom)
    
    add_custom_btn = QPushButton("Add")
    add_custom_btn.clicked.connect(add_custom)
    custom_layout.addWidget(add_custom_btn)
    
    layout.addLayout(custom_layout)
    
    # Current tags list
    layout.addWidget(QLabel("Current tags (click to remove):"))
    tags_list = QListWidget()
    tags_list.setMaximumHeight(150)
    layout.addWidget(tags_list)
    
    def refresh_tags_list():
        tags_list.clear()
        for tag in tags:
            item = QListWidgetItem(f"✕  {tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            tags_list.addItem(item)
    
    def remove_tag(item: QListWidgetItem):
        tag = item.data(Qt.ItemDataRole.UserRole)
        if tag in tags:
            tags.remove(tag)
            refresh_tags_list()
            if tag in all_tags and tag not in available:
                available.append(tag)
                available.sort()
                if refresh_available_list:
                    refresh_available_list()
    
    tags_list.itemClicked.connect(remove_tag)
    refresh_tags_list()
    
    # Create popup
    popup = PopupDialog(parent, "Edit Tags")
    popup.set_dialog_content(content)
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Save", popup.accept, True)
    
    if popup.exec():
        return tags
    return None


def show_notes_edit_popup(parent, notes: str, 
                         note_templates: list[tuple[str, str]] | None = None) -> str | None:
    """Show notes edit popup.
    
    Args:
        parent: Parent widget
        notes: Current notes text
        note_templates: Optional list of (name, template) tuples
    
    Returns:
        Updated notes if saved, None if cancelled
    """
    from PyQt6.QtWidgets import QTextEdit, QListWidget, QPushButton
    from .components import InlineAlert
    
    templates = list(note_templates or [])
    
    # Content
    content = QWidget()
    content.setMinimumWidth(600)  # Wider for notes editor
    content.setMinimumHeight(500)
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    alert = InlineAlert(content)
    layout.addWidget(alert)
    
    # Templates section (if available)
    if templates:
        layout.addWidget(QLabel("Insert from templates:"))
        
        template_search = QLineEdit()
        template_search.setPlaceholderText("Search templates")
        layout.addWidget(template_search)
        
        template_list = QListWidget()
        template_list.addItems([name for name, _ in templates])
        template_list.setMaximumHeight(100)
        layout.addWidget(template_list)
        
        def filter_templates(text: str):
            text_lower = text.lower()
            for i in range(template_list.count()):
                item = template_list.item(i)
                item.setHidden(text_lower not in item.text().lower())
        
        template_search.textChanged.connect(filter_templates)
        
        def get_template_content(name: str) -> str:
            for n, content in templates:
                if n == name:
                    return content
            return ""
        
        def insert_template():
            item = template_list.currentItem()
            if not item:
                return
            name = item.text()
            template_content = get_template_content(name)
            if not template_content:
                alert.show_error("Error", f"Template '{name}' not found.")
                return
            
            current = notes_edit.toPlainText()
            if current and not current.endswith("\n"):
                current += "\n"
            current += template_content
            notes_edit.setPlainText(current)
        
        def replace_with_template():
            item = template_list.currentItem()
            if not item:
                return
            name = item.text()
            template_content = get_template_content(name)
            if not template_content:
                alert.show_error("Error", f"Template '{name}' not found.")
                return
            notes_edit.setPlainText(template_content)
        
        template_list.itemDoubleClicked.connect(lambda: insert_template())
        
        templates_row = QHBoxLayout()
        insert_btn = QPushButton("Insert")
        insert_btn.setStyleSheet(f"background: {COLORS['accent']}; color: white;")
        insert_btn.clicked.connect(insert_template)
        templates_row.addWidget(insert_btn)
        
        replace_btn = QPushButton("Replace")
        replace_btn.clicked.connect(replace_with_template)
        templates_row.addWidget(replace_btn)
        
        layout.addLayout(templates_row)
    
    # Notes editor
    layout.addWidget(QLabel("Notes:"))
    notes_edit = QTextEdit()
    notes_edit.setPlaceholderText("Enter notes for this profile...")
    notes_edit.setText(notes)
    notes_edit.setMinimumHeight(200)
    layout.addWidget(notes_edit)
    
    # Create popup
    popup = PopupDialog(parent, "Edit Notes")
    popup.set_dialog_content(content)
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Save", popup.accept, True)
    
    if popup.exec():
        return notes_edit.toPlainText()
    return None


def show_proxy_pool_popup(parent, proxies: list) -> list | None:
    """Show proxy pool management popup.
    
    Args:
        parent: Parent widget
        proxies: Current proxy list (ProxyConfig objects)
    
    Returns:
        Updated proxy list if saved, None if cancelled
    """
    from PyQt6.QtWidgets import QListWidget, QTextEdit, QPushButton
    from .components import InlineAlert
    
    proxy_list = list(proxies)
    
    # Content
    content = QWidget()
    content.setMinimumWidth(600)  # Wider for proxy pool
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    alert = InlineAlert(content)
    layout.addWidget(alert)
    
    layout.addWidget(QLabel("Manage your proxy pool for quick rotation:"))
    
    # Proxy list
    list_widget = QListWidget()
    list_widget.setMaximumHeight(150)
    layout.addWidget(list_widget)
    
    def refresh_list():
        list_widget.clear()
        for p in proxy_list:
            text = f"{p.proxy_type.value.upper()}://{p.host}:{p.port}"
            if p.username:
                text += " (auth)"
            flag = get_country_flag(p.country_code)
            if flag:
                text = f"{flag} {text}"
            list_widget.addItem(text)
    
    refresh_list()
    
    # Add proxies
    layout.addWidget(QLabel("Add proxies (one per line):"))
    proxy_input = QTextEdit()
    proxy_input.setMaximumHeight(100)
    proxy_input.setPlaceholderText(
        "host:port\nhost:port:user:pass\nsocks5://host:port"
    )
    layout.addWidget(proxy_input)
    
    def add_proxies():
        from .proxy_utils import parse_proxy_list
        
        text = proxy_input.toPlainText()
        new_proxies, errors = parse_proxy_list(text)
        proxy_list.extend(new_proxies)
        refresh_list()
        proxy_input.clear()
        
        if errors:
            alert.show_error(
                "Parse Errors", f"{len(errors)} line(s) failed to parse."
            )
    
    add_btn = QPushButton("Add Proxies")
    add_btn.clicked.connect(add_proxies)
    layout.addWidget(add_btn)
    
    # Create popup
    popup = PopupDialog(parent, "Proxy Pool")
    popup.set_dialog_content(content)
    
    # Buttons
    clear_btn = QPushButton("Clear All")
    clear_btn.clicked.connect(lambda: (proxy_list.clear(), refresh_list()))
    popup.add_button("Clear All", lambda: (proxy_list.clear(), refresh_list()), False)
    
    popup.add_spacer()
    popup.add_button("Close", popup.accept, True)
    
    if popup.exec():
        return proxy_list
    return None


def show_profile_popup(parent, profile: BrowserProfile | None = None, 
                      storage=None) -> tuple[BrowserProfile, bool] | None:
    """Show profile create/edit popup.
    
    Args:
        parent: Parent widget
        profile: Existing profile to edit, or None to create new
        storage: Storage for proxy pool access
    
    Returns:
        Tuple of (profile, should_regenerate) if saved, None if cancelled
    """
    from PyQt6.QtWidgets import QPushButton, QGroupBox
    from PyQt6.QtGui import QColor
    from .components import InlineAlert, make_combobox_searchable
    from .proxy_utils import parse_proxy_string
    from .modal import confirm_dialog, info_dialog, get_item_dialog
    from PyQt6.QtWidgets import QMessageBox
    
    # Prepare profile
    if profile is None:
        profile = BrowserProfile()
        is_new = True
    else:
        is_new = False
    
    regenerate_fingerprint = False
    
    # Content
    content = QWidget()
    content.setMinimumWidth(750)  # Larger popup for profile editor (increased from 700)
    layout = QVBoxLayout(content)
    layout.setSpacing(16)
    
    alert = InlineAlert(content)
    layout.addWidget(alert)
    
    # Profile group
    profile_group = QGroupBox("Profile")
    profile_layout = QFormLayout(profile_group)
    
    name_input = QLineEdit()
    name_input.setPlaceholderText("Profile name")
    name_input.setText(profile.name)
    profile_layout.addRow("Name:", name_input)
    
    os_combo = QComboBox()
    os_combo.addItems(["macOS", "Windows", "Linux"])
    make_combobox_searchable(os_combo, "Search OS")
    
    os_map = {"macos": 0, "windows": 1, "linux": 2}
    os_combo.setCurrentIndex(os_map.get(profile.os_type, 0))
    
    if not is_new:
        os_combo.setEnabled(False)
        os_combo.setToolTip("OS cannot be changed. Use 'Regenerate Fingerprint' to change OS.")
    
    profile_layout.addRow("OS:", os_combo)
    layout.addWidget(profile_group)
    
    # Regenerate fingerprint (only for existing)
    if not is_new:
        regen_group = QGroupBox("Fingerprint")
        regen_layout = QVBoxLayout(regen_group)
        
        regen_info = QLabel(
            "Fingerprint is generated once and saved for consistency.\n"
            "Regenerating will change all browser identifiers."
        )
        regen_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        regen_info.setWordWrap(True)
        regen_layout.addWidget(regen_info)
        
        def on_regenerate():
            nonlocal regenerate_fingerprint
            os_combo.setEnabled(True)
            
            if confirm_dialog(
                parent,
                "Regenerate Fingerprint",
                "⚠️ This will generate a completely new fingerprint:\n\n"
                "• New User-Agent\n"
                "• New WebGL signature\n"
                "• New Canvas fingerprint\n"
                "• New hardware identifiers\n\n"
                "The profile will appear as a different browser.\n"
                "Select the OS for the new fingerprint and click Save.\n\n"
                "Continue?",
                icon=QMessageBox.Icon.Warning,
            ):
                regenerate_fingerprint = True
                alert.show_success("Ready", "Select OS and click Save to regenerate fingerprint")
            else:
                os_combo.setEnabled(False)
        
        regen_btn = QPushButton("🔄 Regenerate Fingerprint")
        regen_btn.setStyleSheet(
            f"background-color: {COLORS['warning']}; color: white; font-weight: 600; padding: 8px 16px;"
        )
        regen_btn.clicked.connect(on_regenerate)
        regen_layout.addWidget(regen_btn)
        
        layout.addWidget(regen_group)
    
    # Proxy group
    proxy_group = QGroupBox("Proxy (Optional)")
    proxy_layout = QVBoxLayout(proxy_group)
    
    # Quick paste
    paste_layout = QHBoxLayout()
    proxy_input = QLineEdit()
    proxy_input.setPlaceholderText("host:port or host:port:user:pass or socks5://...")
    paste_layout.addWidget(proxy_input)
    
    def parse_proxy():
        text = proxy_input.text().strip()
        if not text:
            return
        
        proxy = parse_proxy_string(text)
        if proxy:
            profile.proxy = proxy
            update_proxy_info()
            proxy_input.clear()
        else:
            alert.show_error("Parse Error", "Could not parse proxy string")
    
    parse_btn = QPushButton("Parse")
    parse_btn.clicked.connect(parse_proxy)
    paste_layout.addWidget(parse_btn)
    
    # From pool button
    if storage:
        def select_from_pool():
            proxy_pool = storage.get_proxy_pool()
            if not proxy_pool.proxies:
                info_dialog(parent, "Empty Pool", "Proxy pool is empty. Add proxies in the Proxy page first.")
                return
            
            items = []
            for proxy in proxy_pool.proxies:
                auth = f" (auth: {proxy.username})" if proxy.username else ""
                flag = get_country_flag(proxy.country_code)
                label = f"{proxy.proxy_type.value.upper()}://{proxy.host}:{proxy.port}{auth}"
                if flag:
                    label = f"{flag} {label}"
                items.append(label)
            
            item, ok = get_item_dialog(parent, "Select Proxy from Pool", "Choose proxy:", items, 0, False)
            
            if ok and item:
                idx = items.index(item)
                profile.proxy = proxy_pool.proxies[idx]
                update_proxy_info()
        
        pool_btn = QPushButton("From Pool")
        pool_btn.clicked.connect(select_from_pool)
        paste_layout.addWidget(pool_btn)
    
    proxy_layout.addLayout(paste_layout)
    
    # Proxy info
    proxy_info = QLabel("No proxy configured")
    proxy_info.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 8px;")
    proxy_layout.addWidget(proxy_info)
    
    def update_proxy_info():
        p = profile.proxy
        if p.enabled:
            auth = f" (auth: {p.username})" if p.username else ""
            proxy_info.setText(f"[OK] {p.proxy_type.value.upper()}://{p.host}:{p.port}{auth}")
            proxy_info.setStyleSheet(f"color: {COLORS['success']}; padding: 8px;")
        else:
            proxy_info.setText("No proxy configured")
            proxy_info.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 8px;")
    
    update_proxy_info()
    
    # Clear proxy
    def clear_proxy():
        from .models import ProxyConfig
        profile.proxy = ProxyConfig()
        update_proxy_info()
    
    clear_btn = QPushButton("Clear Proxy")
    clear_btn.clicked.connect(clear_proxy)
    proxy_layout.addWidget(clear_btn)
    
    layout.addWidget(proxy_group)
    
    # Info
    info_label = QLabel(
        "Fingerprint (User-Agent, WebGL, etc.) will be auto-generated.\n"
        "If proxy is set, timezone and language will be auto-detected from IP."
    )
    info_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)
    
    # Create popup
    title = "New Profile" if is_new else "Edit Profile"
    popup = PopupDialog(parent, title)
    popup.set_dialog_content(content)
    
    # Result
    result = None
    
    def on_save():
        name = name_input.text().strip()
        if not name:
            alert.show_error("Error", "Profile name is required")
            return
        
        profile.name = name
        
        os_map_rev = {0: "macos", 1: "windows", 2: "linux"}
        profile.os_type = os_map_rev.get(os_combo.currentIndex(), "macos")
        
        nonlocal result
        result = (profile, regenerate_fingerprint)
        popup.accept()
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Save", on_save, True)
    
    if popup.exec():
        return result
    return None


def show_settings_popup(parent, settings) -> bool:
    """Show settings popup.
    
    Args:
        parent: Parent widget
        settings: Settings object to edit
    
    Returns:
        True if saved, False if cancelled
    """
    from PyQt6.QtWidgets import (
        QTabWidget, QCheckBox, QDoubleSpinBox, QListWidget,
        QListWidgetItem, QFileDialog, QPushButton
    )
    
    # Content
    content = QWidget()
    content.setMinimumWidth(800)  # Large popup for settings
    content.setMinimumHeight(600)
    layout = QVBoxLayout(content)
    layout.setSpacing(12)
    
    # Tab widget
    tabs = QTabWidget()
    tabs.setStyleSheet(
        f"""
        QTabWidget::pane {{
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            background: {COLORS['bg_secondary']};
        }}
        QTabBar::tab {{
            padding: 8px 16px;
            margin-right: 4px;
            background: {COLORS['bg_tertiary']};
            border: 1px solid {COLORS['border']};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        QTabBar::tab:selected {{
            background: {COLORS['bg_secondary']};
            color: {COLORS['accent']};
        }}
    """
    )
    
    # Browser tab
    browser_tab = QWidget()
    browser_layout = QFormLayout(browser_tab)
    browser_layout.setSpacing(12)
    
    save_tabs_checkbox = QCheckBox()
    save_tabs_checkbox.setChecked(settings.save_tabs)
    browser_layout.addRow("Save & restore tabs:", save_tabs_checkbox)
    
    start_page_input = QLineEdit()
    start_page_input.setPlaceholderText("about:blank, https://google.com")
    start_page_input.setText(settings.start_page)
    browser_layout.addRow("Start page:", start_page_input)
    
    # Custom browser path
    browser_path_container = QHBoxLayout()
    browser_path_input = QLineEdit()
    browser_path_input.setPlaceholderText("Leave empty to use bundled Camoufox")
    browser_path_input.setText(settings.browser_executable_path)
    browser_path_container.addWidget(browser_path_input)
    
    def browse_browser():
        file_path, _ = QFileDialog.getOpenFileName(parent, "Select Browser Executable", "", "Executables (*)")
        if file_path:
            browser_path_input.setText(file_path)
    
    browser_path_browse = QPushButton("Browse...")
    browser_path_browse.setFixedWidth(90)
    browser_path_browse.clicked.connect(browse_browser)
    browser_path_container.addWidget(browser_path_browse)
    
    browser_path_widget = QWidget()
    browser_path_widget.setLayout(browser_path_container)
    browser_layout.addRow("Custom browser:", browser_path_widget)
    
    browser_path_help = QLabel("Path to custom AntiDetect browser executable")
    browser_path_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
    browser_layout.addRow("", browser_path_help)
    
    tabs.addTab(browser_tab, "Browser")
    
    # Performance tab
    perf_tab = QWidget()
    perf_layout = QFormLayout(perf_tab)
    perf_layout.setSpacing(12)
    
    block_images_checkbox = QCheckBox()
    block_images_checkbox.setChecked(settings.block_images)
    perf_layout.addRow("Block images:", block_images_checkbox)
    
    block_images_help = QLabel("Saves bandwidth, faster page loads")
    block_images_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
    perf_layout.addRow("", block_images_help)
    
    enable_cache_checkbox = QCheckBox()
    enable_cache_checkbox.setChecked(settings.enable_cache)
    perf_layout.addRow("Enable cache:", enable_cache_checkbox)
    
    cache_help = QLabel("Cache pages and requests (uses more memory)")
    cache_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
    perf_layout.addRow("", cache_help)
    
    tabs.addTab(perf_tab, "Performance")
    
    # Privacy tab
    privacy_tab = QWidget()
    privacy_layout = QFormLayout(privacy_tab)
    privacy_layout.setSpacing(12)
    
    humanize_spin = QDoubleSpinBox()
    humanize_spin.setRange(0.0, 5.0)
    humanize_spin.setSingleStep(0.1)
    humanize_spin.setDecimals(1)
    humanize_spin.setSuffix(" sec")
    humanize_spin.setValue(settings.humanize)
    privacy_layout.addRow("Humanize cursor:", humanize_spin)
    
    humanize_help = QLabel("Humanize cursor movement delay (0 = disabled)")
    humanize_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
    privacy_layout.addRow("", humanize_help)
    
    tabs.addTab(privacy_tab, "Privacy")
    
    # Extensions tab
    ext_tab = QWidget()
    ext_layout = QVBoxLayout(ext_tab)
    ext_layout.setSpacing(12)
    
    exclude_label = QLabel("Exclude default extensions:")
    exclude_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']};")
    ext_layout.addWidget(exclude_label)
    
    exclude_ublock_checkbox = QCheckBox("uBlock Origin (ad blocker)")
    exclude_ublock_checkbox.setChecked(settings.exclude_ublock)
    ext_layout.addWidget(exclude_ublock_checkbox)
    
    exclude_bpc_checkbox = QCheckBox("Bypass Paywalls Clean")
    exclude_bpc_checkbox.setChecked(settings.exclude_bpc)
    ext_layout.addWidget(exclude_bpc_checkbox)
    
    ext_info = QLabel("Note: Default extensions help with anti-detection and privacy")
    ext_info.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
    ext_layout.addWidget(ext_info)
    
    ext_layout.addSpacing(20)
    
    custom_label = QLabel("Custom extensions (.xpi files):")
    custom_label.setStyleSheet(f"font-weight: 600; color: {COLORS['text_primary']};")
    ext_layout.addWidget(custom_label)
    
    custom_addons_list = QListWidget()
    custom_addons_list.setMaximumHeight(120)
    for addon_path in settings.custom_addons:
        custom_addons_list.addItem(addon_path)
    ext_layout.addWidget(custom_addons_list)
    
    def add_addon():
        file_path, _ = QFileDialog.getOpenFileName(parent, "Select Extension File", "", "Firefox Extensions (*.xpi)")
        if file_path:
            custom_addons_list.addItem(file_path)
    
    def remove_addon():
        current_item = custom_addons_list.currentItem()
        if current_item:
            custom_addons_list.takeItem(custom_addons_list.row(current_item))
    
    addons_btn_layout = QHBoxLayout()
    add_addon_btn = QPushButton("Add Extension")
    add_addon_btn.clicked.connect(add_addon)
    addons_btn_layout.addWidget(add_addon_btn)
    
    remove_addon_btn = QPushButton("Remove Selected")
    remove_addon_btn.clicked.connect(remove_addon)
    addons_btn_layout.addWidget(remove_addon_btn)
    
    addons_btn_layout.addStretch()
    ext_layout.addLayout(addons_btn_layout)
    
    ext_layout.addStretch()
    tabs.addTab(ext_tab, "Extensions")
    
    # Debug tab
    debug_tab = QWidget()
    debug_layout = QFormLayout(debug_tab)
    debug_layout.setSpacing(12)
    
    debug_checkbox = QCheckBox()
    debug_checkbox.setChecked(settings.debug_mode)
    debug_layout.addRow("Debug mode:", debug_checkbox)
    
    debug_help = QLabel("Print Camoufox config to console on launch")
    debug_help.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
    debug_layout.addRow("", debug_help)
    
    tabs.addTab(debug_tab, "Debug")
    
    layout.addWidget(tabs)
    
    # Create popup
    popup = PopupDialog(parent, "Settings")
    popup.set_dialog_content(content)
    
    def on_save():
        settings.save_tabs = save_tabs_checkbox.isChecked()
        settings.start_page = start_page_input.text().strip() or "about:blank"
        settings.browser_executable_path = browser_path_input.text().strip()
        settings.block_images = block_images_checkbox.isChecked()
        settings.enable_cache = enable_cache_checkbox.isChecked()
        settings.humanize = humanize_spin.value()
        settings.exclude_ublock = exclude_ublock_checkbox.isChecked()
        settings.exclude_bpc = exclude_bpc_checkbox.isChecked()
        settings.debug_mode = debug_checkbox.isChecked()
        
        settings.custom_addons = [
            custom_addons_list.item(i).text()
            for i in range(custom_addons_list.count())
        ]
        
        popup.accept()
    
    # Buttons
    popup.add_spacer()
    popup.add_button("Cancel", popup.reject, False)
    popup.add_button("Save", on_save, True)
    
    return popup.exec()
