"""GUI package for antidetect browser."""

import os

# Suppress Qt accessibility warnings on Linux (must be before PyQt6 import)
os.environ["QT_ACCESSIBILITY"] = "0"

__all__ = ["main"]


def main():
    """Import and run main function lazily to avoid import issues."""
    from .app import main as _main

    _main()
