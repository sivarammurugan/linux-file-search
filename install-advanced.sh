#!/bin/bash
#
# Advanced Installation Script for Linux File Search App
# Supports multiple installation methods including standalone executables
#

set -e

APP_NAME="filesearch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/usr/local/bin"
DESKTOP_DIR="/usr/share/applications"
LOCAL_DESKTOP_DIR="$HOME/.local/share/applications"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=================================================${NC}"
    echo -e "${BLUE}    Linux File Search App - Installation${NC}"
    echo -e "${BLUE}=================================================${NC}"
    echo ""
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check for Python 3
    if ! command -v python3 >/dev/null 2>&1; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Found Python $PYTHON_VERSION"
    
    # Check for tkinter (GUI dependency)
    if ! python3 -c "import tkinter" >/dev/null 2>&1; then
        print_warning "tkinter not available - GUI version may not work"
        print_warning "Install with: sudo apt-get install python3-tk (Ubuntu/Debian)"
    fi
}

install_method_menu() {
    echo "Choose installation method:"
    echo "1) Standalone executables (recommended - no dependencies)"
    echo "2) Python scripts with dependencies"
    echo "3) System-wide installation (requires sudo)"
    echo "4) User-only installation"
    echo "5) Build new standalone executables"
    echo ""
    read -p "Enter choice [1-5]: " choice
    echo ""
    
    case $choice in
        1) install_standalone_executables ;;
        2) install_python_scripts ;;
        3) install_system_wide ;;
        4) install_user_only ;;
        5) build_and_install_executables ;;
        *) 
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

