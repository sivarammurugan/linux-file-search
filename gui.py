#!/usr/bin/env python3
"""
GUI File Search App for Linux
A simple GUI interface for the file search functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import os
import subprocess
from main import FileSearchApp, FileIndexer


class FileSearchGUI:
    """GUI wrapper for the file search application"""
    
    def __init__(self):
        self.root = tk.Tk(className="Filesearch")
        self.root.title("File Search - Linux")
        self.root.geometry("800x600")
        
        self.app = FileSearchApp()
        self.search_thread = None
        self.file_monitor = None
        
        self.setup_ui()
        self.bind_events()
        
        # Ask user if they want to build initial index
        self.root.after(100, self.prompt_initial_index)
        
        # Start automatic file monitoring
        self.root.after(1000, self.start_file_monitoring)
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Search frame
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Search entry
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
        self.search_entry.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        
        # Search options
        options_frame = ttk.Frame(search_frame)
        options_frame.pack(side=tk.RIGHT)
        
        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Case sensitive", 
                       variable=self.case_sensitive_var).pack(side=tk.LEFT, padx=5)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(buttons_frame, text="Build Index", 
                  command=self.build_index).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="Update Index", 
                  command=self.incremental_update_index).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear", 
                  command=self.clear_results).pack(side=tk.LEFT, padx=5)
        
        # Auto-monitor toggle button
        self.auto_monitor_var = tk.BooleanVar(value=True)
        self.auto_monitor_btn = ttk.Checkbutton(
            buttons_frame, 
            text="Auto-Monitor", 
            variable=self.auto_monitor_var,
            command=self.toggle_auto_monitoring
        )
        self.auto_monitor_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(buttons_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.RIGHT)
        
        # Monitoring indicator
        self.monitor_indicator = ttk.Label(buttons_frame, text="●", foreground="gray")
        self.monitor_indicator.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Progress bar (initially hidden)
        self.progress_bar = ttk.Progressbar(buttons_frame, mode='indeterminate')
        # Don't pack it initially
        
        # Results frame with scrollbar
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for results
        columns = ('Name', 'Size', 'Modified', 'Path')
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        
        # Configure columns
        self.results_tree.heading('Name', text='Name')
        self.results_tree.heading('Size', text='Size')
        self.results_tree.heading('Modified', text='Modified')
        self.results_tree.heading('Path', text='Path')
        
        self.results_tree.column('Name', width=200)
        self.results_tree.column('Size', width=80)
        self.results_tree.column('Modified', width=120)
        self.results_tree.column('Path', width=400)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        
        self.results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and treeview
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Open File", command=self.open_file)
        self.context_menu.add_command(label="Open Folder", command=self.open_folder)
        self.context_menu.add_command(label="Copy Path", command=self.copy_path)
        
    def bind_events(self):
        """Bind keyboard and mouse events"""
        self.search_var.trace('w', self.on_search_change)
        self.results_tree.bind('<Button-3>', self.show_context_menu)  # Right click
        self.results_tree.bind('<Double-1>', self.open_file)  # Double click
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        
    def prompt_initial_index(self):
        """Prompt user to build initial index or update existing ones"""
        # Check if there are existing indexes
        indexed_paths = self.app.indexer.get_indexed_paths()
        
        if indexed_paths:
            # Show existing indexes and ask what to do
            paths_info = "\n".join([
                f"• {path} ({file_count} files, indexed {time.strftime('%Y-%m-%d %H:%M', time.localtime(last_indexed))})"
                for path, last_indexed, file_count in indexed_paths
            ])
            
            result = messagebox.askyesnocancel(
                "Existing Index Found", 
                f"Found existing file indexes:\n\n{paths_info}\n\n"
                f"Would you like to:\n"
                f"• Yes: Update existing indexes incrementally (faster)\n"
                f"• No: Build a new index from scratch\n"
                f"• Cancel: Continue without indexing"
            )
            
            if result is True:  # Yes - incremental update
                self.incremental_update_index()
            elif result is False:  # No - build new index
                self.build_index()
            # Cancel - do nothing
            
        else:
            # No existing index - ask to build one
            if messagebox.askyesno("Build Index", 
                                  "No file index found. Would you like to build one?\n"
                                  "This will help you search files faster."):
                self.build_index()
        
    def on_search_change(self, *args):
        """Handle search text changes"""
        query = self.search_var.get().strip()
        if len(query) >= 2:  # Start searching after 2 characters
            # Cancel any pending search
            if hasattr(self, 'search_after_id'):
                self.root.after_cancel(self.search_after_id)
            
            # Delay search slightly to avoid searching on every keystroke
            self.search_after_id = self.root.after(300, lambda: self.perform_search(query))
        elif len(query) == 0:
            self.clear_results()
    
    def perform_search(self, query):
        """Perform search"""
        try:
            # Check if index exists
            if not hasattr(self.app.indexer, 'conn') or self.app.indexer.conn is None:
                self.status_var.set("No index found. Please build an index first.")
                return
                
            self.status_var.set("Searching...")
            
            start_time = time.time()
            results = self.app.indexer.search(query, 200, self.case_sensitive_var.get())
            search_time = (time.time() - start_time) * 1000
            
            # Update results display
            self.update_results(results, search_time)
            
        except Exception as ex:
            messagebox.showerror("Search Error", str(ex))
    
    def update_results(self, results, search_time):
        """Update results display"""
        # Clear existing results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Add new results
        for result in results:
            size_str = self._format_size(result['size'])
            mod_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(result['modified']))
            
            self.results_tree.insert('', tk.END, values=(
                result['name'],
                size_str,
                mod_time,
                result['path']
            ))
        
        # Update status
        status = f"Found {len(results)} files ({search_time:.1f}ms)"
        self.status_var.set(status)
    
    def _format_size(self, size_bytes):
        """Format file size"""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f}KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f}MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.1f}GB"
    
    def build_index(self):
        """Build file index"""
        path = filedialog.askdirectory(title="Select directory to index",
                                     initialdir="/home")
        if path:
            # Show progress bar
            self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
            self.progress_bar.start()
            self.status_var.set("Building index...")
            
            print(f"Indexing files in {path}...")
            
            def index_worker():
                try:
                    # Collect file information in background thread
                    file_list = []
                    import os
                    from main import FileIndexer
                    
                    # Walk through directory structure
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            try:
                                file_path = os.path.join(root, file)
                                stat_info = os.stat(file_path)
                                
                                # Clean filename for database storage
                                clean_name = file.encode('utf-8', errors='replace').decode('utf-8')
                                clean_path = file_path.encode('utf-8', errors='replace').decode('utf-8')
                                
                                file_info = {
                                    'name': clean_name,
                                    'path': clean_path,
                                    'size': stat_info.st_size,
                                    'modified': int(stat_info.st_mtime)
                                }
                                file_list.append(file_info)
                                
                                # Update status periodically
                                if len(file_list) % 1000 == 0:
                                    self.root.after(0, lambda count=len(file_list): 
                                                   self.status_var.set(f"Indexing... {count} files found"))
                                    
                            except (OSError, PermissionError):
                                continue  # Skip files we can't access
                    
                    # Now update the database in the main thread
                    self.root.after(0, lambda: self.update_index_with_files(file_list, path))
                    
                except Exception as ex:
                    error_msg = str(ex)
                    print(f"Index error: {error_msg}")
                    self.root.after(0, lambda: self.handle_index_error(error_msg))
            
            thread = threading.Thread(target=index_worker)
            thread.daemon = True
            thread.start()
    
    def update_index_with_files(self, file_list, path):
        """Update the index with collected files (runs in main thread)"""
        try:
            # Close existing indexer and create new one
            self.app.indexer.close()
            self.app.indexer = FileIndexer()
            
            # Clear existing index for this path
            self.app.indexer.conn.execute("DELETE FROM files WHERE path LIKE ?", (path + "%",))
            self.app.indexer.conn.commit()
            
            # Insert files in batches
            batch_size = 1000
            current_time = int(time.time())
            
            for i in range(0, len(file_list), batch_size):
                batch = file_list[i:i + batch_size]
                file_data = [(f['name'], f['path'], f['size'], f['modified'], current_time) for f in batch]
                
                self.app.indexer.conn.executemany(
                    "INSERT INTO files (name, path, size, modified, indexed_at) VALUES (?, ?, ?, ?, ?)",
                    file_data
                )
                self.app.indexer.conn.commit()
                
                # Update progress
                progress = (i + len(batch)) / len(file_list) * 100
                self.status_var.set(f"Indexing... {i + len(batch)}/{len(file_list)} files ({progress:.1f}%)")
                self.root.update_idletasks()
            
            # Update index_paths table to record this indexing operation
            self.app.indexer.conn.execute('''
                INSERT OR REPLACE INTO index_paths (path, last_indexed, file_count)
                VALUES (?, ?, ?)
            ''', (path, current_time, len(file_list)))
            self.app.indexer.conn.commit()
            
            # Hide progress bar and show success
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.status_var.set(f"Index built successfully - {len(file_list)} files indexed")
            print(f"Index built successfully! Indexed {len(file_list)} files")
            
            # Restart file monitoring for the new indexed path
            if self.auto_monitor_var.get():
                self.root.after(1000, self.start_file_monitoring)
            
        except Exception as ex:
            error_msg = str(ex)
            print(f"Index update error: {error_msg}")
            self.handle_index_error(error_msg)
    
    def handle_index_error(self, error_msg):
        """Handle index building errors"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        messagebox.showerror("Index Error", error_msg)
        self.status_var.set("Index build failed")
    
    def incremental_update_index(self):
        """Perform incremental update of existing indexes"""
        # Get list of indexed paths
        indexed_paths = self.app.indexer.get_indexed_paths()
        
        if not indexed_paths:
            messagebox.showinfo("No Index", "No paths have been indexed yet. Please build an index first.")
            return
            
        # If only one path, update it directly
        if len(indexed_paths) == 1:
            path = indexed_paths[0][0]
            self._perform_incremental_update(path)
            return
            
        # Multiple paths - let user choose
        self._show_path_selection_dialog(indexed_paths)
    
    def _show_path_selection_dialog(self, indexed_paths):
        """Show dialog to select which paths to update"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Paths to Update")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        ttk.Label(dialog, text="Select paths to update incrementally:").pack(pady=10)
        
        # Listbox with checkboxes (using Treeview)
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ('Path', 'Files', 'Last Indexed')
        tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings')
        tree.heading('#0', text='Select')
        tree.heading('Path', text='Path')
        tree.heading('Files', text='Files')
        tree.heading('Last Indexed', text='Last Indexed')
        
        tree.column('#0', width=50)
        tree.column('Path', width=300)
        tree.column('Files', width=80)
        tree.column('Last Indexed', width=150)
        
        # Add paths to tree
        for path, last_indexed, file_count in indexed_paths:
            indexed_time = time.strftime('%Y-%m-%d %H:%M', time.localtime(last_indexed))
            tree.insert('', tk.END, text='☐', values=(path, file_count, indexed_time))
        
        # Track selected items
        selected_items = set()
        
        def toggle_selection(event):
            item = tree.selection()[0] if tree.selection() else None
            if item:
                if item in selected_items:
                    selected_items.remove(item)
                    tree.item(item, text='☐')
                else:
                    selected_items.add(item)
                    tree.item(item, text='☑')
        
        tree.bind('<Button-1>', toggle_selection)
        tree.pack(fill=tk.BOTH, expand=True)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def update_selected():
            if not selected_items:
                messagebox.showwarning("No Selection", "Please select at least one path to update.")
                return
                
            selected_paths = []
            for item in selected_items:
                path = tree.item(item)['values'][0]
                selected_paths.append(path)
            
            dialog.destroy()
            for path in selected_paths:
                self._perform_incremental_update(path)
        
        def update_all():
            dialog.destroy()
            for path, _, _ in indexed_paths:
                self._perform_incremental_update(path)
        
        def select_all():
            for item in tree.get_children():
                selected_items.add(item)
                tree.item(item, text='☑')
        
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Update Selected", command=update_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Update All", command=update_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _perform_incremental_update(self, path):
        """Perform incremental update for a specific path"""
        # Show progress bar
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress_bar.start()
        self.status_var.set(f"Updating index for {path}...")
        
        print(f"Incrementally updating index for {path}...")
        
        def update_worker():
            try:
                # Perform incremental update in background thread
                import os
                from main import FileIndexer
                
                # Create a new connection for this thread (SQLite threading requirement)
                temp_indexer = FileIndexer()
                
                # Collect information about changes
                current_files = set()
                new_files = []
                updated_files = []
                
                for root, dirs, files in os.walk(path):
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
                            
                            # Clean filenames
                            clean_name = file.encode('utf-8', errors='replace').decode('utf-8')
                            clean_path = file_path.encode('utf-8', errors='replace').decode('utf-8')
                            
                            file_info = {
                                'name': clean_name,
                                'path': clean_path,
                                'size': stat_info.st_size,
                                'modified': modified_time
                            }
                            
                            # Check if file exists in index (using thread-local connection)
                            cursor = temp_indexer.conn.execute(
                                "SELECT modified FROM files WHERE path = ?", (clean_path,)
                            )
                            existing = cursor.fetchone()
                            
                            if not existing:
                                new_files.append(file_info)
                            elif existing[0] != modified_time:
                                updated_files.append(file_info)
                                
                            # Update status periodically
                            total_processed = len(new_files) + len(updated_files)
                            if total_processed % 500 == 0:
                                self.root.after(0, lambda count=total_processed: 
                                               self.status_var.set(f"Scanning... {count} changes found"))
                                
                        except (OSError, PermissionError):
                            continue
                
                # Close the temporary connection
                temp_indexer.close()
                
                # Update the database in main thread
                self.root.after(0, lambda: self._apply_incremental_changes(
                    path, current_files, new_files, updated_files))
                
            except Exception as ex:
                error_msg = str(ex)
                print(f"Incremental update error: {error_msg}")
                self.root.after(0, lambda: self._handle_incremental_error(error_msg))
        
        thread = threading.Thread(target=update_worker)
        thread.daemon = True
        thread.start()
    
    def _apply_incremental_changes(self, path, current_files, new_files, updated_files):
        """Apply incremental changes to the database (runs in main thread)"""
        try:
            current_time = int(time.time())
            
            # Add new files
            if new_files:
                new_data = [(f['name'], f['path'], f['size'], f['modified'], current_time) for f in new_files]
                self.app.indexer.conn.executemany(
                    "INSERT INTO files (name, path, size, modified, indexed_at) VALUES (?, ?, ?, ?, ?)",
                    new_data
                )
            
            # Update modified files
            if updated_files:
                for f in updated_files:
                    self.app.indexer.conn.execute('''
                        UPDATE files SET name = ?, size = ?, modified = ?, indexed_at = ?
                        WHERE path = ?
                    ''', (f['name'], f['size'], f['modified'], current_time, f['path']))
            
            # Remove deleted files
            cursor = self.app.indexer.conn.execute(
                "SELECT path FROM files WHERE path LIKE ?", (path + "%",)
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
                    self.app.indexer.conn.execute(
                        f"DELETE FROM files WHERE path IN ({placeholders})",
                        batch
                    )
                print(f"GUI: Removed {len(deleted_files)} deleted files from index")
            
            # Update index_paths table
            self.app.indexer.conn.execute('''
                INSERT OR REPLACE INTO index_paths (path, last_indexed, file_count)
                VALUES (?, ?, ?)
            ''', (path, current_time, len(current_files)))
            
            self.app.indexer.conn.commit()
            
            # Hide progress bar and show success
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            
            total_changes = len(new_files) + len(updated_files) + len(deleted_files)
            message = (f"Incremental update complete for {os.path.basename(path)}:\n"
                      f"New: {len(new_files)}, Updated: {len(updated_files)}, "
                      f"Deleted: {len(deleted_files)}")
            self.status_var.set(f"Update complete - {total_changes} changes")
            print(message)
            
        except Exception as ex:
            error_msg = str(ex)
            print(f"Apply changes error: {error_msg}")
            self._handle_incremental_error(error_msg)
    
    def _handle_incremental_error(self, error_msg):
        """Handle incremental update errors"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        messagebox.showerror("Update Error", error_msg)
        self.status_var.set("Update failed")
    
    def toggle_auto_monitoring(self):
        """Toggle automatic file monitoring on/off"""
        if self.auto_monitor_var.get():
            # Start monitoring
            self.start_file_monitoring()
        else:
            # Stop monitoring
            self.stop_file_monitoring()
            self.monitor_indicator.config(foreground="gray")
    
    def update_monitor_indicator(self, active=False):
        """Update the monitoring indicator"""
        if active:
            self.monitor_indicator.config(foreground="green")
            self.monitor_indicator.config(text="●")
        else:
            self.monitor_indicator.config(foreground="gray")
            self.monitor_indicator.config(text="●")

    def clear_results(self):
        """Clear search results"""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.status_var.set("Ready")
    
    def show_context_menu(self, event):
        """Show context menu"""
        item = self.results_tree.selection()[0] if self.results_tree.selection() else None
        if item:
            self.context_menu.post(event.x_root, event.y_root)
    
    def open_file(self, event=None):
        """Open selected file"""
        selection = self.results_tree.selection()
        if selection:
            item = selection[0]
            file_path = self.results_tree.item(item)['values'][3]
            import subprocess
            try:
                subprocess.run(['xdg-open', file_path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
    
    def open_folder(self):
        """Open folder containing selected file"""
        selection = self.results_tree.selection()
        if selection:
            item = selection[0]
            file_path = self.results_tree.item(item)['values'][3]
            import os
            import subprocess
            folder_path = os.path.dirname(file_path)
            try:
                subprocess.run(['xdg-open', folder_path])
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def copy_path(self):
        """Copy file path to clipboard"""
        selection = self.results_tree.selection()
        if selection:
            item = selection[0]
            file_path = self.results_tree.item(item)['values'][3]
            self.root.clipboard_clear()
            self.root.clipboard_append(file_path)
            self.status_var.set("Path copied to clipboard")
    
    def start_file_monitoring(self):
        """Start automatic file monitoring for indexed paths"""
        try:
            # Import file monitor
            from file_monitor import FileMonitor
            
            # Get indexed paths
            indexed_paths = self.app.indexer.get_indexed_paths()
            
            if indexed_paths:
                # Create file monitor for all indexed paths
                paths_to_monitor = [path for path, _, _ in indexed_paths]
                
                # Set up monitoring callback
                def on_file_change(event_type, file_path):
                    """Handle file system events"""
                    if event_type == "BATCH_UPDATE":
                        # Schedule incremental update on main thread
                        self.root.after(0, lambda: self._handle_file_change_batch(file_path))
                
                # Start monitoring
                self.file_monitor = FileMonitor(paths_to_monitor, on_file_change)
                
                if self.file_monitor.start():
                    print(f"Started automatic monitoring of {len(paths_to_monitor)} indexed paths")
                    self.status_var.set(f"Auto-monitoring {len(paths_to_monitor)} paths")
                    self.update_monitor_indicator(True)
                else:
                    print("Failed to start file monitoring")
                    self.file_monitor = None
                    self.update_monitor_indicator(False)
                
        except ImportError as e:
            print(f"File monitoring not available: {e}")
        except Exception as ex:
            print(f"Failed to start file monitoring: {ex}")
    
    def _handle_file_change_batch(self, root_path):
        """Handle batched file system change events"""
        try:
            print(f"Processing automatic incremental update for: {root_path}")
            
            # Only update if no indexing operation is currently running
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_viewable():
                print("Skipping automatic update - manual operation in progress")
                # Reschedule after current operation
                self.root.after(10000, lambda: self._handle_file_change_batch(root_path))
                return
            
            # Perform incremental update
            self._perform_automatic_incremental_update(root_path)
                    
        except Exception as ex:
            print(f"Error handling file change batch: {ex}")
    
    def _perform_automatic_incremental_update(self, path):
        """Perform automatic incremental update (less intrusive than manual update)"""
        # Don't show progress bar for automatic updates to avoid interrupting user
        print(f"Auto-updating index for {path}...")
        
        # Store original status
        original_status = self.status_var.get()
        self.status_var.set(f"Auto-updating index...")
        
        def update_worker():
            try:
                # Perform incremental update in background thread
                import os
                from main import FileIndexer
                
                # Create a new connection for this thread (SQLite threading requirement)
                temp_indexer = FileIndexer()
                
                # Collect information about changes
                current_files = set()
                new_files = []
                updated_files = []
                
                for root, dirs, files in os.walk(path):
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
                            
                            # Clean filenames
                            clean_name = file.encode('utf-8', errors='replace').decode('utf-8')
                            clean_path = file_path.encode('utf-8', errors='replace').decode('utf-8')
                            
                            file_info = {
                                'name': clean_name,
                                'path': clean_path,
                                'size': stat_info.st_size,
                                'modified': modified_time
                            }
                            
                            # Check if file exists in index (using thread-local connection)
                            cursor = temp_indexer.conn.execute(
                                "SELECT modified FROM files WHERE path = ?", (clean_path,)
                            )
                            existing = cursor.fetchone()
                            
                            if not existing:
                                new_files.append(file_info)
                            elif existing[0] != modified_time:
                                updated_files.append(file_info)
                                
                        except (OSError, PermissionError):
                            continue
                
                # Close the temporary connection
                temp_indexer.close()
                
                # Update the database in main thread
                self.root.after(0, lambda: self._apply_automatic_incremental_changes(
                    path, current_files, new_files, updated_files, original_status))
                
            except Exception as ex:
                error_msg = str(ex)
                print(f"Automatic incremental update error: {error_msg}")
                self.root.after(0, lambda: self.status_var.set(original_status))
        
        thread = threading.Thread(target=update_worker)
        thread.daemon = True
        thread.start()
    
    def _apply_automatic_incremental_changes(self, path, current_files, new_files, updated_files, original_status):
        """Apply automatic incremental changes to the database (runs in main thread)"""
        try:
            current_time = int(time.time())
            
            # Add new files
            if new_files:
                new_data = [(f['name'], f['path'], f['size'], f['modified'], current_time) for f in new_files]
                self.app.indexer.conn.executemany(
                    "INSERT INTO files (name, path, size, modified, indexed_at) VALUES (?, ?, ?, ?, ?)",
                    new_data
                )
            
            # Update modified files
            if updated_files:
                for f in updated_files:
                    self.app.indexer.conn.execute('''
                        UPDATE files SET name = ?, size = ?, modified = ?, indexed_at = ?
                        WHERE path = ?
                    ''', (f['name'], f['size'], f['modified'], current_time, f['path']))
            
            # Remove deleted files
            cursor = self.app.indexer.conn.execute(
                "SELECT path FROM files WHERE path LIKE ?", (path + "%",)
            )
            indexed_files = {row[0] for row in cursor.fetchall()}
            deleted_files = indexed_files - current_files
            
            if deleted_files:
                placeholders = ",".join("?" * len(deleted_files))
                self.app.indexer.conn.execute(
                    f"DELETE FROM files WHERE path IN ({placeholders})",
                    list(deleted_files)
                )
            
            # Update index_paths table
            self.app.indexer.conn.execute('''
                INSERT OR REPLACE INTO index_paths (path, last_indexed, file_count)
                VALUES (?, ?, ?)
            ''', (path, current_time, len(current_files)))
            
            self.app.indexer.conn.commit()
            
            total_changes = len(new_files) + len(updated_files) + len(deleted_files)
            
            if total_changes > 0:
                message = (f"Auto-updated {os.path.basename(path)}: "
                          f"{len(new_files)} new, {len(updated_files)} modified, "
                          f"{len(deleted_files)} deleted")
                print(message)
                
                # Show brief notification in status
                self.status_var.set(f"Auto-updated: {total_changes} changes")
                # Restore original status after 3 seconds
                self.root.after(3000, lambda: self.status_var.set(original_status))
            else:
                print(f"Auto-update completed for {path} - no changes detected")
                self.status_var.set(original_status)
            
        except Exception as ex:
            error_msg = str(ex)
            print(f"Error applying automatic incremental changes: {error_msg}")
            self.status_var.set(original_status)
    
    def stop_file_monitoring(self):
        """Stop file monitoring"""
        if self.file_monitor:
            try:
                self.file_monitor.stop()
                self.file_monitor = None
                self.update_monitor_indicator(False)
                print("Stopped file monitoring")
            except Exception as ex:
                print(f"Error stopping file monitoring: {ex}")
    
    def run(self):
        """Start the GUI application"""
        try:
            self.root.mainloop()
        finally:
            self.stop_file_monitoring()
            if hasattr(self.app, 'cleanup'):
                self.app.cleanup()


def main():
    """Main entry point for GUI"""
    app = FileSearchGUI()
    app.run()


if __name__ == "__main__":
    main()
