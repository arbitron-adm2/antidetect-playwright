# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Antidetect Browser GUI."""

import sys
from pathlib import Path
import site

block_cipher = None

# Project paths
project_root = Path(SPECPATH)
src_dir = project_root / "src"
resources_dir = src_dir / "antidetect_playwright/resources"
icon_path = project_root / "build/icons"

# Find browserforge data directory
site_packages = Path(site.getsitepackages()[0])
browserforge_data = site_packages / "browserforge"
camoufox_pkg = site_packages / "camoufox"
language_tags_pkg = site_packages / "language_tags"

# Platform-specific icon and version info
if sys.platform == "win32":
    icon_file = str(icon_path / "icon.ico")
    # Version info for Windows executable
    version_info = (
        "0.1.0",  # FileVersion
        "0.1.0",  # ProductVersion
        "Antidetect Browser",  # FileDescription
        "Antidetect Browser",  # ProductName
        "Antidetect Team",  # CompanyName
        "© 2024 Antidetect Team",  # LegalCopyright
    )
elif sys.platform == "darwin":
    icon_file = str(icon_path / "icon.icns")
    version_info = None
else:
    icon_file = None
    version_info = None

# Collect all resource files
datas = [
    (str(resources_dir / "chrome"), "antidetect_playwright/resources/chrome"),
    (str(resources_dir / "icon.svg"), "antidetect_playwright/resources"),
    # Browserforge data files
    (str(browserforge_data / "fingerprints/data"), "browserforge/fingerprints/data"),
    (str(browserforge_data / "headers/data"), "browserforge/headers/data"),
    # Camoufox data files (include all)
    (str(camoufox_pkg), "camoufox"),
    # Language tags data
    (str(language_tags_pkg / "data"), "language_tags/data"),
]

# Hidden imports (packages not auto-detected)
hiddenimports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtSvg',
    'qasync',
    'camoufox',
    'camoufox.async_api',
    'camoufox.ip',
    'camoufox.locale',
    'camoufox.fingerprints',
    'camoufox.webgl',
    'browserforge',
    'browserforge.fingerprints',
    'playwright',
    'playwright.async_api',
    'aiohttp',
    'aiohttp_socks',
    'cryptography',
    'orjson',
]

a = Analysis(
    [str(src_dir / "antidetect_playwright/gui/launcher_pyinstaller.py")],
    pathex=[str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'scipy',
        'PIL.ImageQt',  # Exclude unused PIL modules
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AntidetectBrowser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version='build/version_info.txt' if sys.platform == "win32" else None,
    manifest='build/windows_manifest.xml' if sys.platform == "win32" else None,
    uac_admin=False,  # Don't require admin rights
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AntidetectBrowser',
)

# macOS app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name='AntidetectBrowser.app',
        icon=icon_file,
        bundle_identifier='com.antidetect.browser',
        info_plist={
            'CFBundleName': 'Antidetect Browser',
            'CFBundleDisplayName': 'Antidetect Browser',
            'CFBundleVersion': '0.1.0',
            'CFBundleShortVersionString': '0.1.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15.0',
        },
    )
