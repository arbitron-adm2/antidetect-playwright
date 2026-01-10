@echo off
REM Quick setup script for Windows

echo === Antidetect Playwright Setup ===
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12 or higher.
    exit /b 1
)

REM Create venv
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    exit /b 1
)

REM Activate venv
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip setuptools wheel

REM Install package
echo Installing antidetect-playwright with GUI...
pip install -e ".[gui]"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    exit /b 1
)

REM Install playwright browsers
echo Installing Playwright browsers...
playwright install chromium

REM Copy .env if not exists
if not exist .env (
    echo Copying .env.example to .env...
    copy .env.example .env
)

echo.
echo === Setup complete! ===
echo.
echo To start the GUI:
echo   .venv\Scripts\activate
echo   antidetect-browser
echo.
