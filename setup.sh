#!/bin/bash
# Quick setup script for Linux/macOS

set -e

echo "=== Antidetect Playwright Setup ==="
echo

# Check Python
if ! command -v python3.12 &> /dev/null; then
    echo "ERROR: Python 3.12 not found. Install Python 3.12 or higher."
    exit 1
fi

# Create venv
echo "Creating virtual environment..."
python3.12 -m venv .venv

# Activate venv
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install package
echo "Installing antidetect-playwright with GUI..."
pip install -e ".[gui]"

# Install playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

# Copy .env if not exists
if [ ! -f .env ]; then
    echo "Copying .env.example to .env..."
    cp .env.example .env
fi

echo
echo "=== Setup complete! ==="
echo
echo "To start the GUI:"
echo "  source .venv/bin/activate"
echo "  antidetect-browser"
echo
