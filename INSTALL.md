# Linux File Search App - Installation Guide

## Quick Start

1. **Download and Extract**
   ```bash
   tar -xzf linux-file-search-app.tar.gz
   cd search/
   ```

2. **Install (Recommended)**
   ```bash
   chmod +x install-advanced.sh
   ./install-advanced.sh
   ```
   Choose option 1 for standalone executables (no dependencies required).

3. **Use**
   ```bash
   filesearch                    # Launch GUI
   filesearch --cli --build      # Build index
   filesearch --cli search "*.py" # Search files
   ```

## What's Included

- **Standalone Executables**: `dist/filesearch-gui` (27MB), `dist/filesearch-cli` (23MB)
- **Source Code**: `main.py`, `gui.py`, `file_monitor.py`
- **Installation Scripts**: `install-advanced.sh`, `install.sh`
- **Build Tools**: `build_executable.sh`
- **Desktop Integration**: `filesearch.desktop`

## Installation Options

### Option 1: Standalone Executables (Recommended)
- No Python dependencies required
- Works on any Linux x86_64 system
- Includes desktop integration

### Option 2: Python Scripts
- Requires Python 3.6+
- Install with: `pip install -r requirements.txt`
- Smaller footprint, full source access

### Option 3: System-wide Installation
- Install for all users (requires sudo)
- Automatic desktop integration

## Features

- **🔍 Instant Search**: Sub-millisecond search results
- **🖼️ Dual Interface**: Both CLI and GUI modes
- **🔄 Real-time Monitoring**: Automatic file system updates
- **📊 Incremental Indexing**: Smart updates without full rebuilds
- **🎯 Wildcard Support**: Use `*` and `?` in search patterns
- **📁 File Operations**: Open files and folders directly

## Requirements

- Linux x86_64 (for standalone executables)
- Python 3.6+ (for source installation)
- ~50MB disk space for full installation

## Support

For issues, troubleshooting, or feature requests, see the full README.md file.

## Uninstall

```bash
./install-advanced.sh --uninstall
```

---

Happy searching! 🔍
