"""SVG icons for GUI."""

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray

# Icon color for dark theme - brighter for visibility
ICON_COLOR = "#d4d4d8"  # Lighter gray for better visibility on dark theme


def svg_icon(svg_data: str, size: int = 16, color: str = None) -> QIcon:
    """Create QIcon from SVG string with proper color for dark theme."""
    # Replace currentColor with actual color
    actual_color = color or ICON_COLOR
    colored_svg = svg_data.replace("currentColor", actual_color)

    renderer = QSvgRenderer(QByteArray(colored_svg.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)  # Transparent background
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# === Action Icons ===

ICON_EDIT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
</svg>"""

ICON_PLAY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
<polygon points="5,3 19,12 5,21"/>
</svg>"""

ICON_STOP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
<rect x="4" y="4" width="16" height="16" rx="2"/>
</svg>"""

ICON_DELETE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M3 6h18"/>
<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/>
<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
</svg>"""

ICON_REFRESH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M23 4v6h-6"/>
<path d="M1 20v-6h6"/>
<path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
</svg>"""

ICON_PING = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M5 12.55a11 11 0 0 1 14.08 0"/>
<path d="M1.42 9a16 16 0 0 1 21.16 0"/>
<path d="M8.53 16.11a6 6 0 0 1 6.95 0"/>
<circle cx="12" cy="20" r="1"/>
</svg>"""

ICON_SWAP = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M16 3l4 4-4 4"/>
<path d="M20 7H4"/>
<path d="M8 21l-4-4 4-4"/>
<path d="M4 17h16"/>
</svg>"""

ICON_PLUS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<line x1="12" y1="5" x2="12" y2="19"/>
<line x1="5" y1="12" x2="19" y2="12"/>
</svg>"""

ICON_FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
</svg>"""

ICON_FOLDER_OPEN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2v1"/>
<path d="M4 10h16l-2 9H6z"/>
</svg>"""

ICON_TAG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/>
<circle cx="7" cy="7" r="1"/>
</svg>"""

ICON_SETTINGS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<circle cx="12" cy="12" r="3"/>
<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
</svg>"""

ICON_PROXY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<circle cx="12" cy="12" r="10"/>
<line x1="2" y1="12" x2="22" y2="12"/>
<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
</svg>"""

ICON_CHEVRON_LEFT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<polyline points="15 18 9 12 15 6"/>
</svg>"""

ICON_CHEVRON_RIGHT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<polyline points="9 18 15 12 9 6"/>
</svg>"""

ICON_SEARCH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<circle cx="11" cy="11" r="8"/>
<line x1="21" y1="21" x2="16.65" y2="16.65"/>
</svg>"""

ICON_COPY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
</svg>"""

ICON_NOTE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
<polyline points="14 2 14 8 20 8"/>
<line x1="16" y1="13" x2="8" y2="13"/>
<line x1="16" y1="17" x2="8" y2="17"/>
</svg>"""

ICON_CLOSE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<line x1="18" y1="6" x2="6" y2="18"/>
<line x1="6" y1="6" x2="18" y2="18"/>
</svg>"""

ICON_CHECK = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<polyline points="20 6 9 17 4 12"/>
</svg>"""

ICON_TRASH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<polyline points="3 6 5 6 21 6"/>
<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
<line x1="10" y1="11" x2="10" y2="17"/>
<line x1="14" y1="11" x2="14" y2="17"/>
</svg>"""

ICON_RESTORE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
<path d="M3 3v5h5"/>
</svg>"""

ICON_USER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
<circle cx="12" cy="7" r="4"/>
</svg>"""

ICON_STATUS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
<rect x="3" y="3" width="7" height="7"/>
<rect x="14" y="3" width="7" height="7"/>
<rect x="14" y="14" width="7" height="7"/>
<rect x="3" y="14" width="7" height="7"/>
</svg>"""

ICON_WINDOWS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
<path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801"/>
</svg>"""

ICON_APPLE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
<path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
</svg>"""

ICON_LINUX = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
<path d="M20.8 18.4c0 .1-.1.2-.2.3-1 1.7-3.7 2.9-6.6 3.1h-.1c-.1 0-.2-.1-.2-.2s.1-.2.2-.2c2.8-.2 5.4-1.3 6.3-2.9.1-.1.2-.2.3-.1.2 0 .3.1.3.2zm-10.5.3c.1 0 .2.1.2.2s-.1.2-.2.2h-.1c-2.9-.2-5.6-1.4-6.6-3.1-.1-.1-.1-.2 0-.3.1-.1.2-.1.3-.1.9 1.6 3.5 2.7 6.3 2.9.1.1.1.1.1.2zM12 0c-.7 0-1.2.5-1.2 1.2v1.5C10.2 2.9 9.6 3 9 3c-.1 0-.2.1-.2.2s.1.2.2.2c.7 0 1.3-.1 1.9-.3.1 0 .1-.1.1-.1v-1.8c0-.5.4-.9.9-.9s.9.4.9.9V3c0 .1.1.2.2.2s.2-.1.2-.2V1.2c.1-.7-.4-1.2-1.2-1.2zm6.6 8.4c-.1 0-.2.1-.2.2s.1.2.2.2c.1 0 .2-.1.2-.2s-.1-.2-.2-.2zM5.4 8.4c-.1 0-.2.1-.2.2s.1.2.2.2.2-.1.2-.2-.1-.2-.2-.2zm7.8-3.3c-2 0-3.7 1.5-4 3.5-.2 1.5.5 2.9 1.7 3.7-.1.3-.2.6-.2 1 0 .8.5 1.5 1.2 1.8v1.4c0 .4.3.7.7.7s.7-.3.7-.7v-1.4c.7-.3 1.2-1 1.2-1.8 0-.3-.1-.6-.2-1 1.2-.8 1.9-2.2 1.7-3.7-.3-2-2-3.5-4-3.5zm0 .5c1.8 0 3.2 1.3 3.5 3.1.2 1.3-.4 2.5-1.5 3.2-.1 0-.1.1-.1.2.1.3.2.5.2.8 0 .6-.4 1.1-1 1.4-.1 0-.1.1-.1.2v1.6c0 .3-.2.5-.5.5s-.5-.2-.5-.5v-1.6c0-.1 0-.1-.1-.2-.6-.3-1-1-.8-1.6 0-.3.1-.5.2-.8 0-.1 0-.1-.1-.2-1.1-.7-1.7-1.9-1.5-3.2.3-1.8 1.7-3.1 3.5-3.1z"/>
</svg>"""


def get_icon(name: str, size: int = 16, color: str = None) -> QIcon:
    """Get icon by name with optional color override."""
    icons = {
        "edit": ICON_EDIT,
        "play": ICON_PLAY,
        "stop": ICON_STOP,
        "delete": ICON_DELETE,
        "refresh": ICON_REFRESH,
        "ping": ICON_PING,
        "swap": ICON_SWAP,
        "plus": ICON_PLUS,
        "folder": ICON_FOLDER,
        "folder_open": ICON_FOLDER_OPEN,
        "tag": ICON_TAG,
        "settings": ICON_SETTINGS,
        "proxy": ICON_PROXY,
        "chevron_left": ICON_CHEVRON_LEFT,
        "chevron_right": ICON_CHEVRON_RIGHT,
        "search": ICON_SEARCH,
        "copy": ICON_COPY,
        "note": ICON_NOTE,
        "close": ICON_CLOSE,
        "check": ICON_CHECK,
        "trash": ICON_TRASH,
        "restore": ICON_RESTORE,
        "user": ICON_USER,
        "status": ICON_STATUS,
        "windows": ICON_WINDOWS,
        "apple": ICON_APPLE,
        "linux": ICON_LINUX,
    }
    svg_data = icons.get(name, ICON_EDIT)
    return svg_icon(svg_data, size, color)
