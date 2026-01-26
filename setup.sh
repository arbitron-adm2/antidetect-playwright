#!/bin/bash
# Quick setup script for Linux/macOS

set -e

echo "=== Antidetect Playwright Setup ==="
echo

# Check Python version
if ! command -v python3.12 &> /dev/null; then
    if ! command -v python3 &> /dev/null; then
        echo "ERROR: Python 3.12+ not found. Install Python 3.12 or higher."
        exit 1
    fi
    # Check if python3 is 3.12+
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ "$(echo "$PYTHON_VERSION < 3.12" | bc -l)" -eq 1 ]]; then
        echo "ERROR: Python $PYTHON_VERSION found, but 3.12+ required."
        exit 1
    fi
    PYTHON_CMD=python3
else
    PYTHON_CMD=python3.12
fi

echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"
echo

# Create venv
echo "Creating virtual environment..."
$PYTHON_CMD -m venv .venv

# Activate venv
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

# Install package with GUI
echo "Installing antidetect-playwright with GUI dependencies..."
pip install -e ".[gui]"

# Install Camoufox (not Playwright)
echo "Camoufox will be installed automatically on first launch."

# Create data directories
echo "Creating data directories..."
mkdir -p data/browser_data

echo
echo "=== Setup complete! ==="
echo
echo "To start the GUI:"
echo "  source .venv/bin/activate"
echo "  antidetect-browser"
echo
echo "On first launch, Camoufox browser will be downloaded automatically."
echo
