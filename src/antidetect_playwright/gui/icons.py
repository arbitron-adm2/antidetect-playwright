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
<path d="M12.504 0c-.155 0-.311.001-.465.003-.653.014-1.31.052-1.96.124-.11.012-.218.027-.326.04-.18.022-.359.047-.536.076-.174.029-.347.062-.518.099-.171.037-.339.078-.506.123-.164.045-.326.094-.486.147-.158.053-.315.11-.469.171-.153.061-.304.126-.451.195-.147.07-.291.143-.431.22-.14.077-.277.158-.41.243-.133.085-.262.174-.387.267-.125.093-.246.19-.362.29-.117.1-.228.204-.335.312-.107.107-.208.219-.305.334-.097.115-.189.234-.275.357-.086.123-.167.25-.242.38-.075.13-.144.264-.207.401-.063.137-.12.278-.17.421-.051.143-.095.29-.133.439-.037.149-.068.3-.092.454-.024.153-.041.309-.051.466C5.009 4.908 5 5.07 5 5.233c0 .163.009.325.027.486.018.161.044.321.079.479.034.158.077.314.127.468.05.153.108.304.173.453.065.148.138.294.217.437.079.143.165.284.258.421.093.137.192.271.298.401.106.13.218.257.336.38.118.123.242.242.372.357.13.115.265.226.406.333.14.107.286.21.436.309.15.098.305.193.463.282.158.09.321.175.487.255.166.08.336.156.509.227.173.071.35.138.529.2.179.062.361.12.546.172.185.052.373.1.562.143.19.042.382.08.575.112.193.032.388.06.584.082.196.022.393.04.591.053.199.013.398.021.598.025.2.004.4.003.6-.003.2-.006.4-.017.599-.033.199-.016.398-.038.596-.065.198-.027.395-.059.59-.096.196-.037.39-.08.582-.127.192-.047.382-.1.57-.158.188-.057.374-.12.557-.187.183-.068.364-.141.541-.219.177-.078.352-.16.523-.248.171-.088.339-.181.503-.278.164-.098.324-.2.48-.308.156-.107.309-.22.456-.337.147-.117.291-.239.429-.365.139-.127.273-.258.402-.394.129-.135.253-.276.372-.42.118-.144.232-.293.339-.446.107-.152.209-.309.305-.469.095-.161.185-.325.268-.494.083-.168.16-.34.23-.515.07-.175.134-.354.191-.536.057-.182.107-.367.15-.555.043-.188.079-.379.108-.572.029-.193.051-.388.066-.585.014-.197.022-.396.022-.596s-.008-.399-.022-.596c-.015-.197-.037-.392-.066-.585-.029-.193-.065-.384-.108-.572-.043-.188-.093-.373-.15-.555-.057-.182-.121-.361-.191-.536-.07-.175-.147-.347-.23-.515-.083-.169-.173-.333-.268-.494-.096-.16-.198-.317-.305-.469-.107-.153-.221-.302-.339-.446-.119-.144-.243-.285-.372-.42-.129-.136-.263-.267-.402-.394-.138-.126-.282-.248-.429-.365-.147-.117-.3-.23-.456-.337-.156-.108-.316-.21-.48-.308-.164-.097-.332-.19-.503-.278-.171-.088-.346-.17-.523-.248-.177-.078-.358-.151-.541-.219-.183-.067-.369-.13-.557-.187-.188-.058-.378-.111-.57-.158-.192-.047-.386-.09-.582-.127-.195-.037-.392-.069-.59-.096-.198-.027-.397-.049-.596-.065-.199-.016-.399-.027-.599-.033-.2-.006-.4-.007-.6-.003-.2.004-.399.012-.598.025-.198.013-.395.031-.591.053-.196.022-.391.05-.584.082-.193.032-.385.07-.575.112-.189.043-.377.091-.562.143-.185.052-.367.11-.546.172-.179.062-.356.129-.529.2-.173.071-.343.147-.509.227-.166.08-.329.165-.487.255-.158.089-.313.184-.463.282-.15.099-.296.202-.436.309-.141.107-.276.218-.406.333-.13.115-.254.234-.372.357-.118.123-.23.25-.336.38-.106.13-.205.264-.298.401-.093.137-.179.278-.258.421-.079.143-.152.289-.217.437-.065.149-.123.3-.173.453-.05.154-.093.31-.127.468-.035.158-.061.318-.079.479-.018.161-.027.323-.027.486 0 .163.009.325.027.486.018.161.044.321.079.479.034.158.077.314.127.468.05.153.108.304.173.453.065.148.138.294.217.437.079.143.165.284.258.421.093.137.192.271.298.401.106.13.218.257.336.38.118.123.242.242.372.357.13.115.265.226.406.333.14.107.286.21.436.309.15.098.305.193.463.282.158.09.321.175.487.255.166.08.336.156.509.227.173.071.35.138.529.2.179.062.361.12.546.172.185.052.373.1.562.143.19.042.382.08.575.112.193.032.388.06.584.082.196.022.393.04.591.053.199.013.398.021.598.025.1.002.2.003.3.003z"/>
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
