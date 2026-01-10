"""Entry point for antidetect browser GUI."""

import os
import sys

# Suppress Qt accessibility warnings on Linux
os.environ["QT_ACCESSIBILITY"] = "0"
os.environ["QT_LOGGING_RULES"] = "qt.accessibility.atspi=false"

from .app import main

if __name__ == "__main__":
    sys.exit(main())
