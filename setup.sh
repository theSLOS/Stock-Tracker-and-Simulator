#!/bin/bash
set -e

echo "============================================"
echo " Stock App - macOS / Linux Setup"
echo "============================================"
echo

# Prefer python3; fall back to python
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [ -z "$PYTHON" ]; then
    echo "ERROR: Python not found."
    echo "Please install Python 3.10-3.12 from https://python.org"
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PY_VERSION at $PYTHON"

echo
echo "Creating virtual environment..."
"$PYTHON" -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo
echo "Installing dependencies (this may take 2-3 minutes for Prophet)..."
pip install -r requirements.txt

echo
echo "============================================"
echo " Setup complete!"
echo "============================================"
echo
echo "To run the app:"
echo "  1. Activate the venv: source venv/bin/activate"
echo "  2. Run: python main.py"
echo
