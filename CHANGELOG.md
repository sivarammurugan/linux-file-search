# Changelog

All notable changes to the Linux File Search App project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-20

### Added
- Initial release of Linux File Search App
- CLI interface with interactive mode
- Modern GUI interface using tkinter
- SQLite-based file indexing system
- Real-time file monitoring using polling
- Incremental indexing capabilities
- Standalone executable generation with PyInstaller
- Advanced installation script with multiple options
- Desktop integration with custom icon
- Taskbar/panel pinning support
- Wildcard search support (`*` and `?`)
- Case-sensitive search option
- File operations (open file, open folder, copy path)
- Multiple deployment methods
- Comprehensive documentation

### Technical Features
- Sub-millisecond search performance
- Automatic file change detection
- Batch processing for efficiency
- SQLite threading safety improvements
- Memory-efficient file caching
- Cross-platform Python compatibility

### Performance
- Indexing speed: ~1000 files/second
- Search speed: Sub-millisecond after indexing
- Memory usage: ~1MB per 10,000 indexed files
- Executable sizes: 27.7MB (GUI), 23.3MB (CLI)

### Documentation
- Complete README with installation instructions
- Advanced installation guide
- Taskbar integration instructions
- Project summary and final status
- MIT License for open source distribution

## [0.9.0] - 2025-06-10

### Added
- Basic file search functionality
- Initial CLI implementation
- SQLite database integration
- Simple file indexing

### Fixed
- SQLite "too many variables" error
- Threading issues with database connections
- File monitoring reliability improvements

## [0.5.0] - 2025-06-06

### Added
- Project initialization
- Core search algorithm
- Basic GUI framework
- File system walking capabilities

---

## Legend
- **Added**: New features
- **Changed**: Changes in existing functionality  
- **Deprecated**: Soon-to-be removed features
- **Removed**: Features removed in this version
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes
