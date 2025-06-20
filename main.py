#!/usr/bin/env python3
"""
Minimal File Search App for Linux
A basic implementation of fast file searching similar to "Everything"
"""

import os
import sys
import time
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Optional
import fnmatch
import threading
from concurrent.futures import ThreadPoolExecutor

# Try to import file monitoring
try:
    from file_monitor import FileSystemMonitor, check_inotify_support
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class FileIndexer:
    """Handles file indexing and database operations"""
    
    def __init__(self, db_path: str = "~/.filesearch.db"):
        self.db_path = os.path.expanduser(db_path)
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for file storage"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                size INTEGER,
                modified INTEGER,
                indexed_at INTEGER
            )
        ''')
        # Add index_paths table to track indexed directories
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS index_paths (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                last_indexed INTEGER,
                file_count INTEGER
            )
        ''')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON files(name)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_path ON files(path)')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_indexed_paths ON index_paths(path)')
        self.conn.commit()
    
    def _safe_encode_string(self, s: str) -> str:
        """Safely encode string to handle Unicode issues"""
        try:
            # Try to encode and decode to catch surrogate issues
            s.encode('utf-8')
            return s
        except UnicodeEncodeError:
            # Replace problematic characters with replacement character
            return s.encode('utf-8', errors='replace').decode('utf-8')
        except UnicodeDecodeError:
            # Handle decode errors
            return repr(s)[1:-1]  # Remove quotes from repr
    
    def index_directory(self, root_path: str, progress_callback=None):
        """Index all files in a directory tree"""
        print(f"Indexing files in {root_path}...")
        
        # Clear existing entries for this path
        self.conn.execute('DELETE FROM files WHERE path LIKE ?', (f"{root_path}%",))
        
        files_indexed = 0
        batch_size = 1000
        batch = []
        
        for root, dirs, files in os.walk(root_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                try:
                    stat = os.stat(file_path)
                    
                    # Handle Unicode encoding issues with filenames
                    safe_filename = self._safe_encode_string(file)
                    safe_filepath = self._safe_encode_string(file_path)
                    
                    batch.append((
                        safe_filename,
                        safe_filepath,
                        stat.st_size,
                        int(stat.st_mtime),
                        int(time.time())
                    ))
                    
                    if len(batch) >= batch_size:
                        self._insert_batch(batch)
                        batch = []
                        files_indexed += batch_size
                        
                        if progress_callback:
                            progress_callback(files_indexed)
                            
                except (OSError, PermissionError, UnicodeDecodeError, UnicodeEncodeError):
                    continue
        
        # Insert remaining files
        if batch:
            self._insert_batch(batch)
            files_indexed += len(batch)
        
        print(f"Indexed {files_indexed} files")
        return files_indexed
    
    def _insert_batch(self, batch):
        """Insert a batch of files into database"""
        try:
            self.conn.executemany(
                'INSERT OR REPLACE INTO files (name, path, size, modified, indexed_at) VALUES (?, ?, ?, ?, ?)',
                batch
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            # Try to commit what we can
            self.conn.rollback()
    
    def incremental_index_directory(self, root_path: str, progress_callback=None):
        """Incrementally index a directory - only update changed files"""
        root_path = os.path.abspath(root_path)
        current_time = int(time.time())
        
        # Get last indexed time for this path
        cursor = self.conn.execute(
            "SELECT last_indexed FROM index_paths WHERE path = ?", (root_path,)
        )
        result = cursor.fetchone()
        last_indexed = result[0] if result else 0
        
        print(f"Incremental indexing {root_path}...")
        if last_indexed > 0:
            print(f"Last indexed: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_indexed))}")
        else:
            print("First time indexing this directory")
            
        # Track current files for deletion detection
        current_files = set()
        new_files = 0
        updated_files = 0
        skipped_files = 0
        
        # Walk through directory
        for root, dirs, files in os.walk(root_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                try:
                    file_path = os.path.join(root, file)
                    current_files.add(file_path)
                    
                    stat_info = os.stat(file_path)
                    modified_time = int(stat_info.st_mtime)
                    
                    # Check if file needs to be indexed/updated
                    cursor = self.conn.execute(
                        "SELECT modified FROM files WHERE path = ?", (file_path,)
                    )
                    existing = cursor.fetchone()
                    
                    if not existing:
                        # New file
                        self._add_file_to_index(file_path, stat_info)
                        new_files += 1
                    elif existing[0] != modified_time:
                        # File was modified
                        self._update_file_in_index(file_path, stat_info)
                        updated_files += 1
                    else:
                        # File unchanged
                        skipped_files += 1
                        
                    # Report progress
                    if progress_callback and (new_files + updated_files + skipped_files) % 1000 == 0:
                        progress_callback(new_files + updated_files + skipped_files)
                        
                except (OSError, PermissionError, UnicodeDecodeError, UnicodeEncodeError):
                    continue
        
        # Remove files that no longer exist
        cursor = self.conn.execute(
            "SELECT path FROM files WHERE path LIKE ?", (root_path + "%",)
        )
        indexed_files = {row[0] for row in cursor.fetchall()}
        deleted_files = indexed_files - current_files
        
        if deleted_files:
            # Batch delete operations to avoid "too many SQL variables" error
            batch_size = 500  # SQLite limit is usually 999, use 500 to be safe
            deleted_files_list = list(deleted_files)
            
            for i in range(0, len(deleted_files_list), batch_size):
                batch = deleted_files_list[i:i + batch_size]
                placeholders = ",".join("?" * len(batch))
                self.conn.execute(
                    f"DELETE FROM files WHERE path IN ({placeholders})",
                    batch
                )
            print(f"Removed {len(deleted_files)} deleted files from index")
            
        # Update index_paths table
        total_files = len(current_files)
        self.conn.execute('''
            INSERT OR REPLACE INTO index_paths (path, last_indexed, file_count)
            VALUES (?, ?, ?)
        ''', (root_path, current_time, total_files))
        
        self.conn.commit()
        
        print(f"Incremental index complete:")
        print(f"  New files: {new_files}")
        print(f"  Updated files: {updated_files}")
        print(f"  Unchanged files: {skipped_files}")
        print(f"  Deleted files: {len(deleted_files)}")
        print(f"  Total files: {total_files}")
        
        return new_files + updated_files + len(deleted_files)  # Return number of changes
        
    def _add_file_to_index(self, file_path: str, stat_info):
        """Add a single file to the index"""
        filename = os.path.basename(file_path)
        safe_name = self._safe_encode_string(filename)
        safe_path = self._safe_encode_string(file_path)
        
        self.conn.execute('''
            INSERT INTO files (name, path, size, modified, indexed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (safe_name, safe_path, stat_info.st_size, int(stat_info.st_mtime), int(time.time())))
        
    def _update_file_in_index(self, file_path: str, stat_info):
        """Update an existing file in the index"""
        filename = os.path.basename(file_path)
        safe_name = self._safe_encode_string(filename)
        safe_path = self._safe_encode_string(file_path)
        
        self.conn.execute('''
            UPDATE files SET name = ?, size = ?, modified = ?, indexed_at = ?
            WHERE path = ?
        ''', (safe_name, stat_info.st_size, int(stat_info.st_mtime), int(time.time()), safe_path))
        
    def get_indexed_paths(self):
        """Get list of previously indexed paths"""
        cursor = self.conn.execute('''
            SELECT path, last_indexed, file_count 
            FROM index_paths 
            ORDER BY last_indexed DESC
        ''')
        return cursor.fetchall()
        
    def is_path_indexed(self, path: str):
        """Check if a path has been indexed before"""
        cursor = self.conn.execute(
            "SELECT COUNT(*) FROM index_paths WHERE path = ?", (os.path.abspath(path),)
        )
        return cursor.fetchone()[0] > 0
    
    def search(self, query: str, limit: int = 100, case_sensitive: bool = False) -> List[Dict]:
        """Search for files matching the query"""
        if not query:
            return []
        
        # Convert wildcards to SQL LIKE pattern
        if '*' in query or '?' in query:
            sql_pattern = query.replace('*', '%').replace('?', '_')
            sql_query = '''
                SELECT name, path, size, modified 
                FROM files 
                WHERE name LIKE ? 
                ORDER BY name 
                LIMIT ?
            '''
            params = (sql_pattern if case_sensitive else sql_pattern.lower(), limit)
        else:
            # Simple substring search
            if case_sensitive:
                sql_query = '''
                    SELECT name, path, size, modified 
                    FROM files 
                    WHERE name LIKE ? 
                    ORDER BY name 
                    LIMIT ?
                '''
                params = (f'%{query}%', limit)
            else:
                sql_query = '''
                    SELECT name, path, size, modified 
                    FROM files 
                    WHERE LOWER(name) LIKE LOWER(?) 
                    ORDER BY name 
                    LIMIT ?
                '''
                params = (f'%{query}%', limit)
        
        cursor = self.conn.execute(sql_query, params)
        results = []
        
        for row in cursor.fetchall():
            results.append({
                'name': row[0],
                'path': row[1],
                'size': row[2],
                'modified': row[3]
            })
        
        return results
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class FileSearchApp:
    """Main application class"""
    
    def __init__(self, enable_monitoring: bool = False):
        self.indexer = FileIndexer()
        self.monitor = None
        self.monitoring_enabled = False
        
        if enable_monitoring and MONITORING_AVAILABLE:
            try:
                self.monitor = FileSystemMonitor(
                    self.indexer, 
                    update_callback=self._on_file_changes
                )
                self.monitoring_enabled = True
                print("Real-time file monitoring enabled")
            except Exception as e:
                print(f"Failed to enable monitoring: {e}")
                self.monitoring_enabled = False
        elif enable_monitoring:
            print("File monitoring not available. Install with: pip install inotify")
    
    def _on_file_changes(self, changes: Dict[str, int]):
        """Callback for file change notifications"""
        total_changes = sum(changes.values())
        if total_changes > 0:
            print(f"Index updated: {changes['created']} created, "
                  f"{changes['modified']} modified, {changes['deleted']} deleted")
    
    def enable_monitoring_for_path(self, path: str):
        """Enable real-time monitoring for a specific path"""
        if not self.monitoring_enabled:
            print("Monitoring not available")
            return False
            
        try:
            self.monitor.add_watch_path(path)
            if not self.monitor.running:
                self.monitor.start_monitoring()
            return True
        except Exception as e:
            print(f"Failed to enable monitoring for {path}: {e}")
            return False
    
    def disable_monitoring_for_path(self, path: str):
        """Disable monitoring for a specific path"""
        if self.monitor:
            self.monitor.remove_watch_path(path)
    
    def start_monitoring(self):
        """Start file system monitoring for all indexed paths"""
        if not self.monitoring_enabled:
            return False
            
        # Add monitoring for all indexed paths
        indexed_paths = self.indexer.get_indexed_paths()
        for path, _, _ in indexed_paths:
            self.enable_monitoring_for_path(path)
        
        return True
    
    def stop_monitoring(self):
        """Stop file system monitoring"""
        if self.monitor:
            self.monitor.stop_monitoring()
    
    def get_monitoring_status(self):
        """Get current monitoring status"""
        if not self.monitoring_enabled:
            return {"enabled": False, "monitored_paths": []}
        
        return {
            "enabled": True,
            "running": self.monitor.running if self.monitor else False,
            "monitored_paths": list(self.monitor.get_monitored_paths()) if self.monitor else []
        }
    
    def build_index(self, paths: List[str], enable_monitoring: bool = True):
        """Build file index for given paths"""
        for path in paths:
            if os.path.exists(path):
                self.indexer.index_directory(path)
                
                # Enable monitoring for this path if requested
                if enable_monitoring and self.monitoring_enabled:
                    self.enable_monitoring_for_path(path)
            else:
                print(f"Warning: Path does not exist: {path}")
    
    def incremental_build_index(self, paths: List[str], enable_monitoring: bool = True):
        """Incrementally build file index for given paths"""
        for path in paths:
            if os.path.exists(path):
                self.indexer.incremental_index_directory(path)
                
                # Enable monitoring for this path if requested
                if enable_monitoring and self.monitoring_enabled:
                    self.enable_monitoring_for_path(path)
            else:
                print(f"Warning: Path does not exist: {path}")
    
    def get_indexed_paths_info(self):
        """Get information about previously indexed paths"""
        paths = self.indexer.get_indexed_paths()
        if not paths:
            print("No paths have been indexed yet.")
            return
            
        print("\nIndexed Paths:")
        print("-" * 80)
        for path, last_indexed, file_count in paths:
            indexed_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_indexed))
            print(f"{path:<50} {file_count:>8} files  {indexed_time}")
    
    def suggest_incremental_update(self, path: str) -> bool:
        """Check if incremental update is recommended for a path"""
        return self.indexer.is_path_indexed(path)
    
    def search_files(self, query: str, limit: int = 100, case_sensitive: bool = False):
        """Search for files and display results"""
        start_time = time.time()
        results = self.indexer.search(query, limit, case_sensitive)
        search_time = (time.time() - start_time) * 1000
        
        print(f"\nFound {len(results)} files (search took {search_time:.1f}ms)")
        print("-" * 80)
        
        for result in results:
            size_str = self._format_size(result['size'])
            mod_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(result['modified']))
            print(f"{result['name']:<40} {size_str:>10} {mod_time} {result['path']}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f}MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.1f}GB"
    
    def interactive_mode(self):
        """Run in interactive search mode"""
        print("File Search App - Interactive Mode")
        print("Commands:")
        print("  'exit' - quit application")
        print("  'rebuild' - rebuild full index")
        print("  'update' - incremental update of existing indexes")
        print("  'paths' - show indexed paths")
        print("  'monitor' - show monitoring status")
        print("  'start-monitor' - start real-time monitoring")
        print("  'stop-monitor' - stop real-time monitoring")
        print("  'help' - show this help")
        print("-" * 50)
        
        while True:
            try:
                query = input("Search> ").strip()
                
                if query.lower() == 'exit':
                    break
                elif query.lower() == 'rebuild':
                    self.build_index([os.path.expanduser("~")])
                elif query.lower() == 'update':
                    self._interactive_incremental_update()
                elif query.lower() == 'paths':
                    self.get_indexed_paths_info()
                elif query.lower() == 'monitor':
                    self._show_monitoring_status()
                elif query.lower() == 'start-monitor':
                    self.start_monitoring()
                elif query.lower() == 'stop-monitor':
                    self.stop_monitoring()
                elif query.lower() == 'help':
                    print("\nCommands:")
                    print("  'exit' - quit application")
                    print("  'rebuild' - rebuild full index")
                    print("  'update' - incremental update of existing indexes")
                    print("  'paths' - show indexed paths")
                    print("  'monitor' - show monitoring status")
                    print("  'start-monitor' - start real-time monitoring")
                    print("  'stop-monitor' - stop real-time monitoring")
                    print("  'help' - show this help")
                    print("  Or type any search query to find files")
                elif query:
                    self.search_files(query)
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
        
        print("\nGoodbye!")
    
    def _show_monitoring_status(self):
        """Show current monitoring status"""
        status = self.get_monitoring_status()
        print(f"\nMonitoring Status:")
        print(f"  Enabled: {status['enabled']}")
        
        if status['enabled']:
            print(f"  Running: {status['running']}")
            if status['monitored_paths']:
                print(f"  Monitored Paths:")
                for path in status['monitored_paths']:
                    print(f"    - {path}")
            else:
                print(f"  No paths currently monitored")
        else:
            print("  Install 'inotify' package to enable monitoring")
    
    def _interactive_incremental_update(self):
        """Handle incremental update in interactive mode"""
        paths = self.indexer.get_indexed_paths()
        if not paths:
            print("No paths have been indexed yet. Use 'rebuild' to create an initial index.")
            return
            
        print("\nAvailable paths for incremental update:")
        for i, (path, last_indexed, file_count) in enumerate(paths):
            indexed_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_indexed))
            print(f"{i+1}. {path} ({file_count} files, last indexed: {indexed_time})")
            
        try:
            choice = input("\nEnter path number to update (or 'all' for all paths): ").strip()
            if choice.lower() == 'all':
                for path, _, _ in paths:
                    self.incremental_build_index([path])
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(paths):
                    self.incremental_build_index([paths[idx][0]])
                else:
                    print("Invalid path number")
            else:
                print("Invalid choice")
        except (ValueError, KeyboardInterrupt):
            print("Update cancelled")
    
    def cleanup(self):
        """Cleanup resources"""
        self.indexer.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Fast File Search App for Linux')
    parser.add_argument('query', nargs='?', help='Search query')
    parser.add_argument('-i', '--interactive', action='store_true', 
                       help='Run in interactive mode')
    parser.add_argument('-b', '--build', action='store_true',
                       help='Build/rebuild file index')
    parser.add_argument('-u', '--update', action='store_true',
                       help='Incrementally update existing file index')
    parser.add_argument('--show-paths', action='store_true',
                       help='Show indexed paths and their information')
    parser.add_argument('-p', '--path', default=os.path.expanduser("~"),
                       help='Path to index (default: home directory)')
    parser.add_argument('-l', '--limit', type=int, default=100,
                       help='Maximum number of results (default: 100)')
    parser.add_argument('-c', '--case-sensitive', action='store_true',
                       help='Case sensitive search')
    
    args = parser.parse_args()
    
    app = FileSearchApp()
    
    try:
        if args.show_paths:
            app.get_indexed_paths_info()
            return
            
        if args.build:
            app.build_index([args.path])
            
        if args.update:
            if app.suggest_incremental_update(args.path):
                app.incremental_build_index([args.path])
            else:
                print(f"Path {args.path} has not been indexed before. Use --build to create initial index.")
                return
            
        if args.interactive:
            app.interactive_mode()
        elif args.query:
            app.search_files(args.query, args.limit, args.case_sensitive)
        else:
            # Check if index exists, if not, build it
            if not os.path.exists(os.path.expanduser("~/.filesearch.db")):
                print("No index found. Building index for home directory...")
                app.build_index([args.path])
            
            # Start interactive mode
            app.interactive_mode()
            
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
