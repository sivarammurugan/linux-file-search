#!/bin/bash
"""
Installation script for Linux File Search App
"""

set -e

APP_NAME="filesearch"
APP_DIR="/home/siva/projects/search"
INSTALL_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
LOCAL_DESKTOP_DIR="$HOME/.local/share/applications"

echo "Installing Linux File Search App..."

# Check if running as root for system-wide installation
if [[ $EUID -eq 0 ]]; then
    echo "Installing system-wide..."
    INSTALL_TO_SYSTEM=true
    BIN_DIR="$INSTALL_DIR"
    DESKTOP_INSTALL_DIR="$DESKTOP_DIR"
else
    echo "Installing for current user..."
    INSTALL_TO_SYSTEM=false
    BIN_DIR="$HOME/.local/bin"
    DESKTOP_INSTALL_DIR="$LOCAL_DESKTOP_DIR"
    
    # Create directories if they don't exist
    mkdir -p "$BIN_DIR"
    mkdir -p "$DESKTOP_INSTALL_DIR"
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install --user -r "$APP_DIR/requirements.txt"

# Create wrapper script
cat > "$BIN_DIR/$APP_NAME" << EOF
#!/bin/bash
cd "$APP_DIR"
python3 "$APP_DIR/filesearch" "\$@"
EOF

chmod +x "$BIN_DIR/$APP_NAME"

# Install desktop entry
if [ "$INSTALL_TO_SYSTEM" = true ]; then
    cp "$APP_DIR/filesearch.desktop" "$DESKTOP_INSTALL_DIR/"
else
    # Update desktop file with correct paths for user installation
    sed "s|Exec=.*|Exec=$BIN_DIR/$APP_NAME --gui|g" "$APP_DIR/filesearch.desktop" > "$DESKTOP_INSTALL_DIR/filesearch.desktop"
fi

chmod +x "$DESKTOP_INSTALL_DIR/filesearch.desktop"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    if [ "$INSTALL_TO_SYSTEM" = true ]; then
        update-desktop-database "$DESKTOP_DIR"
    else
        update-desktop-database "$DESKTOP_INSTALL_DIR"
    fi
fi

echo ""
echo "Installation complete!"
echo ""
echo "You can now:"
echo "1. Run 'filesearch --gui' to launch the GUI version"
echo "2. Run 'filesearch --cli' to launch the CLI version"
echo "3. Find 'File Search' in your application menu"
echo ""

if [ "$INSTALL_TO_SYSTEM" = false ]; then
    echo "Note: Make sure $BIN_DIR is in your PATH"
    echo "Add this to your ~/.bashrc or ~/.profile:"
    echo "export PATH=\"\$PATH:$BIN_DIR\""
fi
