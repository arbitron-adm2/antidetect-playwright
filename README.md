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

## Структура данных

```
data/
├── profiles.json         # Браузерные профили (пароли прокси зашифрованы AES-128)
├── proxy_pool.json       # Пул прокси-серверов
├── folders.json          # Организация папок
├── settings.json         # Настройки приложения
├── browser_data/         # Профили браузеров (cookies, localStorage)
└── screenshots/          # Скриншоты
```

Все данные сохраняются локально в папке `data/`.

**Безопасность:** Пароли прокси автоматически шифруются с использованием Fernet (AES-128). Ключ шифрования хранится в `~/.encryption_key` с правами доступа `0600`.

## Docker

```bash
docker-compose up -d
```

Настройки в `.env` файле.

## Безопасность

- ✅ **Шифрование паролей:** Пароли прокси защищены AES-128 (Fernet)
- ✅ **Валидация данных:** Автоматическая проверка корректности прокси
- ✅ **Безопасное хранение:** Ключи шифрования с ограниченными правами доступа
- ✅ **Защита логов:** Автоматическая фильтрация чувствительных данных

См. [GUI_SECURITY_IMPROVEMENTS.md](GUI_SECURITY_IMPROVEMENTS.md) для деталей.

## Обновление

```bash
pip install -e ".[gui]"
```

См. [UPDATE_GUIDE.md](UPDATE_GUIDE.md) для инструкций по миграции.

## Лицензия

MIT