install_standalone_executables() {
    print_status "Installing standalone executables..."
    
    # Check if executables exist
    if [[ ! -f "$SCRIPT_DIR/dist/filesearch-gui" ]] || [[ ! -f "$SCRIPT_DIR/dist/filesearch-cli" ]]; then
        print_warning "Standalone executables not found. Building them..."
        build_executables
    fi
    
    # Determine installation directory
    if [[ $EUID -eq 0 ]]; then
        BIN_DIR="$INSTALL_DIR"
        DESKTOP_INSTALL_DIR="$DESKTOP_DIR"
        print_status "Installing system-wide to $BIN_DIR"
    else
        BIN_DIR="$HOME/.local/bin"
        DESKTOP_INSTALL_DIR="$LOCAL_DESKTOP_DIR"
        mkdir -p "$BIN_DIR"
        mkdir -p "$DESKTOP_INSTALL_DIR"
        print_status "Installing for current user to $BIN_DIR"
    fi
    
    # Copy executables
    cp "$SCRIPT_DIR/dist/filesearch-gui" "$BIN_DIR/filesearch-gui"
    cp "$SCRIPT_DIR/dist/filesearch-cli" "$BIN_DIR/filesearch-cli"
    
    # Make them executable
    chmod +x "$BIN_DIR/filesearch-gui"
    chmod +x "$BIN_DIR/filesearch-cli"
    
    # Create main launcher that chooses between GUI and CLI
    cat > "$BIN_DIR/$APP_NAME" << 'EOF'
#!/bin/bash
# Main launcher for Linux File Search App

if [[ "$1" == "--cli" ]] || [[ "$1" == "-c" ]]; then
    shift
    exec filesearch-cli "$@"
elif [[ "$1" == "--gui" ]] || [[ "$1" == "-g" ]] || [[ $# -eq 0 ]]; then
    shift
    exec filesearch-gui "$@"
else
    # Default: if arguments provided, use CLI, otherwise GUI
    if [[ $# -gt 0 ]]; then
        exec filesearch-cli "$@"
    else
        exec filesearch-gui "$@"
    fi
fi
EOF
    
    chmod +x "$BIN_DIR/$APP_NAME"
    
    # Install desktop entry
    install_desktop_entry "$BIN_DIR" "$DESKTOP_INSTALL_DIR"
    
    print_status "Standalone executables installed successfully!"
    print_final_instructions "$BIN_DIR"
}

install_python_scripts() {
    print_status "Installing Python scripts with dependencies..."
    
    # Install Python dependencies
    if command -v pip3 >/dev/null 2>&1; then
        print_status "Installing Python dependencies..."
        pip3 install --user -r "$SCRIPT_DIR/requirements.txt" || true
    else
        print_warning "pip3 not found - dependencies may need to be installed manually"
    fi
    
    # Use the existing filesearch launcher
    if [[ $EUID -eq 0 ]]; then
        BIN_DIR="$INSTALL_DIR"
        DESKTOP_INSTALL_DIR="$DESKTOP_DIR"
        print_status "Installing system-wide to $BIN_DIR"
    else
        BIN_DIR="$HOME/.local/bin"
        DESKTOP_INSTALL_DIR="$LOCAL_DESKTOP_DIR"
        mkdir -p "$BIN_DIR"
        mkdir -p "$DESKTOP_INSTALL_DIR"
        print_status "Installing for current user to $BIN_DIR"
    fi
    
    # Create wrapper script
    cat > "$BIN_DIR/$APP_NAME" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
python3 "$SCRIPT_DIR/filesearch" "\$@"
EOF
    
    chmod +x "$BIN_DIR/$APP_NAME"
    
    # Install desktop entry
    install_desktop_entry "$BIN_DIR" "$DESKTOP_INSTALL_DIR"
    
    print_status "Python scripts installed successfully!"
    print_final_instructions "$BIN_DIR"
}

install_system_wide() {
    if [[ $EUID -ne 0 ]]; then
        print_error "System-wide installation requires sudo privileges"
        exit 1
    fi
    
    install_standalone_executables
}

install_user_only() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "Running as root - consider system-wide installation instead"
    fi
    
    install_standalone_executables
}

build_and_install_executables() {
    print_status "Building new standalone executables..."
    build_executables
    install_standalone_executables
}

build_executables() {
    print_status "Building standalone executables with PyInstaller..."
    
    # Check if build script exists
    if [[ ! -f "$SCRIPT_DIR/build_executable.sh" ]]; then
        print_error "Build script not found at $SCRIPT_DIR/build_executable.sh"
        exit 1
    fi
    
    # Run build script
    cd "$SCRIPT_DIR"
    chmod +x build_executable.sh
    ./build_executable.sh
    
    if [[ $? -ne 0 ]]; then
        print_error "Build failed!"
        exit 1
    fi
    
    print_status "Build completed successfully!"
}

install_desktop_entry() {
    local bin_dir="$1"
    local desktop_dir="$2"
    
    print_status "Installing desktop entry..."
    
    # Create desktop entry
    cat > "$desktop_dir/filesearch.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=File Search
Comment=Fast file search application for Linux
Exec=$bin_dir/filesearch --gui
Icon=system-search
Terminal=false
Categories=Utility;System;FileTools;
Keywords=search;file;find;index;
StartupNotify=true
MimeType=inode/directory;
EOF
    
    chmod +x "$desktop_dir/filesearch.desktop"
    
    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        if [[ "$desktop_dir" == "$DESKTOP_DIR" ]]; then
            update-desktop-database "$desktop_dir" 2>/dev/null || true
        else
            update-desktop-database "$desktop_dir" 2>/dev/null || true
        fi
    fi
    
    print_status "Desktop entry installed"
}

print_final_instructions() {
    local bin_dir="$1"
    
    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    echo "You can now:"
    echo "• Run 'filesearch' to launch the GUI version"
    echo "• Run 'filesearch --cli' to launch the CLI version"
    echo "• Run 'filesearch --help' for more options"
    echo "• Find 'File Search' in your application menu"
    echo ""
    
    if [[ "$bin_dir" == "$HOME/.local/bin" ]]; then
        if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
            print_warning "Note: $bin_dir is not in your PATH"
            echo "Add this to your ~/.bashrc or ~/.profile:"
            echo "export PATH=\"\$PATH:$bin_dir\""
            echo ""
            echo "Or run commands with full path:"
            echo "$bin_dir/filesearch"
        fi
    fi
    
    # Show usage examples
    echo "Usage examples:"
    echo "  filesearch                    # Launch GUI"
    echo "  filesearch --cli search *.py  # Search for Python files"
    echo "  filesearch --cli --build      # Build index"
    echo "  filesearch --cli --update     # Update index"
    echo ""
}

uninstall() {
    print_status "Uninstalling Linux File Search App..."
    
    # Remove from system directories
    if [[ $EUID -eq 0 ]]; then
        rm -f "$INSTALL_DIR/filesearch"
        rm -f "$INSTALL_DIR/filesearch-gui"
        rm -f "$INSTALL_DIR/filesearch-cli"
        rm -f "$DESKTOP_DIR/filesearch.desktop"
        print_status "Removed system-wide installation"
    fi
    
    # Remove from user directories
    rm -f "$HOME/.local/bin/filesearch"
    rm -f "$HOME/.local/bin/filesearch-gui"
    rm -f "$HOME/.local/bin/filesearch-cli"
    rm -f "$LOCAL_DESKTOP_DIR/filesearch.desktop"
    
    # Ask about database
    read -p "Remove search database (~/.filesearch.db)? [y/N]: " remove_db
    if [[ "$remove_db" =~ ^[Yy]$ ]]; then
        rm -f "$HOME/.filesearch.db"
        print_status "Removed search database"
    fi
    
    print_status "Uninstallation complete"
}

# Main script
print_header

case "${1:-}" in
    --uninstall)
        uninstall
        ;;
    --help|-h)
        echo "Linux File Search App Installation Script"
        echo ""
        echo "Usage:"
        echo "  $0                 Interactive installation"
        echo "  $0 --uninstall     Remove installation"
        echo "  $0 --help          Show this help"
        echo ""
        ;;
    *)
        check_dependencies
        install_method_menu
        ;;
esac
