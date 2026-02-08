# Application Icons

This directory contains all SVG icons for the Antidetect Browser Launcher application.

## Main Application Icons

### Design Philosophy

Icons are designed in **Chrome browser style** with monochromatic grey/black tones:
- Circular shape with 3 characteristic segments (120° arcs each)
- Central circle for depth and recognizability
- Gradient shading for 3D effect
- Professional, modern appearance

### Icon Files

#### `app-icon.svg` (512×512)
- **Usage:** Main application icon, installer, desktop shortcuts
- **Design:** Chrome-style circular icon with 3 segments
- **Colors:** Grayscale gradients (#1a1a1a → #666666)
- **Details:** Full gradients, shadows, borders

#### `app-icon-256.svg` (256×256)
- **Usage:** Taskbar, window icon, medium-resolution displays
- **Design:** Same Chrome style, optimized for medium size
- **Details:** Simplified gradients, clear segments

#### `app-icon-64.svg` (64×64)
- **Usage:** Small icons, file associations, alt+tab
- **Design:** Essential Chrome elements only
- **Details:** Minimal details for clarity at small sizes

## System Tray Icons

### `tray-icon.svg` (22×22)
- **Usage:** System tray/notification area
- **Format:** Monochrome SVG using `currentColor`
- **Theme:** Adapts to system theme (light/dark automatically)
- **Design:** Simplified Chrome-style circle with segments
- **Opacity:** Different opacity levels for segment depth

## Converting to Raster Formats

### For Windows (.ico)

Use ImageMagick or Inkscape to generate multi-resolution ICO:

```bash
# Generate PNG at multiple sizes
inkscape app-icon.svg -w 16 -h 16 -o icon-16.png
inkscape app-icon.svg -w 32 -h 32 -o icon-32.png
inkscape app-icon.svg -w 48 -h 48 -o icon-48.png
inkscape app-icon.svg -w 64 -h 64 -o icon-64.png
inkscape app-icon.svg -w 128 -h 128 -o icon-128.png
inkscape app-icon.svg -w 256 -h 256 -o icon-256.png

# Combine into ICO
convert icon-16.png icon-32.png icon-48.png icon-64.png icon-128.png icon-256.png app-icon.ico
```

### For macOS (.icns)

```bash
# Generate PNG at required sizes
mkdir app-icon.iconset
inkscape app-icon.svg -w 16 -h 16 -o app-icon.iconset/icon_16x16.png
inkscape app-icon.svg -w 32 -h 32 -o app-icon.iconset/icon_16x16@2x.png
inkscape app-icon.svg -w 32 -h 32 -o app-icon.iconset/icon_32x32.png
inkscape app-icon.svg -w 64 -h 64 -o app-icon.iconset/icon_32x32@2x.png
inkscape app-icon.svg -w 128 -h 128 -o app-icon.iconset/icon_128x128.png
inkscape app-icon.svg -w 256 -h 256 -o app-icon.iconset/icon_128x128@2x.png
inkscape app-icon.svg -w 256 -h 256 -o app-icon.iconset/icon_256x256.png
inkscape app-icon.svg -w 512 -h 512 -o app-icon.iconset/icon_256x256@2x.png
inkscape app-icon.svg -w 512 -h 512 -o app-icon.iconset/icon_512x512.png
inkscape app-icon.svg -w 1024 -h 1024 -o app-icon.iconset/icon_512x512@2x.png

# Convert to ICNS
iconutil -c icns app-icon.iconset
```

### For Linux (.png)

```bash
# Generate standard sizes for Linux desktops
inkscape app-icon.svg -w 16 -h 16 -o app-icon-16.png
inkscape app-icon.svg -w 22 -h 22 -o app-icon-22.png
inkscape app-icon.svg -w 24 -h 24 -o app-icon-24.png
inkscape app-icon.svg -w 32 -h 32 -o app-icon-32.png
inkscape app-icon.svg -w 48 -h 48 -o app-icon-48.png
inkscape app-icon.svg -w 64 -h 64 -o app-icon-64.png
inkscape app-icon.svg -w 128 -h 128 -o app-icon-128.png
inkscape app-icon.svg -w 256 -h 256 -o app-icon-256.png
inkscape app-icon.svg -w 512 -h 512 -o app-icon-512.png
```

## Icon Usage in Code

### PyQt6 Application Icon

```python
from PyQt6.QtGui import QIcon
from pathlib import Path

# Load SVG icon
icon_path = Path(__file__).parent / "assets" / "icons" / "app-icon.svg"
app_icon = QIcon(str(icon_path))

# Set application icon
app.setWindowIcon(app_icon)
```

### System Tray Icon

```python
from PyQt6.QtWidgets import QSystemTrayIcon
from PyQt6.QtGui import QIcon

# Load monochrome tray icon
tray_icon_path = Path(__file__).parent / "assets" / "icons" / "tray-icon.svg"
tray_icon = QIcon(str(tray_icon_path))

# Create system tray
tray = QSystemTrayIcon(tray_icon)
tray.show()
```

## Design Guidelines

### Color Scheme
- **Primary Gradient:** #6366f1 (Indigo) → #8b5cf6 (Purple)
- **Accent:** White with opacity for layering
- **Theme:** Professional, modern, tech-focused

### Visual Elements
1. **Browser Window:** Represents web browser functionality
2. **Fingerprint:** Symbolizes antidetect/privacy features
3. **Shield Badge:** Security and protection

### Size Guidelines
- **512×512:** Full detail with shadows and effects
- **256×256:** Simplified effects, clear details
- **64×64:** Essential elements only
- **22×22:** Monochrome outline for system tray

## Automated Icon Generation

The project includes a build script for automated icon generation:

**Location:** `build/generate_icons.py`

**Usage:**
```bash
python build/generate_icons.py
```

**Generates:**
- Multi-resolution ICO for Windows
- ICNS for macOS
- PNG set for Linux
- Optimized for PyInstaller bundling

## PyInstaller Integration

### Windows
```python
# In .spec file
a = Analysis(
    ...
    icon='assets/icons/app-icon.ico'
)
```

### macOS
```python
# In .spec file
app = BUNDLE(
    ...
    icon='assets/icons/app-icon.icns'
)
```

### Linux
Icons are automatically installed via desktop entry:
```ini
[Desktop Entry]
Icon=antidetect-browser
```

PNGs are installed to: `/usr/share/icons/hicolor/{size}/apps/`

## License

These icons are part of the Antidetect Browser Launcher project.

## Credits

- Design: Custom SVG icons for Antidetect Browser Launcher
- Tools: Created with SVG standards, compatible with all modern browsers
- Optimization: Hand-optimized SVG for minimal file size
