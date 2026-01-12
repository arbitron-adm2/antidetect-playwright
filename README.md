# Antidetect Playwright

Антидетект браузер с графическим интерфейсом на основе Camoufox.

## Требования

- Python 3.12 или выше
- Git

## Быстрая установка

### Linux / macOS

```bash
git clone https://github.com/arbitron-adm2/antidetect-playwright.git
cd antidetect-playwright
./setup.sh
```

### Windows

```cmd
git clone https://github.com/arbitron-adm2/antidetect-playwright.git
cd antidetect-playwright
setup.bat
```

## Ручная установка

### Linux / macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[gui]"
playwright install chromium
```

### Windows

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[gui]"
playwright install chromium
```

## Запуск

```bash
antidetect-browser
```
