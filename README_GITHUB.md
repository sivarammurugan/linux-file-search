# 🔍 Linux File Search App

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Linux](https://img.shields.io/badge/platform-Linux-green.svg)](https://www.linux.org/)

A comprehensive, fast file search application for Linux with both CLI and GUI interfaces, similar to "Everything" for Windows. Features instant search, real-time file monitoring, incremental indexing, and desktop integration.

## ✨ Features

- **⚡ Instant Search**: Sub-millisecond search results using SQLite indexing
- **🖼️ Dual Interface**: Both modern GUI and powerful CLI
- **🔄 Real-time Monitoring**: Automatic file system updates using polling
- **📊 Incremental Indexing**: Smart updates without full rebuilds
- **🎯 Wildcard Support**: Use `*` and `?` in search patterns
- **📁 File Operations**: Open files and folders directly from results
- **🎨 Desktop Integration**: Application menu and taskbar support
- **📦 Multiple Deployments**: Standalone executables or Python scripts

## 🚀 Quick Start

### Installation
```bash
git clone https://github.com/yourusername/linux-file-search-app.git
cd linux-file-search-app
chmod +x install-advanced.sh && ./install-advanced.sh
```

### Usage
```bash
# Launch GUI
filesearch

# CLI search
filesearch --cli --search "*.py"
```

## 📋 Requirements

- Python 3.6+
- Linux (tested on Ubuntu, Debian, CentOS)
- Tkinter (usually pre-installed)

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Pull requests are welcome! Please read our contributing guidelines first.