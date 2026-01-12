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

## Обновление

После обновления версии Camoufox (например, с FF146 на FF135) рекомендуется очистить старые fingerprints:

```bash
# Удалить fingerprint.json из всех профилей
find data/browser_data -name "fingerprint.json" -delete
```

Это гарантирует, что все профили будут использовать актуальную версию Firefox и соответствующие fingerprints.

## Возможности

- ✅ Автоматическая генерация и сохранение fingerprints
- ✅ GeoIP определение таймзоны и страны (с прокси и без)
- ✅ Флаги стран в интерфейсе
- ✅ Camoufox Firefox 135 (стабильная версия)
- ✅ Полная изоляция профилей
- ✅ Синхронизация вкладок между сессиями

