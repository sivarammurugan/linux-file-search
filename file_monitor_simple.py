#!/usr/bin/env python3
"""
Simple File Monitor for Linux File Search App
Uses polling method to detect file changes
"""

import os
import threading
import time
from pathlib import Path


class FileMonitor:
    """Simple file system monitor using polling"""
    
    def __init__(self, paths, callback):
        """
        Initialize file monitor
        
        Args:
            paths: List of paths to monitor
            callback: Function to call when files change (event_type, file_path)
        """
        self.paths = [str(Path(p).resolve()) for p in paths]
        self.callback = callback
        self.running = False
        self.thread = None
        self.file_cache = {}
        self.batch_timer = None
        self.pending_changes = set()
        
        print(f"FileMonitor initialized for paths: {self.paths}")
    
    def start(self):
        """Start monitoring"""
        if self.running:
            print("FileMonitor already running")
            return True
            
        try:
            # Initialize file cache
            self._build_file_cache()
            
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print(f"FileMonitor started successfully for {len(self.paths)} paths")
            return True
                
        except Exception as e:
            print(f"Failed to start file monitoring: {e}")
            return False
    
    def stop(self):
        """Stop monitoring"""
        print("Stopping FileMonitor...")
        self.running = False
        
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        
        print("FileMonitor stopped")
    
    def _build_file_cache(self):
        """Build initial cache of file modification times"""
        print("Building initial file cache...")
        self.file_cache.clear()
        
        for path in self.paths:
            if not os.path.exists(path):
                print(f"Warning: Path does not exist: {path}")
                continue
                
            try:
                for root, dirs, files in os.walk(path):
                    # Skip hidden directories
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        if file.startswith('.'):
                            continue
                            
                        file_path = os.path.join(root, file)
                        try:
                            stat_info = os.stat(file_path)
                            self.file_cache[file_path] = {
                                'mtime': stat_info.st_mtime,
                                'size': stat_info.st_size
                            }
                        except (OSError, PermissionError):
                            continue
            except Exception as e:
                print(f"Error building cache for {path}: {e}")
        
        print(f"File cache built with {len(self.file_cache)} files")
    
    def _monitor_loop(self):
        """Main monitoring loop using polling"""
        print("FileMonitor loop started")
        poll_interval = 10  # Check every 10 seconds
        
        while self.running:
            try:
                changes_detected = False
                current_files = {}
                
                # Scan all monitored paths
                for path in self.paths:
                    if not os.path.exists(path):
                        continue
                        
                    try:
                        for root, dirs, files in os.walk(path):
                            # Skip hidden directories
                            dirs[:] = [d for d in dirs if not d.startswith('.')]
                            
                            for file in files:
                                if file.startswith('.'):
                                    continue
                                    
                                file_path = os.path.join(root, file)
                                try:
                                    stat_info = os.stat(file_path)
                                    current_files[file_path] = {
                                        'mtime': stat_info.st_mtime,
                                        'size': stat_info.st_size
                                    }
                                except (OSError, PermissionError):
                                    continue
                    except Exception as e:
                        print(f"Error scanning {path}: {e}")
                        continue
                
                # Check for new or modified files
                for file_path, file_info in current_files.items():
                    if file_path not in self.file_cache:
                        # New file
                        print(f"New file detected: {file_path}")
                        self._queue_change(file_path)
                        changes_detected = True
                    else:
                        cached_info = self.file_cache[file_path]
                        if (file_info['mtime'] != cached_info['mtime'] or 
                            file_info['size'] != cached_info['size']):
                            # Modified file
                            print(f"Modified file detected: {file_path}")
                            self._queue_change(file_path)
                            changes_detected = True
                
                # Check for deleted files
                for file_path in list(self.file_cache.keys()):
                    if file_path not in current_files:
                        # Deleted file
                        print(f"Deleted file detected: {file_path}")
                        self._queue_change(file_path)
                        changes_detected = True
                
                # Update cache
                self.file_cache = current_files
                
                if changes_detected:
                    print(f"Changes detected, scheduling batch update")
                
                # Sleep before next poll
                for _ in range(poll_interval * 10):  # Check every 0.1 seconds if we should stop
                    if not self.running:
                        break
                    time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(poll_interval)
        
        print("FileMonitor loop ended")
    
    def _queue_change(self, file_path):
        """Queue file change for batched processing"""
        # Find the root path this file belongs to
        root_path = None
        for path in self.paths:
            if file_path.startswith(path):
                root_path = path
                break
        
        if root_path:
            self.pending_changes.add(root_path)
            
            # Cancel existing timer and start new one
            if self.batch_timer:
                self.batch_timer.cancel()
            
            # Process changes after delay to batch multiple events
            self.batch_timer = threading.Timer(5.0, self._process_batched_changes)
            self.batch_timer.start()
    
    def _process_batched_changes(self):
        """Process batched file changes"""
        if self.pending_changes and self.callback:
            print(f"Processing batched changes for {len(self.pending_changes)} paths")
            
            # Process each changed root path
            for root_path in self.pending_changes:
                try:
                    print(f"Calling callback for path: {root_path}")
                    self.callback("BATCH_UPDATE", root_path)
                except Exception as e:
                    print(f"Error in callback for {root_path}: {e}")
            
            # Clear pending changes
            self.pending_changes.clear()
        
        self.batch_timer = None
