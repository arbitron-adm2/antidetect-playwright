"""Dolphin Anty-style dark theme styles."""

# Color palette (Dolphin Anty inspired)
COLORS = {
    # Background
    "bg_primary": "#1a1a1a",
    "bg_secondary": "#161616",
    "bg_tertiary": "#232323",
    "bg_hover": "#2a2a2a",
    "bg_selected": "#3a3a3a",
    # Accent
    "accent": "#888888",
    "accent_hover": "#a0a0a0",
    "accent_light": "#707070",
    # Status colors
    "success": "#4ade80",
    "warning": "#fbbf24",
    "error": "#f87171",
    "info": "#60a5fa",
    # Text
    "text_primary": "#ffffff",
    "text_secondary": "#9ca3af",
    "text_muted": "#6b7280",
    # Border
    "border": "#2e2e2e",
    "border_light": "#3e3e3e",
    # Tags
    "tag_bg": "#2a2a2a",
    "tag_text": "#d1d5db",
}


def get_stylesheet() -> str:
    """Get complete application stylesheet."""
    return f"""
    /* Main Window */
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}
    
    QWidget {{
        background-color: transparent;
        color: {COLORS['text_primary']};
        font-family: system-ui, "Segoe UI", "SF Pro Text", -apple-system, sans-serif;
        font-size: 13px;
    }}
    
    /* Sidebar */
    #sidebar {{
        background-color: {COLORS['bg_secondary']};
        border-right: 1px solid {COLORS['border']};
    }}
    
    #sidebar QLabel {{
        color: {COLORS['text_secondary']};
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 8px 16px 4px 16px;
    }}
    
    /* Folder list items */
    .folder-item {{
        background-color: transparent;
        border-radius: 4px;
        padding: 8px 12px;
        margin: 2px 8px;
    }}
    
    .folder-item:hover {{
        background-color: {COLORS['bg_hover']};
    }}
    
    .folder-item.selected {{
        background-color: {COLORS['accent']};
    }}
    
    /* Main content area */
    #content {{
        background-color: {COLORS['bg_primary']};
    }}
    
    /* Header */
    #header {{
        background-color: {COLORS['bg_tertiary']};
        border-bottom: 1px solid {COLORS['border']};
        padding: 12px 16px;
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 6px 14px;
        font-weight: 500;
        font-size: 13px;
    }}
    
    QPushButton:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['border_light']};
    }}
    
    QPushButton:pressed {{
        background-color: {COLORS['bg_selected']};
    }}
    
    QPushButton.primary {{
        background-color: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}
    
    QPushButton.primary:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    
    QPushButton.icon-btn {{
        padding: 6px;
        min-width: 32px;
        max-width: 32px;
    }}
    
    QPushButton.start-btn {{
        background-color: {COLORS['success']};
        border-color: {COLORS['success']};
        color: white;
    }}
    
    QPushButton.start-btn:hover {{
        background-color: #16a34a;
    }}
    
    QPushButton.stop-btn {{
        background-color: {COLORS['error']};
        border-color: {COLORS['error']};
        color: white;
    }}
    
    QPushButton.stop-btn:hover {{
        background-color: #dc2626;
    }}
    
    /* Search input */
    QLineEdit {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 6px 12px;
        font-size: 13px;
    }}
    
    QLineEdit:focus {{
        border-color: {COLORS['accent']};
    }}
    
    QLineEdit::placeholder {{
        color: {COLORS['text_muted']};
    }}
    
    /* Table */
    QTableWidget {{
        background-color: {COLORS['bg_primary']};
        alternate-background-color: {COLORS['bg_tertiary']};
        border: none;
        gridline-color: {COLORS['border']};
    }}
    
    QTableWidget::item {{
        padding: 8px 12px;
        border-bottom: 1px solid {COLORS['border']};
    }}
    
    QTableWidget::item:selected {{
        background-color: {COLORS['bg_selected']};
    }}
    
    QTableWidget::item:hover {{
        background-color: {COLORS['bg_hover']};
    }}
    
    QHeaderView::section {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border: none;
        border-bottom: 1px solid {COLORS['border']};
        padding: 10px 12px;
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
    }}
    
    /* Scrollbars */
    QScrollBar:vertical {{
        background-color: {COLORS['bg_primary']};
        width: 8px;
        border-radius: 4px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {COLORS['border_light']};
        border-radius: 4px;
        min-height: 40px;
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}
    
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    
    /* ComboBox */
    QComboBox {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 5px 10px;
        min-width: 60px;
        font-size: 13px;
    }}
    
    QComboBox:hover {{
        border-color: {COLORS['border_light']};
    }}
    
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    
    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['accent']};
    }}
    
    /* SpinBox */
    QSpinBox {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 6px 12px;
    }}
    
    /* Status badges */
    .status-running {{
        background-color: {COLORS['success']};
        color: white;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    .status-stopped {{
        background-color: {COLORS['text_muted']};
        color: white;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    .status-error {{
        background-color: {COLORS['error']};
        color: white;
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 11px;
        font-weight: 600;
    }}
    
    /* Tags */
    .tag {{
        background-color: {COLORS['tag_bg']};
        color: {COLORS['tag_text']};
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 11px;
        margin-right: 4px;
    }}
    
    /* Footer */
    #footer {{
        background-color: {COLORS['bg_secondary']};
        border-top: 1px solid {COLORS['border']};
        padding: 8px 16px;
    }}
    
    /* Dialog */
    QDialog {{
        background-color: {COLORS['bg_tertiary']};
    }}
    
    QDialog QLabel {{
        color: {COLORS['text_primary']};
    }}
    
    /* GroupBox */
    QGroupBox {{
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 12px;
    }}
    
    QGroupBox::title {{
        color: {COLORS['text_secondary']};
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 4px;
    }}
    
    /* TextEdit */
    QTextEdit {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 8px;
    }}
    
    /* Menu */
    QMenu {{
        background-color: {COLORS['bg_tertiary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 4px;
    }}
    
    QMenu::item {{
        padding: 8px 24px;
        border-radius: 4px;
    }}
    
    QMenu::item:selected {{
        background-color: {COLORS['accent']};
    }}
    
    /* ToolTip */
    QToolTip {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    
    /* Checkbox */
    QCheckBox {{
        color: {COLORS['text_primary']};
    }}
    
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 1px solid {COLORS['border']};
        background-color: {COLORS['bg_tertiary']};
    }}
    
    QCheckBox::indicator:checked {{
        background-color: {COLORS['accent']};
        border-color: {COLORS['accent']};
    }}
    """


# OS icons (text - emoji cause segfault on some systems)
OS_ICONS = {
    "windows": "[win]",
    "macos": "[mac]",
    "linux": "[lnx]",
}


def get_country_flag(country_code: str) -> str:
    """Get flag emoji for ISO 3166-1 alpha-2 country code.

    Converts country code to Unicode Regional Indicator Symbols.
    Example: "US" -> 🇺🇸, "DE" -> 🇩🇪

    Works for all 249 ISO 3166-1 alpha-2 codes.
    """
    if not country_code or len(country_code) != 2:
        return "🌐"
    code = country_code.upper()
    # Regional Indicator Symbol base: 🇦 = U+1F1E6
    # Each letter A-Z maps to U+1F1E6 through U+1F1FF
    try:
        flag = "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code)
        return flag
    except (ValueError, TypeError):
        return "🌐"
