"""Dolphin Anty-style dark theme styles.

DEPRECATED: This module is deprecated. Use theme.py instead.
This file is kept for backward compatibility only.
"""

# Import from unified theme system
from .theme import COLORS as _COLORS, Theme

# Legacy COLORS dictionary for backward compatibility
COLORS = {
    "bg_primary": _COLORS.bg_primary,
    "bg_secondary": _COLORS.bg_secondary,
    "bg_tertiary": _COLORS.bg_tertiary,
    "bg_hover": _COLORS.bg_hover,
    "bg_selected": _COLORS.bg_selected,
    "accent": _COLORS.accent,
    "accent_hover": _COLORS.accent_hover,
    "accent_light": _COLORS.accent_light,
    "success": _COLORS.success,
    "warning": _COLORS.warning,
    "error": _COLORS.error,
    "info": _COLORS.info,
    "text_primary": _COLORS.text_primary,
    "text_secondary": _COLORS.text_secondary,
    "text_muted": _COLORS.text_muted,
    "border": _COLORS.border,
    "border_light": _COLORS.border_light,
    "tag_bg": _COLORS.tag_bg,
    "tag_text": _COLORS.tag_text,
}


def get_stylesheet() -> str:
    """Get complete application stylesheet.

    DEPRECATED: Use Theme.get_stylesheet() instead.
    """
    return Theme.get_stylesheet()


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

