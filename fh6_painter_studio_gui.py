#!/usr/bin/env python3
import sys
import os
import time
import math
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

# --- Ensure we can import from the tools directory ---
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
try:
    from tools.fh6_painter_generator import run_generator
    from tools.fh6_import_layer_table import run_importer
    from PIL import Image, ImageTk, ImageDraw
    import numpy as np
    HAS_LIBS = True
except ImportError as e:
    HAS_LIBS = False
    IMPORT_ERROR = str(e)

# --- Thread-safe Console I/O Redirector ---
class IORedirector:
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, string):
        self.log_queue.put(string)

    def flush(self):
        pass

# --- Premium Dark Studio GUI Application ---
class ForzaStudioGUI:
    def __init__(self, root, preload_file=None):
        self.root = root
        self.root.title("FORZA STUDIO - FH6 Shape Generator & Importer")
        self.root.geometry("1100x760")
        self.root.minsize(1024, 720)
        
        # --- UI Color Palette ---
        self.bg_main = "#121212"       # Dark Background
        self.bg_card = "#1E1E1E"       # Panel / Card Background
        self.bg_input = "#151515"      # Input Field Background
        self.border_color = "#2A2A2A"   # Card Border
        self.fg_primary = "#FFFFFF"     # White Primary Text
        self.fg_secondary = "#A0A0A0"   # Gray Secondary Text
        
        # Tech green for generation, sky blue for importing
        self.color_green = "#4CAF50"
        self.color_green_hover = "#45a049"
        self.color_green_disabled = "#1E3822"
        
        self.color_blue = "#2196F3"
        self.color_blue_hover = "#0b7dda"
        self.color_blue_disabled = "#132D42"
        
        self.color_btn_default = "#2C2C2C"
        self.color_btn_default_hover = "#3A3A3A"
        
        self.root.configure(bg=self.bg_main)
        
        # Initialize thread-safe data holders
        self.log_queue = queue.Queue()
        self.preview_image_lock = threading.Lock()
        self.latest_canvas_array = None
        self.latest_progress = (0, 100, 0.0, 0.0) # (current, total, speed, eta)
        self.need_preview_update = False
        
        self.active_thread = None
        self.is_generating = False
        self.is_importing = False
        self.auto_load_json_path = None
        
        # Scan profiles
        self.profiles = self.scan_profiles()
        
        # Build UI layout
        self.build_ui()
        self.apply_styles()
        
        # Start background polling timer
        self.root.after(100, self.poll_background_updates)
        
        # Preload file if dragged or supplied
        if preload_file:
            self.entry_file_path.insert(0, os.path.abspath(preload_file))
            self.on_file_changed()
            self.log_to_console(f"Successfully preloaded: {preload_file}\n")
        else:
            self.log_to_console("Welcome to Forza Studio! Load an image or a geometry JSON file to begin.\n")
            
        if not HAS_LIBS:
            self.log_to_console(f"WARNING: Missing dependencies: {IMPORT_ERROR}\n")
            self.log_to_console("Please install required libraries: pip install pillow numpy numba\n")
            messagebox.showerror("Missing Dependencies", f"Required libraries were not found:\n{IMPORT_ERROR}\n\nPlease run:\npip install pillow numpy numba")

    def scan_profiles(self):
        """Scans the 'settings' directory for available .ini configurations."""
        profiles = []
        settings_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")
        if os.path.exists(settings_dir):
            for f in os.listdir(settings_dir):
                if f.endswith(".ini"):
                    path = os.path.join(settings_dir, f)
                    desc = "No description available."
                    # Parse description
                    try:
                        with open(path, "r", encoding="utf-8") as file:
                            for line in file:
                                if line.strip().startswith("description"):
                                    parts = line.split("=", 1)
                                    if len(parts) == 2:
                                        desc = parts[1].strip()
                                    break
                    except Exception:
                        pass
                    profiles.append({
                        "filename": f,
                        "name": os.path.splitext(f)[0],
                        "path": path,
                        "desc": desc
                    })
        # If empty, add a default profile stub
        if not profiles:
            profiles.append({
                "filename": "_default.ini",
                "name": "_default",
                "path": "",
                "desc": "Default system generation profile"
            })
        # Sort so default is first
        profiles.sort(key=lambda x: 0 if x["name"] == "_default" else 1)
        return profiles

    def apply_styles(self):
        """Set up standard TTK style properties for modern flat design."""
        style = ttk.Style()
        style.theme_use('default')
        style.configure(".", background=self.bg_main, foreground=self.fg_primary)
        
        # Card settings
        style.configure("Card.TFrame", background=self.bg_card, borderwidth=1, relief="flat")
        
        # Combobox style
        style.configure("TCombobox", fieldbackground=self.bg_input, background=self.color_btn_default, foreground=self.fg_primary, arrowcolor=self.fg_primary)
        style.map("TCombobox", fieldbackground=[('readonly', self.bg_input)], foreground=[('readonly', self.fg_primary)])
        
        # Label settings
        style.configure("Title.TLabel", font=("Microsoft JhengHei", 12, "bold"), background=self.bg_card, foreground=self.fg_primary)
        style.configure("Text.TLabel", font=("Microsoft JhengHei", 9), background=self.bg_card, foreground=self.fg_secondary)
        style.configure("MetricVal.TLabel", font=("Consolas", 14, "bold"), background=self.bg_card, foreground=self.color_blue)
        style.configure("MetricLbl.TLabel", font=("Microsoft JhengHei", 8), background=self.bg_card, foreground=self.fg_secondary)

        # Progressbar
        style.configure("Custom.Horizontal.TProgressbar", thickness=10, background=self.color_green, troughcolor=self.bg_input, borderwidth=0)

    def build_ui(self):
        """Build the responsive layout of the Forza Studio GUI."""
        # Main layout frame
        main_container = tk.Frame(self.root, bg=self.bg_main)
        main_container.pack(fill="both", expand=True, padx=15, pady=10)
        
        # --- Top Header Bar ---
        header_frame = tk.Frame(main_container, bg=self.bg_main)
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = tk.Label(header_frame, text="FORZA STUDIO", font=("Outfit", 18, "bold"), bg=self.bg_main, fg=self.color_green)
        title_label.pack(side="left")
        
        subtitle_label = tk.Label(header_frame, text="  |  FH6 ONE-STOP LIVERY ENGINE", font=("Microsoft JhengHei", 10, "bold"), bg=self.bg_main, fg=self.fg_secondary)
        subtitle_label.pack(side="left", fill="y")
        
        self.status_lbl = tk.Label(header_frame, text="READY", font=("Consolas", 10, "bold"), bg=self.bg_card, fg="#888888", padx=10, pady=2, bd=1, relief="solid")
        self.status_lbl.pack(side="right")
        
        # --- Workspace Splitting (Left Control vs Right Preview) ---
        workspace = tk.Frame(main_container, bg=self.bg_main)
        workspace.pack(fill="both", expand=True)
        
        # Left Panel (Width ~ 450)
        left_panel = tk.Frame(workspace, bg=self.bg_main, width=450)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Right Panel (Width ~ 550)
        right_panel = tk.Frame(workspace, bg=self.bg_main, width=550)
        right_panel.pack(side="right", fill="both", expand=True)
        right_panel.pack_propagate(False)
        
        # --- LEFT PANEL CARDS ---
        # Card 1: Input Source Configuration
        card_input = ttk.Frame(left_panel, style="Card.TFrame")
        card_input.pack(fill="x", pady=(0, 10), ipady=8)
        
        self.create_card_header(card_input, "1. INPUT SOURCE", "Select target image (PNG/JPG) or geometry JSON file")
        
        input_body = tk.Frame(card_input, bg=self.bg_card)
        input_body.pack(fill="x", padx=15, pady=(5, 5))
        
        self.entry_file_path = tk.Entry(input_body, bg=self.bg_input, fg=self.fg_primary, insertbackground=self.fg_primary, font=("Microsoft JhengHei", 9), bd=0)
        self.entry_file_path.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 5))
        self.entry_file_path.bind("<KeyRelease>", lambda e: self.on_file_changed())
        
        btn_browse = tk.Button(input_body, text="Browse", font=("Microsoft JhengHei", 9, "bold"), bg=self.color_btn_default, fg=self.fg_primary, activebackground=self.color_btn_default_hover, activeforeground=self.fg_primary, bd=0, padx=12, command=self.browse_file)
        btn_browse.pack(side="right", ipady=2)
        
        # Card 2: Livery Generation Parameters
        card_params = ttk.Frame(left_panel, style="Card.TFrame")
        card_params.pack(fill="x", pady=(0, 10), ipady=8)
        
        self.create_card_header(card_params, "2. GENERATOR SETTINGS", "Configure livery shape reconstruction thresholds")
        
        params_body = tk.Frame(card_params, bg=self.bg_card)
        params_body.pack(fill="x", padx=15, pady=5)
        
        # Profile Dropdown
        tk.Label(params_body, text="Speed/Quality Profile:", font=("Microsoft JhengHei", 9), bg=self.bg_card, fg=self.fg_secondary).grid(row=0, column=0, sticky="w", pady=4)
        self.combo_profile = ttk.Combobox(params_body, values=[p["name"] for p in self.profiles], state="readonly", width=35)
        self.combo_profile.grid(row=0, column=1, sticky="we", pady=4, padx=(10, 0))
        self.combo_profile.current(0)
        self.combo_profile.bind("<<ComboboxSelected>>", self.on_profile_selected)
        
        # Profile Description Label
        self.lbl_profile_desc = tk.Label(params_body, text="...", font=("Microsoft JhengHei", 8, "italic"), bg=self.bg_card, fg="#888888", wraplength=380, justify="left")
        self.lbl_profile_desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 8))
        
        # Layer Limits (with game budget note)
        tk.Label(params_body, text="Max Layers/Shapes:", font=("Microsoft JhengHei", 9), bg=self.bg_card, fg=self.fg_secondary).grid(row=2, column=0, sticky="w", pady=4)
        
        self.val_layers = tk.StringVar(value="2000")
        self.entry_layers = tk.Entry(params_body, textvariable=self.val_layers, bg=self.bg_input, fg=self.fg_primary, insertbackground=self.fg_primary, font=("Consolas", 10), bd=0, width=12)
        self.entry_layers.grid(row=2, column=1, sticky="w", pady=4, padx=(10, 0), ipady=3)
        
        lbl_limits_tip = tk.Label(params_body, text="FH6 Game Limits: Bumper up to 1000 | Left/Right/Top up to 3000", font=("Microsoft JhengHei", 8), bg=self.bg_card, fg=self.color_blue)
        lbl_limits_tip.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 8))
        
        # Advanced Overrides
        self.show_adv = tk.BooleanVar(value=False)
        self.chk_adv = tk.Checkbutton(params_body, text="Enable Advanced Sample Override (Use INI settings otherwise)", variable=self.show_adv, font=("Microsoft JhengHei", 9), bg=self.bg_card, fg=self.fg_secondary, selectcolor=self.bg_card, activebackground=self.bg_card, activeforeground=self.fg_primary, bd=0, command=self.toggle_advanced_panel)
        self.chk_adv.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        
        self.adv_frame = tk.Frame(params_body, bg=self.bg_card)
        
        tk.Label(self.adv_frame, text="Candidates (Samples):", font=("Microsoft JhengHei", 9), bg=self.bg_card, fg=self.fg_secondary).grid(row=0, column=0, sticky="w", pady=4)
        self.val_candidates = tk.StringVar(value="20000")
        self.entry_candidates = tk.Entry(self.adv_frame, textvariable=self.val_candidates, bg=self.bg_input, fg=self.fg_primary, insertbackground=self.fg_primary, font=("Consolas", 9), bd=0, width=12)
        self.entry_candidates.grid(row=0, column=1, sticky="w", pady=4, padx=(10, 0), ipady=3)
        
        tk.Label(self.adv_frame, text="Hill-climb Steps:", font=("Microsoft JhengHei", 9), bg=self.bg_card, fg=self.fg_secondary).grid(row=1, column=0, sticky="w", pady=4)
        self.val_steps = tk.StringVar(value="200")
        self.entry_steps = tk.Entry(self.adv_frame, textvariable=self.val_steps, bg=self.bg_input, fg=self.fg_primary, insertbackground=self.fg_primary, font=("Consolas", 9), bd=0, width=12)
        self.entry_steps.grid(row=1, column=1, sticky="w", pady=4, padx=(10, 0), ipady=3)
        
        # Trigger initial description print
        self.on_profile_selected(None)
        
        # Card 3: Action Panel (Double-Button Execution)
        card_actions = ttk.Frame(left_panel, style="Card.TFrame")
        card_actions.pack(fill="x", expand=True, pady=(0, 0), ipady=8)
        
        self.create_card_header(card_actions, "3. WORKSPACE ACTIONS", "Launch shape generation or memory injection pipeline")
        
        actions_body = tk.Frame(card_actions, bg=self.bg_card)
        actions_body.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Start Generation Button (Green)
        self.btn_generate = tk.Button(actions_body, text="開始生成 JSON\nStart Generation", font=("Microsoft JhengHei", 10, "bold"), bg=self.color_green, fg=self.fg_primary, activebackground=self.color_green_hover, activeforeground=self.fg_primary, bd=0, pady=10, command=self.start_generation)
        self.btn_generate.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        # Inject to Game Button (Blue)
        self.btn_inject = tk.Button(actions_body, text="注入至遊戲\nImport to Game", font=("Microsoft JhengHei", 10, "bold"), bg=self.color_blue, fg=self.fg_primary, activebackground=self.color_blue_hover, activeforeground=self.fg_primary, bd=0, pady=10, command=self.start_injection)
        self.btn_inject.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        # Make sure buttons start in correct states
        self.on_file_changed()

        # --- RIGHT PANEL CARDS ---
        # Card 4: Fitment Preview Canvas
        card_preview = ttk.Frame(right_panel, style="Card.TFrame")
        card_preview.pack(fill="both", expand=True, ipady=5)
        
        self.create_card_header(card_preview, "4. LIVE SHAPE FITTING WORKBENCH", "Real-time canvas visualization of Numba JIT geometry fitting")
        
        preview_body = tk.Frame(card_preview, bg=self.bg_card)
        preview_body.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Preview Canvas Container
        self.canvas_size = 380
        self.canvas_preview = tk.Canvas(preview_body, bg="#0E0E0E", width=self.canvas_size, height=self.canvas_size, bd=0, highlightthickness=1, highlightbackground=self.border_color)
        self.canvas_preview.pack(pady=5)
        
        # Draw placeholder cyber graphics on start
        self.draw_cyber_placeholder()
        
        # Live Metrics HUD (4 Slots)
        hud_frame = tk.Frame(preview_body, bg=self.bg_card)
        hud_frame.pack(fill="x", pady=(5, 5))
        
        # Column configuration
        for i in range(4):
            hud_frame.columnconfigure(i, weight=1)
            
        # Metric 1: Layer
        m1_card = tk.Frame(hud_frame, bg=self.bg_card)
        m1_card.grid(row=0, column=0, sticky="we")
        self.lbl_metric_layer = ttk.Label(m1_card, text="0 / 0", style="MetricVal.TLabel")
        self.lbl_metric_layer.pack()
        ttk.Label(m1_card, text="LAYER PROGRESS", style="MetricLbl.TLabel").pack()
        
        # Metric 2: Speed
        m2_card = tk.Frame(hud_frame, bg=self.bg_card)
        m2_card.grid(row=0, column=1, sticky="we")
        self.lbl_metric_speed = ttk.Label(m2_card, text="0.0 L/s", style="MetricVal.TLabel")
        self.lbl_metric_speed.pack()
        ttk.Label(m2_card, text="GENERATION SPEED", style="MetricLbl.TLabel").pack()
        
        # Metric 3: ETA
        m3_card = tk.Frame(hud_frame, bg=self.bg_card)
        m3_card.grid(row=0, column=2, sticky="we")
        self.lbl_metric_eta = ttk.Label(m3_card, text="0s", style="MetricVal.TLabel")
        self.lbl_metric_eta.pack()
        ttk.Label(m3_card, text="ESTIMATED REMAINING", style="MetricLbl.TLabel").pack()
        
        # Metric 4: Progress %
        m4_card = tk.Frame(hud_frame, bg=self.bg_card)
        m4_card.grid(row=0, column=3, sticky="we")
        self.lbl_metric_pct = ttk.Label(m4_card, text="0.0%", style="MetricVal.TLabel")
        self.lbl_metric_pct.pack()
        ttk.Label(m4_card, text="COMPLETION RATIO", style="MetricLbl.TLabel").pack()
        
        # Fluid progress bar
        self.progress_bar = ttk.Progressbar(preview_body, orient="horizontal", mode="determinate", style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", pady=(5, 5))
        
        # --- BOTTOM SYSTEM CONSOLE ---
        card_console = ttk.Frame(main_container, style="Card.TFrame")
        card_console.pack(fill="x", side="bottom", pady=(10, 0))
        
        self.create_card_header(card_console, "5. SYSTEM LOG CONSOLE", "Diagnostic outputs, scanner logs, and engine responses")
        
        console_body = tk.Frame(card_console, bg=self.bg_card)
        console_body.pack(fill="both", expand=True, padx=15, pady=(2, 8))
        
        self.txt_console = scrolledtext.ScrolledText(console_body, height=7, bg="#080808", fg="#00FF66", insertbackground="#00FF66", font=("Consolas", 9), bd=0, highlightthickness=1, highlightbackground="#1A1A1A")
        self.txt_console.pack(fill="both", expand=True)

    def create_card_header(self, parent, title, subtitle):
        """Creates a standardized modern card header inside custom panels."""
        header_frame = tk.Frame(parent, bg=self.bg_card)
        header_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        lbl_title = ttk.Label(header_frame, text=title, style="Title.TLabel")
        lbl_title.pack(anchor="w")
        
        lbl_sub = ttk.Label(header_frame, text=subtitle, style="Text.TLabel")
        lbl_sub.pack(anchor="w")
        
        # Cyber subtle accent line
        accent = tk.Frame(parent, bg=self.border_color, height=1)
        accent.pack(fill="x", padx=15, pady=(2, 5))

    def toggle_advanced_panel(self):
        """Collapses or expands the advanced parameters override panel."""
        if self.show_adv.get():
            self.adv_frame.grid(row=5, column=0, columnspan=2, sticky="we", pady=(5, 0))
        else:
            self.adv_frame.grid_forget()

    def draw_cyber_placeholder(self, text="STUDIO READY"):
        """Draws a clean, dark tech cyberpunk graphic when no active simulation is running."""
        self.canvas_preview.delete("all")
        # Cyber grid lines
        for i in range(10):
            gap = self.canvas_size / 10
            # Horizontal lines
            self.canvas_preview.create_line(0, i * gap, self.canvas_size, i * gap, fill="#151515", width=1)
            # Vertical lines
            self.canvas_preview.create_line(i * gap, 0, i * gap, self.canvas_size, fill="#151515", width=1)
            
        # Circular HUD radar lines
        center = self.canvas_size / 2
        self.canvas_preview.create_oval(center - 150, center - 150, center + 150, center + 150, outline="#222222", width=1)
        self.canvas_preview.create_oval(center - 100, center - 100, center + 100, center + 100, outline="#2A2A2A", width=1)
        self.canvas_preview.create_oval(center - 40, center - 40, center + 40, center + 40, outline="#333333", width=1)
        
        # Crosshair lines
        self.canvas_preview.create_line(center - 160, center, center - 10, center, fill="#333333", width=1)
        self.canvas_preview.create_line(center + 10, center, center + 160, center, fill="#333333", width=1)
        self.canvas_preview.create_line(center, center - 160, center, center - 10, fill="#333333", width=1)
        self.canvas_preview.create_line(center, center + 10, center, center + 160, fill="#333333", width=1)
        
        # Text label in center
        self.canvas_preview.create_text(center, center, text=text, fill=self.fg_secondary, font=("Outfit", 10, "bold"))
        self.canvas_preview.create_text(center, center + 25, text="LOAD INPUT DATA FILE", fill="#555555", font=("Microsoft JhengHei", 8))

    def log_to_console(self, text):
        """Prints a diagnostic log line into the virtual system console."""
        self.txt_console.insert(tk.END, text)
        self.txt_console.see(tk.END)

    def on_profile_selected(self, event):
        """Fires when user selects a profile; updates HUD descriptive elements and pre-populates overrides."""
        idx = self.combo_profile.current()
        if 0 <= idx < len(self.profiles):
            p = self.profiles[idx]
            self.lbl_profile_desc.configure(text=f"Description: {p['desc']}")
            
            # Auto populate advanced values if not override checked
            if not self.show_adv.get() and p["path"]:
                try:
                    with open(p["path"], "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("randomSamples"):
                                self.val_candidates.set(line.split("=", 1)[1].strip())
                            elif line.startswith("mutatedSamples"):
                                self.val_steps.set(line.split("=", 1)[1].strip())
                            elif line.startswith("stopAt"):
                                self.val_layers.set(line.split("=", 1)[1].strip())
                except Exception:
                    pass

    def browse_file(self):
        """Open file picker targeting images or JSONs."""
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[
                ("Supported Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.json)", "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.json"),
                ("Images (*.png;*.jpg;*.jpeg;*.bmp;*.webp)", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"),
                ("Geometry JSON (*.json)", "*.json"),
                ("All files (*.*)", "*.*")
            ]
        )
        if file_path:
            self.entry_file_path.delete(0, tk.END)
            self.entry_file_path.insert(0, os.path.abspath(file_path))
            self.on_file_changed()

    def on_file_changed(self):
        """Analyzes input file type and dynamically configures button availability & visuals."""
        path = self.entry_file_path.get().strip()
        if not path:
            self.btn_generate.configure(state="disabled", bg=self.bg_card, fg="#555555")
            self.btn_inject.configure(state="disabled", bg=self.bg_card, fg="#555555")
            return
            
        ext = os.path.splitext(path.lower())[1]
        
        # Image patterns
        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
            # Image Loaded: Enable Generation, Disable Injection
            self.btn_generate.configure(state="normal", bg=self.color_green, fg=self.fg_primary)
            self.btn_inject.configure(state="disabled", bg=self.color_green_disabled, fg="#888888")
            
        # JSON pattern
        elif ext == ".json":
            # JSON Loaded: Disable Generation, Enable Injection
            self.btn_generate.configure(state="disabled", bg=self.color_blue_disabled, fg="#888888")
            self.btn_inject.configure(state="normal", bg=self.color_blue, fg=self.fg_primary)
            
        else:
            # Unidentified format
            self.btn_generate.configure(state="disabled", bg=self.bg_card, fg="#555555")
            self.btn_inject.configure(state="disabled", bg=self.bg_card, fg="#555555")

    def lock_ui(self):
        """Disables controls during background executions to maintain stability."""
        self.entry_file_path.configure(state="disabled")
        self.combo_profile.configure(state="disabled")
        self.entry_layers.configure(state="disabled")
        self.entry_candidates.configure(state="disabled")
        self.entry_steps.configure(state="disabled")
        self.chk_adv.configure(state="disabled")
        
        self.btn_generate.configure(state="disabled")
        self.btn_inject.configure(state="disabled")

    def unlock_ui(self):
        """Enables UI elements once computing threads terminate."""
        self.entry_file_path.configure(state="normal")
        self.combo_profile.configure(state="readonly")
        self.entry_layers.configure(state="normal")
        self.entry_candidates.configure(state="normal")
        self.entry_steps.configure(state="normal")
        self.chk_adv.configure(state="normal")
        
        self.on_file_changed()

    # --- Thread-Safe Update Hook ---
    def poll_background_updates(self):
        """Cycles every 100ms in the main loop to dump log queues and repaint previews."""
        # 1. Update text console
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.log_to_console(msg)
            except queue.Empty:
                break
                
        # 2. Update Canvas Preview from shared numpy variable
        if self.need_preview_update:
            with self.preview_image_lock:
                arr = self.latest_canvas_array.copy() if self.latest_canvas_array is not None else None
                self.need_preview_update = False
                
            if arr is not None:
                try:
                    # Clip numpy array and convert float32 to uint8
                    arr_clipped = np.clip(arr, 0.0, 255.0).astype(np.uint8)
                    pil_img = Image.fromarray(arr_clipped)
                    # Resize to fit panel
                    pil_resized = pil_img.resize((self.canvas_size, self.canvas_size), Image.Resampling.NEAREST)
                    self.img_tk = ImageTk.PhotoImage(pil_resized)
                    self.canvas_preview.delete("all")
                    self.canvas_preview.create_image(0, 0, anchor="nw", image=self.img_tk)
                except Exception as e:
                    self.log_to_console(f"\n[Preview Error] {e}\n")
                    
        # 3. Update HUD Metrics
        if self.is_generating:
            curr, total, speed, eta = self.latest_progress
            self.lbl_metric_layer.configure(text=f"{curr} / {total}")
            self.lbl_metric_speed.configure(text=f"{speed:.1f} L/s")
            self.lbl_metric_eta.configure(text=f"{eta:.0f}s")
            pct = (curr * 100.0 / total) if total > 0 else 0.0
            self.lbl_metric_pct.configure(text=f"{pct:.1f}%")
            self.progress_bar["value"] = pct
            
        # 4. Check Thread Completion for UX Automatic Transitions
        if self.active_thread and not self.active_thread.is_alive():
            self.active_thread = None
            
            # Restore stdout/stderr
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            
            self.unlock_ui()
            
            if self.is_generating:
                self.is_generating = False
                self.status_lbl.configure(text="GEN DONE", fg=self.color_green)
                self.log_to_console("\n[System] Shape generation process completed.\n")
                
                # Check for automatic loading transition
                if self.auto_load_json_path and os.path.exists(self.auto_load_json_path):
                    self.log_to_console(f"[UX Transition] Automatically loading generated JSON:\n-> {self.auto_load_json_path}\n")
                    self.entry_file_path.delete(0, tk.END)
                    self.entry_file_path.insert(0, os.path.abspath(self.auto_load_json_path))
                    self.on_file_changed()
                    self.auto_load_json_path = None
                    # Visual pulse notification on inject button
                    self.btn_inject.focus_set()
                    
            elif self.is_importing:
                self.is_importing = False
                self.status_lbl.configure(text="INJECT DONE", fg=self.color_blue)
                self.log_to_console("\n[System] Livery memory injection completed.\n")
                
        # Loop again in 100ms
        self.root.after(100, self.poll_background_updates)

    # --- Shape Generation Thread Launcher ---
    def start_generation(self):
        """Collects GUI configuration and starts the Numba shape generation loop on a worker thread."""
        if self.active_thread:
            return
            
        img_path = self.entry_file_path.get().strip()
        if not os.path.exists(img_path):
            messagebox.showerror("Error", f"Input file not found:\n{img_path}")
            return
            
        # Layers Limit Check
        try:
            layers = int(self.val_layers.get())
            if not (500 <= layers <= 3000):
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "Invalid Layers Limit.\nPlease enter an integer between 500 and 3000.")
            return
            
        # Determine output JSON name
        base_name, _ = os.path.splitext(img_path)
        output_json = f"{base_name}.json"
        self.auto_load_json_path = output_json
        
        # Determine profile INI path
        profile_idx = self.combo_profile.current()
        profile_path = self.profiles[profile_idx]["path"] if 0 <= profile_idx < len(self.profiles) else None
        
        # Override values
        candidates = None
        steps = None
        if self.show_adv.get():
            try:
                candidates = int(self.val_candidates.get())
                steps = int(self.val_steps.get())
            except ValueError:
                messagebox.showerror("Error", "Advanced Overrides must be valid integers.")
                return
                
        # Pre-reset preview metrics
        self.latest_progress = (0, layers, 0.0, 0.0)
        self.lbl_metric_layer.configure(text=f"0 / {layers}")
        self.lbl_metric_speed.configure(text="0.0 L/s")
        self.lbl_metric_eta.configure(text="0s")
        self.lbl_metric_pct.configure(text="0.0%")
        self.progress_bar["value"] = 0
        
        # Lock GUI controls
        self.lock_ui()
        self.is_generating = True
        self.status_lbl.configure(text="GENERATING", fg=self.color_green)
        
        # Redirect prints to queue
        redirector = IORedirector(self.log_queue)
        sys.stdout = redirector
        sys.stderr = redirector
        
        # Clear Console Log Box
        self.txt_console.delete("1.0", tk.END)
        self.log_to_console("[System] Triggering high-performance Python shape generator...\n")
        
        # Progress callback hook
        def generator_cb(curr, total, speed, eta, canvas_arr):
            with self.preview_image_lock:
                self.latest_canvas_array = canvas_arr.copy()
                self.latest_progress = (curr, total, speed, eta)
                self.need_preview_update = True
                
        # Launch Worker Thread
        self.active_thread = threading.Thread(
            target=run_generator,
            args=(img_path, output_json, profile_path, layers, candidates, steps, generator_cb),
            daemon=True
        )
        self.active_thread.start()

    # --- Livery Memory Injection Thread Launcher ---
    def start_injection(self):
        """Launches Win32 memory writing thread on the active game process."""
        if self.active_thread:
            return
            
        json_path = self.entry_file_path.get().strip()
        if not os.path.exists(json_path):
            messagebox.showerror("Error", f"Geometry JSON file not found:\n{json_path}")
            return
            
        # Layers count based on GUI value (matching our search count)
        try:
            layers = int(self.val_layers.get())
        except ValueError:
            layers = 3000
            
        # Confirm user opens ungrouped shapes
        confirm = messagebox.askyesno(
            "Game Injection Confirmation",
            "Before injecting, please ensure:\n"
            "1. Forza Horizon 6 (forzahorizon6.exe) is running.\n"
            f"2. You are inside the Vinyl Group Editor with a fresh template of exactly {layers} ungrouped circular layers.\n\n"
            "Would you like to proceed with memory injection?"
        )
        
        if not confirm:
            return
            
        # Lock UI
        self.lock_ui()
        self.is_importing = True
        self.status_lbl.configure(text="INJECTING", fg=self.color_blue)
        
        # Redirect prints to queue
        redirector = IORedirector(self.log_queue)
        sys.stdout = redirector
        sys.stderr = redirector
        
        # Clear log box
        self.txt_console.delete("1.0", tk.END)
        self.log_to_console("[System] Opening Win32 process handles for forzahorizon6.exe...\n")
        
        # Clean HUD Radar Canvas to signal injection
        self.draw_cyber_placeholder(text="INJECTING GEOMETRY")
        self.progress_bar["value"] = 0
        self.lbl_metric_pct.configure(text="HUD LOCKED")
        
        # Launch Worker Thread
        self.active_thread = threading.Thread(
            target=run_importer,
            kwargs={
                "json_path": json_path,
                "layers": layers,
                "dry_run": False,
                "reverse": False,
                "include_header": False,
                "no_cache": False,
                "scale_div": 63.0,
                "coord_scale": 1.0,
                "max_candidates": 200000
            },
            daemon=True
        )
        self.active_thread.start()

# --- Main Entry Script ---
def main():
    preload = None
    if len(sys.argv) > 1:
        preload = sys.argv[1]
        
    root = tk.Tk()
    app = ForzaStudioGUI(root, preload_file=preload)
    root.mainloop()

if __name__ == "__main__":
    main()
