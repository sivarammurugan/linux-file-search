#!/bin/bash
"""
Simple wrapper script for Linux File Search App
"""

APP_DIR="$(dirname "$(readlink -f "$0")")"
cd "$APP_DIR"

# Check if Python dependencies are installed
if ! python3 -c "import tkinter, sqlite3" >/dev/null 2>&1; then
    echo "Installing dependencies..."
    pip3 install --user -r requirements.txt
fi

# Launch the application
if [ "$1" = "--cli" ] || [ "$1" = "-c" ]; then
    python3 main.py "${@:2}"
else
    python3 gui.py "$@"
fi
