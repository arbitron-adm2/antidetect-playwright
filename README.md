# Antidetect Browser

Stealth browser with anti-detection. PyQt6 GUI + Camoufox engine.

## Download

**[v0.1.0](https://github.com/arbitron-adm2/antidetect-playwright/releases/tag/v0.1.0)** — Linux only

| File | Size | Install |
|------|------|---------|
| [antidetect-browser_0.1.0_amd64.deb](https://github.com/arbitron-adm2/antidetect-playwright/releases/download/v0.1.0/antidetect-browser_0.1.0_amd64.deb) | 125 MB | `sudo dpkg -i antidetect-browser_0.1.0_amd64.deb` |
| [AntidetectBrowser-Linux-x86_64.tar.gz](https://github.com/arbitron-adm2/antidetect-playwright/releases/download/v0.1.0/AntidetectBrowser-Linux-x86_64.tar.gz) | 161 MB | Extract → `./AntidetectBrowser` |

## Features

- **Fingerprint spoofing** — Canvas, WebGL, fonts, timezone, geolocation
- **Proxy support** — HTTP/HTTPS/SOCKS5
- **Profile management** — save/restore sessions, tags, labels
- **Batch operations** — start/stop/ping multiple profiles
- **System tray** — minimize to tray, running count
- **Dark theme GUI** — Dolphin Anty style

## From source

```bash
git clone https://github.com/arbitron-adm2/antidetect-playwright.git
cd antidetect-playwright
pip install -e ".[gui]"
antidetect-browser
```

Requires Python 3.12+.

## Data locations

| Mode | Path |
|------|------|
| Dev (from source) | `./data/` |
| Installed — Linux | `~/.local/share/antidetect-browser/` |
| Installed — Windows | `%APPDATA%\AntidetectBrowser\` |
| Installed — macOS | `~/Library/Application Support/AntidetectBrowser/` |

## License

MIT
