@echo off
REM Quick setup script for Windows

echo === Antidetect Playwright Setup ===
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.12 or higher from python.org
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if Python version is 3.12+
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo Found Python version: %PYVER%

REM Create venv
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment.
    echo Make sure Python 3.12+ is installed with venv support.
    pause
    exit /b 1
)

REM Activate venv
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel

REM Install package with GUI
echo Installing antidetect-playwright with GUI dependencies...
pip install -e ".[gui]"
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

REM Install Camoufox (not Playwright)
echo Camoufox will be installed automatically on first launch.

REM Create data directories
echo Creating data directories...
if not exist data\browser_data mkdir data\browser_data

echo.
echo === Setup complete! ===
echo.
echo To start the GUI:
echo   .venv\Scripts\activate
echo   antidetect-browser
echo.
echo On first launch, Camoufox browser will be downloaded automatically.
echo.
pause
