# Antidetect Playwright

Антидетект браузер с графическим интерфейсом на основе Camoufox.

## Требования

- Python 3.12 или выше
- Git

## Быстрая установка

### Linux / macOS

```bash
git clone https://github.com/antidetect/antidetect-playwright.git
cd antidetect-playwright
./setup.sh
```

### Windows

```cmd
git clone https://github.com/antidetect/antidetect-playwright.git
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

## Структура данных

```
data/
├── profiles.json         # Браузерные профили
├── proxy_pool.json       # Пул прокси-серверов
├── folders.json          # Организация папок
├── settings.json         # Настройки приложения
├── browser_data/         # Профили браузеров (cookies, localStorage)
└── screenshots/          # Скриншоты
```

Все данные сохраняются локально в папке `data/`.

## Docker

```bash
docker-compose up -d
```

Настройки в `.env` файле.

## Лицензия

MIT
