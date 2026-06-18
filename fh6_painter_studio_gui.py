#!/usr/bin/env python3
import os
import sys

# 阻斷隱式 Vulkan Layers（如 Game Capture, OBS, Discord overlay 等）注入，防止產生大量垃圾調試輸出並提升啟動穩定度
os.environ["VK_LOADER_LAYERS_DISABLE"] = "~implicit~"
os.environ["DISABLE_OBS_CAPTURE"] = "1"

import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# --- Real-time Log Redirector for GUI Diagnostics ---
global_log_buffer = []


class LogRedirector:
    def __init__(self, buffer_list, original_stream=None):
        self.buffer_list = buffer_list
        self.original_stream = original_stream

    def write(self, string):
        self.buffer_list.append(string)
        if self.original_stream is not None:
            try:
                self.original_stream.write(string)
            except Exception:
                pass

    def flush(self):
        if self.original_stream is not None:
            try:
                self.original_stream.flush()
            except Exception:
                pass


sys.stdout = LogRedirector(global_log_buffer, sys.stdout)
sys.stderr = LogRedirector(global_log_buffer, sys.stderr)

# --- Ensure we can import from the tools directory ---
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageTk

    from evaluators import EvaluatorFactory
    from tools.fh6_import_layer_table import run_importer
    from tools.fh6_painter_generator import run_generator

    HAS_LIBS = True
except ImportError as e:
    HAS_LIBS = False
    IMPORT_ERROR = str(e)


def get_project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# --- Lightweight Custom Tooltip Helper ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hide_tip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show_tip)

    def unschedule(self):
        id_ = self.id
        self.id = None
        if id_:
            self.widget.after_cancel(id_)

    def show_tip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#2e2e2e",
            foreground="#e0e0e0",
            relief="solid",
            border=1,
            font=("Microsoft JhengHei", 9),
            padx=8,
            pady=6,
        )
        label.pack(ipadx=1)

    def hide_tip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


# --- Premium Dark Studio GUI Application ---
class ForzaStudioGUI:
    def __init__(self, root, preload_file=None):
        # Print Startup Diagnostic plugins status to captured stdout so it is saved in global_log_buffer
        if (
            HAS_LIBS
            and "EvaluatorFactory" in globals()
            and EvaluatorFactory is not None
        ):
            try:
                engines = list(EvaluatorFactory.get_available_evaluators())
                print(
                    "===================================================================="
                )
                print("     FH6 Painter - FH6 Livery Engine Startup Diagnostic")
                print(
                    "===================================================================="
                )
                print("\n[Diagnostic] Computational Engine Plugins Status:")
                for e in engines:
                    if e["available"]:
                        status_str = "[ENABLED]"
                    else:
                        if e["code"] == "GO_OPENCL":
                            status_str = "[DISABLED] (Missing binary at tools/bin/forza-painter-geometrize-go.exe)"
                        else:
                            status_str = f"[DISABLED] (Missing library, run: pip install {'numba' if e['code'] == 'NUMBA' else 'taichi'} to enable)"
                    print(
                        f" - {e['name']:<32} | Code: {e['code']:<12} | Status: {status_str}"
                    )
                print()
                print(
                    "===================================================================="
                )
                print()
            except Exception as ex:
                print(f"[Diagnostic Error] Failed to run engine check: {ex}")

        self.root = root
        self.root.title("FH6 Painter - Shape Generator & Importer")
        self.root.geometry("1216x863")
        self.root.minsize(1216, 863)

        # --- UI Color Palette ---
        self.bg_main = "#121212"  # Dark Background
        self.bg_card = "#1E1E1E"  # Panel / Card Background
        self.bg_input = "#151515"  # Input Field Background
        self.border_color = "#2A2A2A"  # Card Border
        self.fg_primary = "#FFFFFF"  # White Primary Text
        self.fg_secondary = "#A0A0A0"  # Gray Secondary Text

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
        self.preview_image_lock = threading.Lock()
        self.latest_canvas_array = None
        self.latest_progress = (0, 100, 0.0, 0.0)  # (current, total, speed, eta)
        self.need_preview_update = False
        self.enable_preview = True
        self.preview_image_id = None
        self.last_canvas_draw_time = 0.0

        self.active_thread = None
        self.is_generating = False
        self.cancel_generation_flag = False
        self.last_generated_image_path = None
        self.is_importing = False
        self.auto_load_json_path = None

        # Scan profiles
        self.profiles = self.scan_profiles()

        # Scan available GPU devices
        self.gpu_list = self.scan_gpus()

        # Load optimization settings
        self.load_optimization_settings()

        # Bind close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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
            self.log_to_console(
                "Welcome to FH6 Painter! Load an image or a geometry JSON file to begin.\n"
            )

        if not HAS_LIBS:
            self.log_to_console(f"WARNING: Missing dependencies: {IMPORT_ERROR}\n")
            self.log_to_console(
                "Please install required libraries: pip install pillow numpy numba\n"
            )
            messagebox.showerror(
                "Missing Dependencies",
                f"Required libraries were not found:\n{IMPORT_ERROR}\n\nPlease run:\npip install pillow numpy numba",
            )

    def scan_profiles(self):
        """Scans the 'settings' directory for available .ini configurations."""
        profiles = []
        settings_dir = os.path.join(get_project_root(), "settings")
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
                    profiles.append(
                        {
                            "filename": f,
                            "name": os.path.splitext(f)[0],
                            "path": path,
                            "desc": desc,
                        }
                    )
        # If empty, add a default profile stub
        if not profiles:
            profiles.append(
                {
                    "filename": "_default.ini",
                    "name": "_default",
                    "path": "",
                    "desc": "Default system generation profile",
                }
            )
        # Sort alphabetically first
        profiles.sort(key=lambda x: x["name"])
        # Move "c. balanced" profile to the front (index 0) so it's selected by default
        balanced_idx = -1
        for idx, p in enumerate(profiles):
            if "balanced" in p["name"].lower():
                balanced_idx = idx
                break
        if balanced_idx != -1:
            balanced_item = profiles.pop(balanced_idx)
            profiles.insert(0, balanced_item)
        elif len(profiles) > 0:
            default_idx = -1
            for idx, p in enumerate(profiles):
                if p["name"] == "_default":
                    default_idx = idx
                    break
            if default_idx != -1:
                default_item = profiles.pop(default_idx)
                profiles.insert(0, default_item)
        return profiles

    def scan_gpus(self):
        """偵測系統中的顯示卡列表 (支援 winreg 登錄檔、wmic 與 PowerShell 多重防禦機制)"""
        gpus = []

        # 定義排除關鍵字 (不區分大小寫)
        exclude_keywords = [
            "display adapter",
            "parsec",
            "remote",
            "virtual",
            "indirect",
            "mirror",
        ]

        def is_valid_gpu(name):
            if not name:
                return False
            name_lower = name.lower()
            return not any(kw in name_lower for kw in exclude_keywords)

        # 1. 優先採用 Python 原生 winreg 讀取登錄檔 (速度最快，免行程開銷，完全不受 wmic 棄用影響)
        try:
            import winreg

            path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        if subkey_name.isdigit():
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    gpu_name, _ = winreg.QueryValueEx(
                                        subkey, "DriverDesc"
                                    )
                                    if (
                                        gpu_name
                                        and gpu_name not in gpus
                                        and is_valid_gpu(gpu_name)
                                    ):
                                        gpus.append(gpu_name)
                                except Exception:
                                    pass
                    except Exception:
                        pass
        except Exception:
            pass

        # 2. 次要備援方案：wmic 指令 (以 stderr=DEVNULL 靜音)
        if not gpus:
            try:
                import subprocess

                out = subprocess.check_output(
                    "wmic path win32_VideoController get name",
                    shell=True,
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8", errors="ignore")
                lines = [line.strip() for line in out.split("\n") if line.strip()]
                if len(lines) > 1:
                    for l in lines[1:]:
                        if (
                            l
                            and "name" not in l.lower()
                            and l not in gpus
                            and is_valid_gpu(l)
                        ):
                            gpus.append(l)
            except Exception:
                pass

        # 3. 終極備援方案：PowerShell 原生 CimInstance 查詢
        if not gpus:
            try:
                import subprocess

                out = subprocess.check_output(
                    'powershell -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"',
                    shell=True,
                    stderr=subprocess.DEVNULL,
                ).decode("utf-8", errors="ignore")
                lines = [line.strip() for line in out.split("\n") if line.strip()]
                for l in lines:
                    if l and l not in gpus and is_valid_gpu(l):
                        gpus.append(l)
            except Exception:
                pass

        if not gpus:
            gpus = ["Default GPU (Device 0)"]
        return gpus

    def apply_styles(self):
        """Set up standard TTK style properties for modern flat design."""
        style = ttk.Style()
        style.theme_use("default")
        style.configure(".", background=self.bg_main, foreground=self.fg_primary)

        # Card settings
        style.configure(
            "Card.TFrame", background=self.bg_card, borderwidth=1, relief="flat"
        )

        # Combobox style
        style.configure(
            "TCombobox",
            fieldbackground=self.bg_input,
            background=self.color_btn_default,
            foreground=self.fg_primary,
            arrowcolor=self.fg_primary,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.bg_input)],
            foreground=[("readonly", self.fg_primary)],
        )

        # Label settings
        style.configure(
            "Title.TLabel",
            font=("Microsoft JhengHei", 12, "bold"),
            background=self.bg_card,
            foreground=self.fg_primary,
        )
        style.configure(
            "Text.TLabel",
            font=("Microsoft JhengHei", 9),
            background=self.bg_card,
            foreground=self.fg_secondary,
        )
        style.configure(
            "MetricVal.TLabel",
            font=("Consolas", 14, "bold"),
            background=self.bg_card,
            foreground=self.color_blue,
        )
        style.configure(
            "MetricLbl.TLabel",
            font=("Microsoft JhengHei", 8),
            background=self.bg_card,
            foreground=self.fg_secondary,
        )

        # Progressbar
        style.configure(
            "Custom.Horizontal.TProgressbar",
            thickness=10,
            background=self.color_green,
            troughcolor=self.bg_input,
            borderwidth=0,
        )

    def build_ui(self):
        """Build the responsive layout of the FH6 Painter GUI."""
        # Main layout frame
        main_container = tk.Frame(self.root, bg=self.bg_main)
        main_container.pack(fill="both", expand=True, padx=15, pady=10)

        # --- Top Header Bar ---
        header_frame = tk.Frame(main_container, bg=self.bg_main)
        header_frame.pack(fill="x", pady=(0, 10))

        title_label = tk.Label(
            header_frame,
            text="FH6 Painter",
            font=("Outfit", 18, "bold"),
            bg=self.bg_main,
            fg=self.color_green,
        )
        title_label.pack(side="left")

        subtitle_label = tk.Label(
            header_frame,
            text="  |  FH6 ONE-STOP LIVERY ENGINE",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=self.bg_main,
            fg=self.fg_secondary,
        )
        subtitle_label.pack(side="left", fill="y")

        self.status_lbl = tk.Label(
            header_frame,
            text="READY",
            font=("Consolas", 10, "bold"),
            bg=self.bg_card,
            fg="#888888",
            padx=10,
            pady=2,
            bd=1,
            relief="solid",
        )
        self.status_lbl.pack(side="right")

        self.btn_show_logs = tk.Button(
            header_frame,
            text="診斷主控台 / Show Logs",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=self.bg_card,
            fg=self.color_blue,
            activebackground=self.color_btn_default_hover,
            activeforeground=self.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=self.open_log_window,
        )
        self.btn_show_logs.pack(side="right", padx=(0, 10))

        self.btn_benchmark = tk.Button(
            header_frame,
            text="效能測試 / Benchmark",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=self.bg_card,
            fg=self.color_blue,
            activebackground=self.color_btn_default_hover,
            activeforeground=self.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=self.run_benchmark_gui,
        )
        self.btn_benchmark.pack(side="right", padx=(0, 10))

        self.btn_toggle_preview = tk.Button(
            header_frame,
            text="關閉預覽 / Disable Preview",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=self.bg_card,
            fg=self.color_green,
            activebackground=self.color_btn_default_hover,
            activeforeground=self.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=self.toggle_preview_state,
        )
        self.btn_toggle_preview.pack(side="right", padx=(0, 10))

        # --- Workspace Splitting (Left Control vs Right Preview) ---
        workspace = tk.Frame(main_container, bg=self.bg_main)
        workspace.pack(fill="both", expand=True)

        # Left Panel (Width ~ 480)
        left_panel = tk.Frame(workspace, bg=self.bg_main, width=480)
        left_panel.pack(side="left", fill="y", expand=False, padx=(0, 10))
        left_panel.pack_propagate(False)

        # Right Panel (Width ~ 680)
        right_panel = tk.Frame(workspace, bg=self.bg_main, width=680)
        right_panel.pack(side="right", fill="both", expand=True)
        right_panel.pack_propagate(False)

        # --- LEFT PANEL CARDS ---
        # Card 1: Input Source Configuration
        card_input = ttk.Frame(left_panel, style="Card.TFrame")
        card_input.pack(fill="x", pady=(0, 8), ipady=4)

        self.create_card_header(
            card_input,
            "1. INPUT SOURCE",
            "Select target image (PNG/JPG) or geometry JSON file",
        )

        input_body = tk.Frame(card_input, bg=self.bg_card)
        input_body.pack(fill="x", padx=15, pady=(5, 5))

        self.entry_file_path = tk.Entry(
            input_body,
            bg=self.bg_input,
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            font=("Microsoft JhengHei", 9),
            bd=0,
        )
        self.entry_file_path.pack(
            side="left", fill="x", expand=True, ipady=6, padx=(0, 5)
        )
        self.entry_file_path.bind("<KeyRelease>", lambda e: self.on_file_changed())

        btn_browse = tk.Button(
            input_body,
            text="Browse",
            font=("Microsoft JhengHei", 9, "bold"),
            bg=self.color_btn_default,
            fg=self.fg_primary,
            activebackground=self.color_btn_default_hover,
            activeforeground=self.fg_primary,
            bd=0,
            padx=12,
            command=self.browse_file,
        )
        btn_browse.pack(side="right", ipady=2)

        # Card 2: Livery Generation Parameters
        card_params = ttk.Frame(left_panel, style="Card.TFrame")
        card_params.pack(fill="x", pady=(0, 8), ipady=4)

        self.create_card_header(
            card_params,
            "2. GENERATOR SETTINGS",
            "Configure livery shape reconstruction thresholds",
        )

        params_body = tk.Frame(card_params, bg=self.bg_card)
        params_body.pack(fill="x", padx=15, pady=5)

        # Profile Dropdown
        tk.Label(
            params_body,
            text="Speed/Quality Profile:",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.combo_profile = ttk.Combobox(
            params_body,
            values=[p["name"] for p in self.profiles],
            state="readonly",
            width=35,
        )
        self.combo_profile.grid(row=0, column=1, sticky="we", pady=4, padx=(10, 0))
        self.combo_profile.current(0)
        self.combo_profile.bind("<<ComboboxSelected>>", self.on_profile_selected)

        # Profile Description Label
        self.lbl_profile_desc = tk.Label(
            params_body,
            text="...",
            font=("Microsoft JhengHei", 8, "italic"),
            bg=self.bg_card,
            fg="#888888",
            wraplength=380,
            justify="left",
        )
        self.lbl_profile_desc.grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(2, 8)
        )

        # Layer Limits (with game budget note)
        tk.Label(
            params_body,
            text="Max Layers/Shapes:",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        ).grid(row=2, column=0, sticky="w", pady=4)

        self.val_layers = tk.StringVar(value="2000")

        # 使用橫向子 Frame 把 Entry 和提早收斂 Checkbutton 完美組合在同一欄，避免任何重疊
        layers_container = tk.Frame(params_body, bg=self.bg_card)
        layers_container.grid(row=2, column=1, sticky="w", pady=4, padx=(10, 0))

        self.entry_layers = tk.Entry(
            layers_container,
            textvariable=self.val_layers,
            bg=self.bg_input,
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            font=("Consolas", 10),
            bd=0,
            width=12,
        )
        self.entry_layers.pack(side="left", ipady=3)

        self.var_early_conv = tk.BooleanVar(value=True)
        self.chk_early_conv = tk.Checkbutton(
            layers_container,
            text="啟用提早收斂 (Early Conv)",
            variable=self.var_early_conv,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.color_blue,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            padx=10,
        )
        self.chk_early_conv.pack(side="left")

        lbl_limits_tip = tk.Label(
            params_body,
            text="FH6 Game Limits: Bumper up to 1000 | Left/Right/Top up to 3000",
            font=("Microsoft JhengHei", 8),
            bg=self.bg_card,
            fg=self.color_blue,
        )
        lbl_limits_tip.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 8))

        # JIT Engine Plugin Dropdown
        tk.Label(
            params_body,
            text="JIT Engine Plugin:",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        ).grid(row=4, column=0, sticky="w", pady=4)

        if (
            HAS_LIBS
            and "EvaluatorFactory" in globals()
            and EvaluatorFactory is not None
        ):
            self.available_evaluators = EvaluatorFactory.get_available_evaluators()
        else:
            # Fallback mock setup if library not available (e.g. frozen PyInstaller build)
            go_binary_path = os.path.join(
                get_project_root(), "tools", "bin", "forza-painter-geometrize-go.exe"
            )
            has_go = os.path.exists(go_binary_path)
            self.available_evaluators = [
                {
                    "code": "NUMBA",
                    "name": "Numba JIT (CPU, Recommanded)",
                    "available": False,
                },
                {
                    "code": "TAICHI",
                    "name": "Taichi JIT (GPU, High-perf)",
                    "available": False,
                },
                {
                    "code": "GO_OPENCL",
                    "name": "Go-OpenCL (GPU, Fastest)",
                    "available": has_go,
                },
            ]
        evaluator_names = []
        for e in self.available_evaluators:
            if e["available"]:
                evaluator_names.append(e["name"])
            else:
                evaluator_names.append(f"{e['name']} (Unavailable)")

        self.combo_engine = ttk.Combobox(
            params_body, values=evaluator_names, state="readonly", width=35
        )
        self.combo_engine.grid(row=4, column=1, sticky="we", pady=4, padx=(10, 0))

        # Default select Numba if available, else first available
        default_idx = 0
        for idx, e in enumerate(self.available_evaluators):
            if e["code"] == "NUMBA" and e["available"]:
                default_idx = idx
                break
        self.combo_engine.current(default_idx)
        self.combo_engine.bind("<<ComboboxSelected>>", self.on_engine_selected)

        # Taichi 後端模式 (Vulkan, CUDA, OpenGL, CPU)
        self.lbl_taichi_arch = tk.Label(
            params_body,
            text="Taichi Arch GPU Mode:",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        )
        self.lbl_taichi_arch.grid(row=5, column=0, sticky="w", pady=4)

        # Container to place Combobox and Hybrid checkbox side-by-side perfectly
        self.taichi_arch_container = tk.Frame(params_body, bg=self.bg_card)
        self.taichi_arch_container.grid(
            row=5, column=1, sticky="we", pady=4, padx=(10, 0)
        )

        self.combo_taichi_arch = ttk.Combobox(
            self.taichi_arch_container,
            values=["Vulkan", "CUDA", "OpenGL", "CPU"],
            state="readonly",
            width=18,
        )
        self.combo_taichi_arch.pack(side="left", fill="x", expand=True)
        self.combo_taichi_arch.current(0)

        self.var_hybrid = tk.BooleanVar(value=True)
        self.chk_hybrid = tk.Checkbutton(
            self.taichi_arch_container,
            text="啟用混合模式 (Hybrid)",
            variable=self.var_hybrid,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.color_blue,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            padx=10,
        )
        self.chk_hybrid.pack(side="left")

        # Taichi 顯示卡選擇
        self.lbl_taichi_device = tk.Label(
            params_body,
            text="Taichi GPU Device:",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        )
        self.lbl_taichi_device.grid(row=6, column=0, sticky="w", pady=4)

        self.combo_taichi_device = ttk.Combobox(
            params_body,
            values=[f"({idx}) {gpu}" for idx, gpu in enumerate(self.gpu_list)],
            state="readonly",
            width=35,
        )
        self.combo_taichi_device.grid(
            row=6, column=1, sticky="we", pady=4, padx=(10, 0)
        )
        self.combo_taichi_device.current(0)

        # Advanced Overrides
        self.show_adv = tk.BooleanVar(value=False)
        self.chk_adv = tk.Checkbutton(
            params_body,
            text="Enable Advanced Sample Override (Use INI settings otherwise)",
            variable=self.show_adv,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.toggle_advanced_panel,
        )
        self.chk_adv.grid(row=7, column=0, columnspan=2, sticky="w", pady=4)

        self.adv_frame = tk.Frame(params_body, bg=self.bg_card)

        tk.Label(
            self.adv_frame,
            text="Candidates (Samples):",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.val_candidates = tk.StringVar(value="20000")
        self.entry_candidates = tk.Entry(
            self.adv_frame,
            textvariable=self.val_candidates,
            bg=self.bg_input,
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            font=("Consolas", 9),
            bd=0,
            width=12,
        )
        self.entry_candidates.grid(
            row=0, column=1, sticky="w", pady=4, padx=(10, 0), ipady=3
        )

        tk.Label(
            self.adv_frame,
            text="Hill-climb Steps:",
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.val_steps = tk.StringVar(value="200")
        self.entry_steps = tk.Entry(
            self.adv_frame,
            textvariable=self.val_steps,
            bg=self.bg_input,
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            font=("Consolas", 9),
            bd=0,
            width=12,
        )
        self.entry_steps.grid(
            row=1, column=1, sticky="w", pady=4, padx=(10, 0), ipady=3
        )

        # Trigger initial description print
        self.on_profile_selected(None)

        # Card 2.5: Advanced Optimization Algorithms
        self.card_opts = ttk.Frame(left_panel, style="Card.TFrame")
        self.card_opts.pack(fill="x", pady=(0, 8), ipady=4)

        self.create_card_header(
            self.card_opts,
            "2.5 ADVANCED OPTIMIZATIONS",
            "Toggle high-performance optimization algorithms",
        )

        opts_body = tk.Frame(self.card_opts, bg=self.bg_card)
        opts_body.pack(fill="x", padx=15, pady=5)

        # 設置兩欄平分寬度
        opts_body.columnconfigure(0, weight=1)
        opts_body.columnconfigure(1, weight=1)

        self.var_pyramid = tk.BooleanVar(
            value=self.opt_settings["image_pyramid"]["enabled"]
        )
        self.var_importance = tk.BooleanVar(
            value=self.opt_settings["importance_sampling"]["enabled"]
        )
        self.var_annealing = tk.BooleanVar(
            value=self.opt_settings["simulated_annealing"]["enabled"]
        )
        self.var_freeze = tk.BooleanVar(
            value=self.opt_settings["dynamic_freeze"]["enabled"]
        )
        self.var_weight = tk.BooleanVar(
            value=self.opt_settings["error_weighting"]["enabled"]
        )
        self.var_decay = tk.BooleanVar(
            value=self.opt_settings["decaying_shape"]["enabled"]
        )

        self.chk_pyramid = tk.Checkbutton(
            opts_body,
            text="漸進式像素採樣 (Progressive Sampling)",
            variable=self.var_pyramid,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.on_opt_changed,
        )
        self.chk_pyramid.grid(row=0, column=0, sticky="w", pady=3)

        self.chk_freeze = tk.Checkbutton(
            opts_body,
            text="動態凍結遮罩 (Dynamic Freeze)",
            variable=self.var_freeze,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.on_opt_changed,
        )
        self.chk_freeze.grid(row=0, column=1, sticky="w", pady=3)

        self.chk_importance = tk.Checkbutton(
            opts_body,
            text="錯誤驅動重點採樣 (Importance)",
            variable=self.var_importance,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.on_opt_changed,
        )
        self.chk_importance.grid(row=1, column=0, sticky="w", pady=3)

        self.chk_weight = tk.Checkbutton(
            opts_body,
            text="區域誤差加權 (Error Weighting)",
            variable=self.var_weight,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.on_opt_changed,
        )
        self.chk_weight.grid(row=1, column=1, sticky="w", pady=3)

        self.chk_annealing = tk.Checkbutton(
            opts_body,
            text="解析解最佳色彩 (Analytical Color)",
            variable=self.var_annealing,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.on_opt_changed,
        )
        self.chk_annealing.grid(row=2, column=0, sticky="w", pady=3)

        self.chk_decay = tk.Checkbutton(
            opts_body,
            text="衰減式形狀限縮 (Decaying Shape)",
            variable=self.var_decay,
            font=("Microsoft JhengHei", 9),
            bg=self.bg_card,
            fg=self.fg_secondary,
            selectcolor=self.bg_card,
            activebackground=self.bg_card,
            activeforeground=self.fg_primary,
            bd=0,
            command=self.on_opt_changed,
        )
        self.chk_decay.grid(row=2, column=1, sticky="w", pady=3)

        # Bind Tooltips for Step 2.5
        Tooltip(
            self.chk_pyramid,
            "【漸進式像素採樣】\n在生成前期（形狀較大時）跳過部分像素以大幅提速，隨進度逐漸恢復全像素精細評估。",
        )
        Tooltip(
            self.chk_freeze,
            "【動態凍結遮罩】\n自動鎖定已經完美匹配的像素區域，避開重複評估以大幅減少運算負擔。",
        )
        Tooltip(
            self.chk_importance,
            "【錯誤驅動重點採樣】\n依據殘餘誤差圖進行重點採樣，將隨機橢圓生成優先配置於高誤差區域。",
        )
        Tooltip(
            self.chk_weight,
            "【區域誤差加權】\n根據像素的空間特徵（如前景或邊緣）對誤差進行加權，提升邊緣清晰度。",
        )
        Tooltip(
            self.chk_annealing,
            "【解析解最佳色彩】\n在評估幾何時利用解析解直接算出最優顏色，使爬山收斂速度倍增，無需隨機模擬退火。",
        )
        Tooltip(
            self.chk_decay,
            "【衰減式形狀限縮】\n隨著貼圖數量增加，動態縮小橢圓最大半徑以避免破壞已有的微小細節。",
        )

        # --- RIGHT PANEL CARDS ---
        # Card 3: Action Panel (Double-Button Execution) - Moved to Right Panel Bottom
        card_actions = ttk.Frame(right_panel, style="Card.TFrame")
        card_actions.pack(side="bottom", fill="x", pady=(5, 0), ipady=4)

        self.create_card_header(
            card_actions,
            "3. WORKSPACE ACTIONS",
            "Launch shape generation or memory injection pipeline",
        )

        actions_body = tk.Frame(card_actions, bg=self.bg_card)
        actions_body.pack(fill="both", expand=True, padx=15, pady=8)

        # Start Generation Button (Green)
        self.btn_generate = tk.Button(
            actions_body,
            text="開始生成 JSON\nStart Generation",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=self.color_green,
            fg=self.fg_primary,
            activebackground=self.color_green_hover,
            activeforeground=self.fg_primary,
            bd=0,
            pady=10,
            command=self.start_generation,
        )
        self.btn_generate.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Inject to Game Button (Blue)
        self.btn_inject = tk.Button(
            actions_body,
            text="注入至遊戲\nImport to Game",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=self.color_blue,
            fg=self.fg_primary,
            activebackground=self.color_blue_hover,
            activeforeground=self.fg_primary,
            bd=0,
            pady=10,
            command=self.start_injection,
        )
        self.btn_inject.pack(side="right", fill="both", expand=True, padx=(8, 0))

        # Make sure buttons start in correct states
        self.on_file_changed()

        # Card 4: Fitment Preview Canvas
        card_preview = ttk.Frame(right_panel, style="Card.TFrame")
        card_preview.pack(side="top", fill="both", expand=True, pady=(0, 5), ipady=5)

        self.create_card_header(
            card_preview,
            "4. LIVE SHAPE FITTING WORKBENCH",
            "Real-time canvas visualization of Numba JIT geometry fitting",
        )

        preview_body = tk.Frame(card_preview, bg=self.bg_card)
        preview_body.pack(fill="both", expand=True, padx=15, pady=5)

        # Preview Canvas Container
        self.canvas_size = 380
        self.canvas_preview = tk.Canvas(
            preview_body,
            bg="#0E0E0E",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.border_color,
        )
        self.canvas_preview.pack(fill="both", expand=True, pady=5)

        # Bind resize event to dynamically redraw grid/image
        self.canvas_preview.bind("<Configure>", self.on_canvas_resize)

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
        self.lbl_metric_layer = ttk.Label(
            m1_card, text="0 / 0", style="MetricVal.TLabel"
        )
        self.lbl_metric_layer.pack()
        ttk.Label(m1_card, text="LAYER PROGRESS", style="MetricLbl.TLabel").pack()

        # Metric 2: Speed
        m2_card = tk.Frame(hud_frame, bg=self.bg_card)
        m2_card.grid(row=0, column=1, sticky="we")
        self.lbl_metric_speed = ttk.Label(
            m2_card, text="0.0 L/s", style="MetricVal.TLabel"
        )
        self.lbl_metric_speed.pack()
        ttk.Label(m2_card, text="GENERATION SPEED", style="MetricLbl.TLabel").pack()

        # Metric 3: ETA
        m3_card = tk.Frame(hud_frame, bg=self.bg_card)
        m3_card.grid(row=0, column=2, sticky="we")
        self.lbl_metric_eta = ttk.Label(m3_card, text="0s", style="MetricVal.TLabel")
        self.lbl_metric_eta.pack()
        self.lbl_metric_eta_header = ttk.Label(
            m3_card, text="ESTIMATED REMAINING", style="MetricLbl.TLabel"
        )
        self.lbl_metric_eta_header.pack()

        # Metric 4: Progress %
        m4_card = tk.Frame(hud_frame, bg=self.bg_card)
        m4_card.grid(row=0, column=3, sticky="we")
        self.lbl_metric_pct = ttk.Label(m4_card, text="0.0%", style="MetricVal.TLabel")
        self.lbl_metric_pct.pack()
        ttk.Label(m4_card, text="COMPLETION RATIO", style="MetricLbl.TLabel").pack()

        # Fluid progress bar
        self.progress_bar = ttk.Progressbar(
            preview_body,
            orient="horizontal",
            mode="determinate",
            style="Custom.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x", pady=(5, 5))

        # 初始化引擎下拉選單的連動狀態
        self.on_engine_selected(None)

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
            self.adv_frame.grid(row=8, column=0, columnspan=2, sticky="we", pady=(5, 0))
        else:
            self.adv_frame.grid_forget()

    def on_engine_selected(self, event):
        """依據選取的引擎動態切換 Taichi 專用參數的啟用狀態"""
        engine_idx = self.combo_engine.current()
        if 0 <= engine_idx < len(self.available_evaluators):
            engine = self.available_evaluators[engine_idx]
            if not engine["available"]:
                import sys

                ver_str = f"{sys.version_info.major}.{sys.version_info.minor}"
                if sys.version_info >= (3, 14) and engine["code"] == "TAICHI":
                    reason = f"在 Python {ver_str} 環境下，GPU 加速 (Taichi JIT) 已預設停用且不可選擇，因為 Taichi 官方尚未在 PyPI 發布相容於 Python 3.14 的 cp314 軟體套件。\n\n本專案已自動為您切換至效能極佳的 CPU 加速 (Numba JIT) 引擎！"
                else:
                    reason = f"計算引擎 '{engine['name']}' 在當前環境中不可用。系統已為您切換至 CPU 加速 (Numba JIT)。"
                messagebox.showwarning("計算引擎不可用 / Engine Unavailable", reason)

                # 自動恢復成 Numba (若可用) 或 Pure Python
                for idx, e in enumerate(self.available_evaluators):
                    if e["code"] == "NUMBA" and e["available"]:
                        self.combo_engine.current(idx)
                        break
                self.on_engine_selected(None)
                return

        engine_code = (
            self.available_evaluators[engine_idx]["code"]
            if 0 <= engine_idx < len(self.available_evaluators)
            else "NUMBA"
        )

        if engine_code == "TAICHI":
            # 顯示 Taichi 專屬元件
            self.lbl_taichi_arch.grid(row=5, column=0, sticky="w", pady=4)
            self.taichi_arch_container.grid(
                row=5, column=1, sticky="we", pady=4, padx=(10, 0)
            )
            self.lbl_taichi_device.grid(row=6, column=0, sticky="w", pady=4)
            self.combo_taichi_device.grid(
                row=6, column=1, sticky="we", pady=4, padx=(10, 0)
            )

            self.combo_taichi_arch.configure(state="readonly")
            self.combo_taichi_device.configure(state="readonly")
            self.chk_hybrid.configure(state="normal")
        else:
            # 隱藏 Taichi 專屬元件
            self.lbl_taichi_arch.grid_remove()
            self.taichi_arch_container.grid_remove()
            self.lbl_taichi_device.grid_remove()
            self.combo_taichi_device.grid_remove()

        # 當選擇 Go 引擎時，隱藏 2.5 的六個優化選項卡片而不只是停用它們
        if engine_code == "GO_OPENCL":
            self.card_opts.pack_forget()
        else:
            self.card_opts.pack(fill="x", pady=(0, 8), ipady=4)

    def draw_cyber_placeholder(self, text="STUDIO READY"):
        """Draws a clean, dark tech cyberpunk graphic when no active simulation is running."""
        self.preview_image_id = None
        self.canvas_preview.delete("all")

        canvas_w = self.canvas_preview.winfo_width()
        canvas_h = self.canvas_preview.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            canvas_w = 380
            canvas_h = 380

        # 保持正方形區域繪製 grid
        size = min(canvas_w, canvas_h)
        offset_x = (canvas_w - size) / 2
        offset_y = (canvas_h - size) / 2

        # Cyber grid lines within square region
        for i in range(10):
            gap = size / 10
            # Horizontal lines
            self.canvas_preview.create_line(
                offset_x,
                offset_y + i * gap,
                offset_x + size,
                offset_y + i * gap,
                fill="#151515",
                width=1,
            )
            # Vertical lines
            self.canvas_preview.create_line(
                offset_x + i * gap,
                offset_y,
                offset_x + i * gap,
                offset_y + size,
                fill="#151515",
                width=1,
            )

        # Circular HUD radar lines
        center_x = canvas_w / 2
        center_y = canvas_h / 2

        radar_radius = size * 0.4
        self.canvas_preview.create_oval(
            center_x - radar_radius,
            center_y - radar_radius,
            center_x + radar_radius,
            center_y + radar_radius,
            outline="#222222",
            width=1,
        )
        self.canvas_preview.create_oval(
            center_x - radar_radius * 0.67,
            center_y - radar_radius * 0.67,
            center_x + radar_radius * 0.67,
            center_y + radar_radius * 0.67,
            outline="#2A2A2A",
            width=1,
        )
        self.canvas_preview.create_oval(
            center_x - radar_radius * 0.27,
            center_y - radar_radius * 0.27,
            center_x + radar_radius * 0.27,
            center_y + radar_radius * 0.27,
            outline="#333333",
            width=1,
        )

        # Crosshair lines
        cross_len = radar_radius * 1.07
        self.canvas_preview.create_line(
            center_x - cross_len,
            center_y,
            center_x - 10,
            center_y,
            fill="#333333",
            width=1,
        )
        self.canvas_preview.create_line(
            center_x + 10,
            center_y,
            center_x + cross_len,
            center_y,
            fill="#333333",
            width=1,
        )
        self.canvas_preview.create_line(
            center_x,
            center_y - cross_len,
            center_x,
            center_y - 10,
            fill="#333333",
            width=1,
        )
        self.canvas_preview.create_line(
            center_x,
            center_y + 10,
            center_x,
            center_y + cross_len,
            fill="#333333",
            width=1,
        )

        # Text label in center
        self.canvas_preview.create_text(
            center_x,
            center_y,
            text=text,
            fill=self.fg_secondary,
            font=("Outfit", 10, "bold"),
        )
        self.canvas_preview.create_text(
            center_x,
            center_y + 25,
            text="LOAD INPUT DATA FILE",
            fill="#555555",
            font=("Microsoft JhengHei", 8),
        )

    def on_canvas_resize(self, event):
        """當預覽畫布大小改變時觸發重新整理"""
        if not self.enable_preview:
            # 如果預覽已關閉，重新繪製 PREVIEW DISABLED 畫面
            self.canvas_preview.delete("all")
            self.preview_image_id = None
            canvas_w = self.canvas_preview.winfo_width()
            canvas_h = self.canvas_preview.winfo_height()
            if canvas_w <= 1 or canvas_h <= 1:
                canvas_w = 380
                canvas_h = 380
            center_x = canvas_w / 2
            center_y = canvas_h / 2
            self.canvas_preview.create_text(
                center_x,
                center_y,
                text="PREVIEW DISABLED",
                fill="#555555",
                font=("Outfit", 12, "bold"),
            )
            self.canvas_preview.create_text(
                center_x,
                center_y + 25,
                text="Click 'Enable Preview' to restore visual fitting",
                fill="#444444",
                font=("Microsoft JhengHei", 8),
            )
        elif self.latest_canvas_array is not None:
            self.need_preview_update = True
        else:
            self.draw_cyber_placeholder()

    def log_to_console(self, text):
        """Prints a diagnostic log line into the standard terminal console."""
        if sys.stdout is not None:
            sys.stdout.write(text)
            sys.stdout.flush()

    def toggle_preview_state(self):
        """切換畫布預覽的開啟與關閉狀態"""
        self.enable_preview = not self.enable_preview
        if self.enable_preview:
            self.btn_toggle_preview.configure(
                text="關閉預覽 / Disable Preview", fg=self.color_green
            )
            self.log_to_console("[System] 預覽功能已開啟。\n")
            if self.latest_canvas_array is not None:
                self.need_preview_update = True
        else:
            self.btn_toggle_preview.configure(
                text="開啟預覽 / Enable Preview", fg=self.fg_secondary
            )
            self.log_to_console("[System] 預覽功能已關閉。\n")
            self.canvas_preview.delete("all")
            self.preview_image_id = None

            canvas_w = self.canvas_preview.winfo_width()
            canvas_h = self.canvas_preview.winfo_height()
            if canvas_w <= 1 or canvas_h <= 1:
                canvas_w = 380
                canvas_h = 380
            center_x = canvas_w / 2
            center_y = canvas_h / 2
            self.canvas_preview.create_text(
                center_x,
                center_y,
                text="PREVIEW DISABLED",
                fill="#555555",
                font=("Outfit", 12, "bold"),
            )
            self.canvas_preview.create_text(
                center_x,
                center_y + 25,
                text="Click 'Enable Preview' to restore visual fitting",
                fill="#444444",
                font=("Microsoft JhengHei", 8),
            )

    def open_log_window(self):
        """Opens a scrollable Traditional Chinese & English bilingual diagnostic console window showing all captured stdout/stderr logs."""
        log_win = tk.Toplevel(self.root)
        log_win.title("FH6 Painter - Diagnostic Log Console")
        log_win.geometry("820x560")
        log_win.configure(bg=self.bg_main)
        log_win.transient(self.root)

        hdr = tk.Frame(log_win, bg=self.bg_card)
        hdr.pack(fill="x", padx=10, pady=(10, 5), ipady=4)
        lbl = tk.Label(
            hdr,
            text="系統即時診斷主控台 / Real-time Diagnostic Log Console",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=self.bg_card,
            fg=self.color_blue,
        )
        lbl.pack(side="left", padx=10)

        btn_clear = tk.Button(
            hdr,
            text="清除日誌 / Clear Logs",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=self.bg_main,
            fg=self.fg_secondary,
            activebackground=self.color_btn_default_hover,
            activeforeground=self.fg_primary,
            bd=1,
            relief="solid",
            padx=12,
            command=lambda: self.clear_logs(txt_widget),
        )
        btn_clear.pack(side="right", padx=10)

        txt_widget = scrolledtext.ScrolledText(
            log_win,
            bg="#0A0A0A",
            fg="#00FF00",
            insertbackground="#00FF00",
            font=("Consolas", 9),
            bd=0,
            highlightthickness=1,
            highlightbackground=self.border_color,
        )
        txt_widget.pack(fill="both", expand=True, padx=10, pady=5)

        txt_widget.insert(tk.END, "".join(global_log_buffer))
        txt_widget.see(tk.END)
        txt_widget.configure(state="disabled")

        def update_log_view():
            if log_win.winfo_exists():
                txt_widget.configure(state="normal")
                curr_len = len(txt_widget.get("1.0", tk.END)) - 1
                full_log = "".join(global_log_buffer)
                if len(full_log) > curr_len:
                    txt_widget.insert(tk.END, full_log[curr_len:])
                    txt_widget.see(tk.END)
                txt_widget.configure(state="disabled")
                log_win.after(200, update_log_view)

        update_log_view()

    def clear_logs(self, txt_widget):
        global global_log_buffer
        global_log_buffer.clear()
        txt_widget.configure(state="normal")
        txt_widget.delete("1.0", tk.END)
        txt_widget.configure(state="disabled")

    def run_benchmark_gui(self):
        """Opens a modern dark-themed window and runs benchmark_taichi.py in a background thread, streaming stdout in real time."""
        bench_win = tk.Toplevel(self.root)
        bench_win.title("FH6 Painter - Performance Benchmark Suite")
        bench_win.geometry("900x600")
        bench_win.configure(bg=self.bg_main)
        bench_win.transient(self.root)

        hdr = tk.Frame(bench_win, bg=self.bg_card)
        hdr.pack(fill="x", padx=10, pady=(10, 5), ipady=4)

        lbl = tk.Label(
            hdr,
            text="🏆 性能基準測試主控台 / Performance Benchmark Console",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=self.bg_card,
            fg=self.color_green,
        )
        lbl.pack(side="left", padx=10)

        # Status indicator
        status_lbl = tk.Label(
            hdr,
            text="RUNNING TESTS",
            font=("Consolas", 9, "bold"),
            bg=self.bg_main,
            fg=self.color_blue,
            padx=10,
            pady=2,
            bd=1,
            relief="solid",
        )
        status_lbl.pack(side="right", padx=10)

        # ScrolledText for output
        txt_widget = scrolledtext.ScrolledText(
            bench_win,
            bg="#080808",
            fg=self.fg_primary,
            insertbackground=self.fg_primary,
            font=("Consolas", 9.5),
            bd=0,
            highlightthickness=1,
            highlightbackground=self.border_color,
        )
        txt_widget.pack(fill="both", expand=True, padx=10, pady=5)
        txt_widget.insert(tk.END, "Initializing benchmark pipeline...\n")
        txt_widget.see(tk.END)

        # Lock main GUI during benchmark execution
        self.status_lbl.configure(text="BENCHMARKING", fg=self.color_blue)
        self.lock_ui()

        def worker():
            import subprocess
            import sys

            script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "tools",
                "benchmark_taichi.py",
            )

            try:
                # Use sys.executable to run in unbuffered mode so stdout streams line-by-line
                process = subprocess.Popen(
                    [sys.executable, "-u", script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    cwd=os.path.dirname(os.path.abspath(__file__)),
                )

                for line in iter(process.stdout.readline, ""):
                    # Append output line-by-line to the text box
                    txt_widget.after(
                        0,
                        lambda l=line: (
                            txt_widget.configure(state="normal"),
                            txt_widget.insert(tk.END, l),
                            txt_widget.see(tk.END),
                            txt_widget.configure(state="disabled"),
                        ),
                    )

                process.stdout.close()
                return_code = process.wait()

                if return_code == 0:
                    status_text = "PASSED / SUCCESS"
                    status_color = self.color_green
                else:
                    status_text = "FAILED / REGRESSION WARNING"
                    status_color = "#D32F2F"

                txt_widget.after(
                    0, lambda: status_lbl.configure(text=status_text, fg=status_color)
                )
            except Exception as e:
                txt_widget.after(
                    0,
                    lambda err=e: (
                        txt_widget.configure(state="normal"),
                        txt_widget.insert(
                            tk.END, f"\n[Benchmark Execution Error] {err}\n"
                        ),
                        txt_widget.see(tk.END),
                        txt_widget.configure(state="disabled"),
                        status_lbl.configure(text="ERROR", fg="#D32F2F"),
                    ),
                )
            finally:
                # Always unlock main GUI after completion
                txt_widget.after(
                    0,
                    lambda: (
                        self.status_lbl.configure(text="READY", fg="#888888"),
                        self.unlock_ui(),
                    ),
                )

        # Launch the subprocess in a daemon thread so the GUI remains perfectly responsive!
        t = threading.Thread(target=worker, daemon=True)
        t.start()

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
                            if not line or line.startswith("#") or line.startswith(";"):
                                continue
                            if "=" in line:
                                key, val = line.split("=", 1)
                                key = key.strip()
                                val = val.strip()
                                if key == "randomSamples":
                                    self.val_candidates.set(val)
                                elif key == "mutatedSamples":
                                    self.val_steps.set(val)
                                elif key == "stopAt":
                                    self.val_layers.set(val)
                except Exception:
                    pass

    def browse_file(self):
        """Open file picker targeting images or JSONs."""
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[
                (
                    "Supported Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.json)",
                    "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.json",
                ),
                (
                    "Images (*.png;*.jpg;*.jpeg;*.bmp;*.webp)",
                    "*.png;*.jpg;*.jpeg;*.bmp;*.webp",
                ),
                ("Geometry JSON (*.json)", "*.json"),
                ("All files (*.*)", "*.*"),
            ],
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
            self.btn_generate.configure(
                state="normal",
                text="開始生成 JSON\nStart Generation",
                bg=self.color_green,
                activebackground=self.color_green_hover,
                fg=self.fg_primary,
                activeforeground=self.fg_primary,
                command=self.start_generation,
            )
            self.btn_inject.configure(
                state="disabled", bg=self.color_green_disabled, fg="#888888"
            )
            self.last_generated_image_path = path

            # Reset HUD to ready/ETA state
            if hasattr(self, "lbl_metric_eta_header"):
                self.lbl_metric_eta_header.configure(text="ESTIMATED REMAINING")
            if hasattr(self, "lbl_metric_eta"):
                self.lbl_metric_eta.configure(text="0s")

        # JSON pattern
        elif ext == ".json":
            # JSON Loaded: Enable Injection
            self.btn_inject.configure(
                state="normal", bg=self.color_blue, fg=self.fg_primary
            )

            # If we have a previously generated/loaded image path, keep "Generate Again" enabled!
            if getattr(self, "last_generated_image_path", None) and os.path.exists(
                self.last_generated_image_path
            ):
                self.btn_generate.configure(
                    state="normal",
                    text="再次生成 JSON\nGenerate Again",
                    bg=self.color_green,
                    activebackground=self.color_green_hover,
                    fg=self.fg_primary,
                    activeforeground=self.fg_primary,
                    command=self.start_generation,
                )
            else:
                self.btn_generate.configure(
                    state="disabled",
                    text="開始生成 JSON\nStart Generation",
                    bg=self.color_blue_disabled,
                    fg="#888888",
                )

            # --- Load JSON and render preview instantly ---
            if os.path.exists(path):
                import json

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    shapes = data.get("shapes", [])
                    if len(shapes) > 0:
                        # QoL 2: 自動更新 Max Layer 控制項的值以匹配 JSON 裡的圖層數 (扣除第0層背景)
                        num_layers = len(shapes) - 1
                        if num_layers > 0:
                            self.val_layers.set(str(num_layers))

                        header = shapes[0]
                        # Extract background dimensions and colors from header shape
                        h_data = header.get("data", [0.0, 0.0, 600.0, 600.0])
                        h_color = header.get("color", [128, 128, 128, 0])
                        width = int(h_data[2]) if len(h_data) >= 3 else 600
                        height = int(h_data[3]) if len(h_data) >= 4 else 600
                        avg_r, avg_g, avg_b = h_color[0], h_color[1], h_color[2]

                        # 為了獲得超高解析度的精緻預覽，將加載 JSON 重建畫布的解析度翻倍 (2.0 倍)
                        import copy

                        from tools.fh6_painter_generator import scale_shapes_list

                        render_scale = 2.0
                        width_high = int(width * render_scale)
                        height_high = int(height * render_scale)

                        shapes_copied = copy.deepcopy(shapes)
                        scale_shapes_list(shapes_copied, render_scale)

                        # Generate premium RGBA preview canvas array to support checkerboard preview
                        canvas = np.zeros(
                            (height_high, width_high, 4), dtype=np.float32
                        )
                        evaluator = EvaluatorFactory.create_evaluator(
                            "NUMBA",
                            np.zeros((height_high, width_high, 3), dtype=np.float32),
                            None,
                        )
                        evaluator.rebuild_canvas(
                            canvas, shapes_copied, avg_r, avg_g, avg_b
                        )
                        evaluator.cleanup()

                        # Lock and update share preview array for live workbench repainting
                        with self.preview_image_lock:
                            self.latest_canvas_array = canvas.copy()
                            self.need_preview_update = True
                except Exception as e:
                    self.log_to_console(f"\n[Instant Preview Loader Error] {e}\n")

        else:
            # Unidentified format
            self.btn_generate.configure(state="disabled", bg=self.bg_card, fg="#555555")
            self.btn_inject.configure(state="disabled", bg=self.bg_card, fg="#555555")

    def lock_ui(self):
        """Disables controls during background executions to maintain stability."""
        self.entry_file_path.configure(state="disabled")
        self.combo_profile.configure(state="disabled")
        self.combo_engine.configure(state="disabled")
        self.entry_layers.configure(state="disabled")
        self.entry_candidates.configure(state="disabled")
        self.entry_steps.configure(state="disabled")
        self.chk_adv.configure(state="disabled")
        self.chk_pyramid.configure(state="disabled")
        self.chk_importance.configure(state="disabled")
        self.chk_annealing.configure(state="disabled")
        self.chk_freeze.configure(state="disabled")
        self.chk_weight.configure(state="disabled")
        self.chk_decay.configure(state="disabled")
        self.btn_benchmark.configure(state="disabled")
        self.chk_hybrid.configure(state="disabled")

        self.btn_inject.configure(state="disabled")

        if self.is_generating:
            # During shape generation, btn_generate becomes "Stop Generation" button
            self.btn_generate.configure(
                state="normal",
                text="停止生成\nStop Generation",
                bg="#D32F2F",
                activebackground="#C62828",
                fg=self.fg_primary,
                activeforeground=self.fg_primary,
                command=self.stop_generation,
            )
        else:
            self.btn_generate.configure(state="disabled")

    def unlock_ui(self):
        """Enables UI elements once computing threads terminate."""
        self.entry_file_path.configure(state="normal")
        self.combo_profile.configure(state="readonly")
        self.combo_engine.configure(state="readonly")
        self.entry_layers.configure(state="normal")
        self.entry_candidates.configure(state="normal")
        self.entry_steps.configure(state="normal")
        self.chk_adv.configure(state="normal")
        self.chk_pyramid.configure(state="normal")
        self.chk_importance.configure(state="normal")
        self.chk_annealing.configure(state="normal")
        self.chk_freeze.configure(state="normal")
        self.chk_weight.configure(state="normal")
        self.chk_decay.configure(state="normal")
        self.btn_benchmark.configure(state="normal")
        self.on_engine_selected(None)

        # Restore btn_generate to "Generate Again" style
        self.btn_generate.configure(
            state="normal",
            text="再次生成 JSON\nGenerate Again",
            bg=self.color_green,
            activebackground=self.color_green_hover,
            fg=self.fg_primary,
            activeforeground=self.fg_primary,
            command=self.start_generation,
        )

        self.on_file_changed()

    # --- Thread-Safe Update Hook ---
    def poll_background_updates(self):
        """Cycles every 100ms in the main loop to repaint previews and handle metrics."""
        # 1. Update Canvas Preview from shared numpy variable
        # 始終讓預覽的更新頻率固定為 2Hz (500ms)，並在 enable_preview 開啟時才更新
        now_time = time.time()
        curr, total, _, _ = self.latest_progress
        is_finished = (curr == total) if self.is_generating else True

        # 當開啟預覽且需要更新時，檢查是否已間隔 500ms 或已經生成完成
        if self.need_preview_update and self.enable_preview:
            if (now_time - self.last_canvas_draw_time >= 0.50) or is_finished:
                with self.preview_image_lock:
                    arr = (
                        self.latest_canvas_array.copy()
                        if self.latest_canvas_array is not None
                        else None
                    )
                    self.need_preview_update = False
                self.last_canvas_draw_time = now_time

                if arr is not None:
                    try:
                        # Clip numpy array and convert float32 to uint8
                        arr_clipped = np.clip(arr, 0.0, 255.0).astype(np.uint8)

                        if arr.ndim == 3 and arr.shape[2] == 4:
                            # Extract RGB and Alpha
                            arr_rgb = arr_clipped[:, :, :3].astype(np.float32)
                            alpha = arr_clipped[:, :, 3].astype(np.float32) / 255.0
                            alpha = np.expand_dims(alpha, axis=2)  # Shape: (H, W, 1)

                            # 直接使用 UI 原生的深黑色背景色融為一體 (RGB: 14, 14, 14)，取消透明背景的灰白方格
                            bg_color = np.array([14.0, 14.0, 14.0], dtype=np.float32)
                            blended = (
                                arr_rgb * alpha + bg_color * (1.0 - alpha)
                            ).astype(np.uint8)
                            pil_img = Image.fromarray(blended)
                        else:
                            pil_img = Image.fromarray(arr_clipped)

                        # Resize to fit panel: use high-quality bilinear interpolation for static previews to eliminate aliasing, NEAREST for active generation performance
                        resample_mode = (
                            Image.Resampling.NEAREST
                            if self.is_generating
                            else Image.Resampling.BILINEAR
                        )

                        # 動態取得當前 Canvas 實體大小進行自適應縮放
                        canvas_w = self.canvas_preview.winfo_width()
                        canvas_h = self.canvas_preview.winfo_height()
                        if canvas_w <= 1 or canvas_h <= 1:
                            canvas_w = 380
                            canvas_h = 380

                        # 保持圖片長寬比例 (Aspect Ratio) 縮放，置中繪製於 Canvas
                        w, h = pil_img.size
                        scale = min(canvas_w / w, canvas_h / h)
                        new_w = max(1, int(w * scale))
                        new_h = max(1, int(h * scale))

                        pil_resized = pil_img.resize((new_w, new_h), resample_mode)
                        self.img_tk = ImageTk.PhotoImage(pil_resized)

                        # 增量更新點陣圖，消除 GDI 物件重複重建與 DWM 負載，置中於當前實際尺寸
                        center_x = canvas_w / 2
                        center_y = canvas_h / 2
                        if getattr(self, "preview_image_id", None) is None:
                            self.canvas_preview.delete("all")
                            self.preview_image_id = self.canvas_preview.create_image(
                                center_x,
                                center_y,
                                anchor="center",
                                image=self.img_tk,
                            )
                        else:
                            try:
                                self.canvas_preview.itemconfig(
                                    self.preview_image_id, image=self.img_tk
                                )
                                self.canvas_preview.coords(
                                    self.preview_image_id, center_x, center_y
                                )
                            except Exception:
                                self.canvas_preview.delete("all")
                                self.preview_image_id = (
                                    self.canvas_preview.create_image(
                                        center_x,
                                        center_y,
                                        anchor="center",
                                        image=self.img_tk,
                                    )
                                )
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

            self.unlock_ui()

            if self.is_generating:
                self.is_generating = False

                # Calculate and show final total duration
                elapsed_time = time.time() - getattr(
                    self, "generation_start_time", time.time()
                )
                if hasattr(self, "lbl_metric_eta_header"):
                    self.lbl_metric_eta_header.configure(text="TOTAL DURATION")
                if hasattr(self, "lbl_metric_eta"):
                    self.lbl_metric_eta.configure(text=f"{elapsed_time:.1f}s")

                if self.cancel_generation_flag:
                    self.status_lbl.configure(text="GEN STOPPED", fg="#FFA500")
                    self.log_to_console(
                        "\n[System] Shape generation process stopped by user.\n"
                    )
                else:
                    self.status_lbl.configure(text="GEN DONE", fg=self.color_green)
                    self.log_to_console(
                        "\n[System] Shape generation process completed.\n"
                    )

                # Check for automatic loading transition
                if self.auto_load_json_path and os.path.exists(
                    self.auto_load_json_path
                ):
                    self.log_to_console(
                        f"[UX Transition] Automatically loading generated JSON:\n-> {self.auto_load_json_path}\n"
                    )
                    self.entry_file_path.delete(0, tk.END)
                    self.entry_file_path.insert(
                        0, os.path.abspath(self.auto_load_json_path)
                    )
                    self.on_file_changed()
                    self.auto_load_json_path = None
                    # Visual pulse notification on inject button
                    self.btn_inject.focus_set()

            elif self.is_importing:
                self.is_importing = False
                result = getattr(self, "import_result", 1)
                if result == 0:
                    self.status_lbl.configure(text="INJECT DONE", fg=self.color_blue)
                    self.log_to_console(
                        "\n[System] Livery memory injection completed.\n"
                    )

                    # QoL 2: 導入完成後，彈出傳統中文對話框提示玩家導入了多少幾何圖層
                    imported_layers = self.val_layers.get()
                    messagebox.showinfo(
                        "導入成功 / Import Completed",
                        f"彩繪圖層注入成功！\n共成功導入 {imported_layers} 個幾何圖層至遊戲記憶體中。",
                    )
                else:
                    self.status_lbl.configure(text="INJECT ERROR", fg="#D32F2F")
                    self.log_to_console(
                        "\n[System] ERROR: Livery memory injection failed! Check log/terminal for details.\n"
                    )

                    # Redraw error visual state on GUI Radar
                    self.draw_cyber_placeholder(text="INJECT FAILED")

                    messagebox.showerror(
                        "導入失敗 / Import Failed",
                        "彩繪圖層注入失敗！無任何級別的候選者通過驗證。\n\n"
                        "請點擊右上角「診斷主控台 / Show Logs」查看詳細驗證失敗原因。\n\n"
                        "常見疑難排解：\n"
                        "1. 確保您已進入編輯器並建立了正確數量的圓形圖層。\n"
                        "2. ⚠️ 確保所有圓形圖層都已「解除群組 (Ungrouped)」。\n"
                        "3. 嘗試退出編輯器再重新進入，並重新建立圖層。\n"
                        "4. 如果 Log 顯示 LastError=5 (Access Denied)，請以「系統管理員身分」重啟本程式。",
                    )

        # Loop again in 100ms
        self.root.after(100, self.poll_background_updates)

    # --- Shape Generation Thread Launcher ---
    def start_generation(self):
        """Collects GUI configuration and starts the Numba shape generation loop on a worker thread."""
        if self.active_thread:
            return

        img_path = self.entry_file_path.get().strip()
        resume_path = None

        # If the input path is a JSON file but we have a stored image path, use the stored image path instead
        if img_path.lower().endswith(".json"):
            resume_path = img_path
            if getattr(self, "last_generated_image_path", None) and os.path.exists(
                self.last_generated_image_path
            ):
                img_path = self.last_generated_image_path
            else:
                messagebox.showerror(
                    "Error",
                    "Please select or generate from the original image first, then drop the JSON to resume.",
                )
                return
        else:
            # Store the current image path for future regeneration
            self.last_generated_image_path = img_path

        if not os.path.exists(img_path):
            messagebox.showerror("Error", f"Input file not found:\n{img_path}")
            return

        # Layers Limit Check
        try:
            layers = int(self.val_layers.get())
            if not (500 <= layers <= 3000):
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Error",
                "Invalid Layers Limit.\nPlease enter an integer between 500 and 3000.",
            )
            return

        # Determine output JSON name and create a structured output folder under the project root
        img_base = os.path.splitext(os.path.basename(img_path))[0]
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "output", img_base)
        output_json = os.path.join(output_dir, f"{img_base}.json")
        self.auto_load_json_path = output_json

        # Determine profile INI path
        profile_idx = self.combo_profile.current()
        profile_path = (
            self.profiles[profile_idx]["path"]
            if 0 <= profile_idx < len(self.profiles)
            else None
        )

        # 動態同步「提早收斂」在 GUI 中的啟用狀態至優化設定中
        if "early_convergence" not in self.opt_settings:
            self.opt_settings["early_convergence"] = {}
        self.opt_settings["early_convergence"]["enabled"] = self.var_early_conv.get()

        # Override values
        candidates = None
        steps = None
        if self.show_adv.get():
            try:
                candidates = int(self.val_candidates.get())
                steps = int(self.val_steps.get())
            except ValueError:
                messagebox.showerror(
                    "Error", "Advanced Overrides must be valid integers."
                )
                return

        # Pre-reset preview metrics
        self.latest_progress = (0, layers, 0.0, 0.0)
        self.lbl_metric_layer.configure(text=f"0 / {layers}")
        self.lbl_metric_speed.configure(text="0.0 L/s")
        if hasattr(self, "lbl_metric_eta_header"):
            self.lbl_metric_eta_header.configure(text="ESTIMATED REMAINING")
        self.lbl_metric_eta.configure(text="0s")
        self.lbl_metric_pct.configure(text="0.0%")
        self.progress_bar["value"] = 0

        # Lock GUI controls
        self.cancel_generation_flag = False
        self.is_generating = True
        self.generation_start_time = time.time()
        self.lock_ui()
        self.status_lbl.configure(text="GENERATING", fg=self.color_green)

        self.log_to_console(
            "[System] Triggering high-performance Python shape generator...\n"
        )

        # Progress callback hook
        self.last_cb_update_time = 0.0

        def generator_cb(curr, total, speed, eta, canvas_arr):
            if self.cancel_generation_flag:
                return "ABORT"

            # 更新節流：限制拷貝頻率大約在 20Hz (每 50ms 一次) 或是最後一幀時強制拷貝
            now_time = time.time()
            if (now_time - self.last_cb_update_time >= 0.05) or (curr == total):
                with self.preview_image_lock:
                    self.latest_canvas_array = canvas_arr.copy()
                    self.latest_progress = (curr, total, speed, eta)
                    self.need_preview_update = True
                self.last_cb_update_time = now_time

            # 若為 Taichi/Numba 引擎，釋放 GIL 給 Tkinter 執行緒以保持 GUI 響應與終端機刷新，避免線程飢餓與 DWM 阻塞
            if engine_code == "TAICHI":
                time.sleep(0.002)
            elif engine_code == "NUMBA":
                # Numba 模式也釋放極小時間 (1ms) 給 CPU 進行排程，減少 DWM 阻塞，徹底解決 AMD GPU VCE 佔用問題
                time.sleep(0.001)
            return True

        # Determine JIT Engine to use
        engine_idx = self.combo_engine.current()
        engine_code = (
            self.available_evaluators[engine_idx]["code"]
            if 0 <= engine_idx < len(self.available_evaluators)
            else "NUMBA"
        )

        # 獲取 Taichi GPU 與後端架構設定及混合模式
        taichi_arch = self.combo_taichi_arch.get()
        taichi_device_id = self.combo_taichi_device.current()
        use_pure_gpu = not self.var_hybrid.get()

        # Launch Worker Thread in Safe Wrapper to prevent silent thread deaths
        if engine_code == "GO_OPENCL":
            self.active_thread = threading.Thread(
                target=self.safe_run_go_generator,
                args=(
                    img_path,
                    output_json,
                    profile_path,
                    layers,
                ),
                kwargs={
                    "resume_path": resume_path,
                },
                daemon=True,
            )
        else:
            self.active_thread = threading.Thread(
                target=self.safe_run_generator,
                args=(
                    img_path,
                    output_json,
                    profile_path,
                    layers,
                    candidates,
                    steps,
                    generator_cb,
                    self.opt_settings,
                    engine_code,
                ),
                kwargs={
                    "taichi_arch": taichi_arch,
                    "taichi_device_id": taichi_device_id,
                    "use_pure_gpu": use_pure_gpu,
                    "resume_path": resume_path,
                },
                daemon=True,
            )
        self.active_thread.start()

    def safe_run_generator(self, *args, **kwargs):
        """安全的外掛執行緒外殼，捕獲生圖引擎內部可能引發的所有異常"""
        try:
            from tools.fh6_painter_generator import run_generator

            res = run_generator(*args, **kwargs)
            if res != 0:
                self.root.after(
                    0,
                    lambda: self.on_generation_failed(
                        "Generator returned a non-zero exit code. Please inspect terminal diagnostics."
                    ),
                )
        except Exception as e:
            # 捕獲所有異常 (包括 Taichi 編譯、硬體相容性、CUDA/OpenGL 崩潰)
            import traceback

            tb = traceback.format_exc()
            err_msg = f"{e}\n\n[Traceback]\n{tb}"
            self.root.after(0, lambda msg=err_msg: self.on_generation_failed(msg))

    def safe_run_go_generator(
        self, img_path, output_json, profile_path, layers, resume_path=None
    ):
        """安全地調用 Go-OpenCL 二進位生成器（已標準化重構為 Evaluator 插件）"""
        try:
            # 獲取當前選定的 GoOpenCLEvaluator 類別並實例化之
            engine_idx = self.combo_engine.current()
            evaluator_cls = self.available_evaluators[engine_idx]["class"]

            # 使用目前的 canvas 圖像尺寸來實例化，以維持 BaseEvaluator 行為
            arr_shape = (2, 2, 3)
            if self.latest_canvas_array is not None:
                arr_shape = self.latest_canvas_array.shape

            evaluator = evaluator_cls(
                self.latest_canvas_array
                if self.latest_canvas_array is not None
                else np.zeros(arr_shape, dtype=np.float32)
            )

            self.current_go_evaluator = evaluator

            def on_progress(curr, total, speed, eta):
                with self.preview_image_lock:
                    self.latest_progress = (curr, total, speed, eta)

            def on_log(msg):
                self.log_to_console(msg)

            def on_preview(arr):
                with self.preview_image_lock:
                    self.latest_canvas_array = arr
                    self.need_preview_update = True

            def on_success():
                pass

            def on_failed(msg):
                self.root.after(0, lambda: self.on_generation_failed(msg))

            evaluator.run_generator(
                img_path=img_path,
                output_json=output_json,
                profile_path=profile_path,
                layers=layers,
                resume_path=resume_path,
                progress_callback=on_progress,
                log_callback=on_log,
                preview_callback=on_preview,
                on_success_callback=on_success,
                on_failed_callback=on_failed,
            )

        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            err_msg = f"{e}\n\n[Traceback]\n{tb}"
            self.root.after(0, lambda msg=err_msg: self.on_generation_failed(msg))
        finally:
            self.current_go_evaluator = None

    def kill_generator_process(self):
        """結束執行中的 Go 執行檔行程"""
        proc = getattr(self, "generator_proc", None)
        if proc is not None:
            try:
                if sys.platform == "win32":
                    import subprocess

                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5,
                    )
                else:
                    proc.terminate()
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def on_generation_failed(self, error_message):
        """當生圖引擎異常崩潰時，優雅地通知使用者並完全重置 UI 狀態"""
        self.is_generating = False
        self.unlock_ui()
        self.status_lbl.configure(text="GEN ERROR", fg="#D32F2F")
        self.log_to_console(f"\n[ERROR] Generation thread failed:\n{error_message}\n")

        # 精緻高階錯誤提示視窗
        messagebox.showerror(
            "Livery Engine Error",
            f"An error occurred within the livery generation engine:\n\n{error_message}\n"
            "Suggestions:\n"
            "1. If using Taichi, try switching 'Taichi Arch GPU Mode' to 'Vulkan' (Recommended) or 'CPU'.\n"
            "2. Switch 'JIT Engine Plugin' to 'Numba JIT' for maximum baseline compatibility.",
        )

    def stop_generation(self):
        """Sets the cancellation flag to abort active shape generation."""
        if not self.is_generating or self.cancel_generation_flag:
            return

        self.cancel_generation_flag = True

        # 如果當前有運行中的 Go 評估器，調用它的 stop_generator 方法
        go_eval = getattr(self, "current_go_evaluator", None)
        if go_eval:
            go_eval.stop_generator()
        else:
            self.kill_generator_process()
        self.log_to_console(
            "\n[System] Stop requested. Gracefully finalizing current layer and saving progress...\n"
        )
        self.status_lbl.configure(text="STOPPING", fg="#FFA500")

        # Disable the stop button and show "Stopping..."
        self.btn_generate.configure(
            state="disabled", text="正在停止...\nStopping...", bg="#555555"
        )

    def run_importer_wrapper(self, **kwargs):
        """BACKGROUND THREAD: Invokes the actual run_importer logic and captures the return code."""
        self.import_result = None
        try:
            from tools.fh6_import_layer_table import run_importer

            self.import_result = run_importer(**kwargs)
        except Exception as e:
            self.import_result = 1
            print(
                f"Exception raised in background importer thread: {e}", file=sys.stderr
            )

    # --- Livery Memory Injection Thread Launcher ---
    def start_injection(self):
        """Launches Win32 memory writing thread on the active game process."""
        if self.active_thread:
            return

        json_path = self.entry_file_path.get().strip()
        if not os.path.exists(json_path):
            messagebox.showerror("Error", f"Geometry JSON file not found:\n{json_path}")
            return

        # QoL 2: 載入 JSON 路徑時，自動解析 JSON 檔內的實體圖層數作為注入基準，免除手動設定
        if json_path.lower().endswith(".json") and os.path.exists(json_path):
            try:
                import json

                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                shapes = data.get("shapes", [])
                if len(shapes) > 0:
                    layers = len(shapes) - 1
                    self.val_layers.set(str(layers))
                else:
                    layers = 3000
            except Exception:
                try:
                    layers = int(self.val_layers.get())
                except ValueError:
                    layers = 3000
        else:
            try:
                layers = int(self.val_layers.get())
            except ValueError:
                layers = 3000

        # Confirm user opens ungrouped shapes
        confirm = messagebox.askyesno(
            "遊戲記憶體注入確認 / Game Injection Confirmation",
            "在開始注入前，請務必確認以下事項：\n\n"
            "1. 《極限競速：地平線 6》遊戲主程式 (forzahorizon6.exe) 正在運行中。\n"
            "2. 您目前已進入遊戲內的「彩繪貼圖組編輯器 (Vinyl Group Editor)」。\n"
            "3. ⚠️【極度重要】您在編輯器內建立的圓形圖層數量，必須「恰好精準等於」下方數值，不能多也不能少：\n"
            f"   👉 必須剛好是：{layers} 個未編組的圓形圖層！\n"
            "   （若圖層數量有任何偏差，記憶體搜尋將會失敗，且可能導致注入崩潰！）\n\n"
            "您是否確定要繼續執行記憶體注入？",
        )

        if not confirm:
            return

        # Lock UI
        self.lock_ui()
        self.is_importing = True
        self.status_lbl.configure(text="INJECTING", fg=self.color_blue)

        self.log_to_console(
            "[System] Opening Win32 process handles for forzahorizon6.exe...\n"
        )

        # Clean HUD Radar Canvas to signal injection
        self.draw_cyber_placeholder(text="INJECTING GEOMETRY")
        self.progress_bar["value"] = 0
        self.lbl_metric_pct.configure(text="HUD LOCKED")

        # Initialize result before starting thread
        self.import_result = None

        # Launch Worker Thread
        self.active_thread = threading.Thread(
            target=self.run_importer_wrapper,
            kwargs={
                "json_path": json_path,
                "layers": layers,
                "dry_run": False,
                "reverse": False,
                "include_header": False,
                "no_cache": False,
                "scale_div": 63.0,
                "coord_scale": 1.0,
                "max_candidates": 200000,
            },
            daemon=True,
        )
        self.active_thread.start()

    def validate_geometry(self, geom_str, screen_w, screen_h):
        """解析並校驗視窗幾何字串，防止視窗小於 1216x863 或移出可見螢幕範圍之外"""
        import re

        pattern = r"^(\d+)x(\d+)([+-]\d+)?([+-]\d+)?$"
        match = re.match(pattern, geom_str.strip())

        default_w = 1216
        default_h = 863

        if not match:
            # 解析失敗，使用預設值置中
            x = max(0, (screen_w - default_w) // 2)
            y = max(0, (screen_h - default_h) // 2)
            return f"{default_w}x{default_h}+{x}+{y}"

        w = int(match.group(1))
        h = int(match.group(2))
        x_str = match.group(3)
        y_str = match.group(4)

        # 確保大小始終不小於 1216x863
        if w < default_w:
            w = default_w
        if h < default_h:
            h = default_h

        if x_str is None or y_str is None:
            # 沒有位置資訊，則居中
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)
            return f"{w}x{h}+{x}+{y}"

        x = int(x_str)
        y = int(y_str)

        # 螢幕邊界安全檢查防護：
        # 1. 標題列頂部不可移出螢幕上方 (y < 0)
        # 2. 視窗頂部不能低於螢幕底部的 100 像素以內 (y > screen_h - 100)
        # 3. 視窗右邊不能小於左邊 100 像素 (x + w < 100)
        # 4. 視窗左邊不能大於螢幕右邊的 100 像素以內 (x > screen_w - 100)
        # 如果不符合安全條件，則強制將其置中。
        if y < 0 or y > screen_h - 100 or x + w < 100 or x > screen_w - 100:
            x = max(0, (screen_w - w) // 2)
            y = max(0, (screen_h - h) // 2)

        x_part = f"+{x}" if x >= 0 else str(x)
        y_part = f"+{y}" if y >= 0 else str(y)
        return f"{w}x{h}{x_part}{y_part}"

    def load_optimization_settings(self):
        """載入或初始化優化設定 JSON 檔"""
        if not getattr(self, "settings_path", None):
            self.settings_path = os.path.join(
                get_project_root(), "optimization_settings.json"
            )
        default_settings = {
            "window_geometry": "1216x863",
            "image_pyramid": {"enabled": False, "fine_phase_layer": 500},
            "importance_sampling": {"enabled": False, "update_interval": 10},
            "simulated_annealing": {
                "enabled": False,
                "initial_temp": 10.0,
                "cooling_rate": 0.95,
            },
            "dynamic_freeze": {
                "enabled": False,
                "update_interval": 100,
                "error_threshold": 3,
            },
            "error_weighting": {"enabled": False, "update_interval": 100},
            "decaying_shape": {"enabled": False, "min_max_r": 5.0},
            "uncovered_bias": {"enabled": True, "bias": 5.0},
            "boundary_weighting": {"enabled": True, "bias": 3.0},
        }

        if os.path.exists(self.settings_path):
            try:
                import json

                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.opt_settings = json.load(f)
                # 確保所有必要鍵都存在
                for k, v in default_settings.items():
                    if k not in self.opt_settings:
                        self.opt_settings[k] = v
                    elif isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            if sub_k not in self.opt_settings[k]:
                                self.opt_settings[k][sub_k] = sub_v
            except Exception as e:
                self.log_to_console(
                    f"[Settings] 讀取優化設定失敗: {e}，正在重建設定檔並恢復預設值。\n"
                )
                self.opt_settings = default_settings
                self.save_optimization_settings()
        else:
            self.opt_settings = default_settings
            self.save_optimization_settings()

        # 套用儲存的視窗幾何尺寸與位置
        geom = self.opt_settings.get("window_geometry", "1216x863")
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            validated_geom = self.validate_geometry(geom, screen_w, screen_h)
            self.root.geometry(validated_geom)
        except Exception as e:
            self.log_to_console(
                f"[Settings] 套用視窗幾何失敗: {e}，回退到 1216x863 置中。\n"
            )
            try:
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()
                x = max(0, (screen_w - 1216) // 2)
                y = max(0, (screen_h - 863) // 2)
                self.root.geometry(f"1216x863+{x}+{y}")
            except Exception:
                self.root.geometry("1216x863")

    def save_optimization_settings(self):
        """保存優化設定到 JSON 檔"""
        try:
            import json

            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.opt_settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_to_console(f"[Settings] 儲存優化設定失敗: {e}\n")

    def on_opt_changed(self):
        """當優化設定 Checkbox 被點擊時，更新並保存設定"""
        self.opt_settings["image_pyramid"]["enabled"] = self.var_pyramid.get()
        self.opt_settings["importance_sampling"]["enabled"] = self.var_importance.get()
        self.opt_settings["simulated_annealing"]["enabled"] = self.var_annealing.get()
        self.opt_settings["dynamic_freeze"]["enabled"] = self.var_freeze.get()
        self.opt_settings["error_weighting"]["enabled"] = self.var_weight.get()
        self.opt_settings["decaying_shape"]["enabled"] = self.var_decay.get()
        self.save_optimization_settings()
        self.log_to_console("[Settings] 已更新優化設定至 JSON 檔\n")

    def on_close(self):
        """視窗關閉時的攔截處理：儲存當前視窗幾何尺寸與六個優化項的選取狀況"""
        try:
            self.opt_settings["window_geometry"] = self.root.geometry()
            self.opt_settings["image_pyramid"]["enabled"] = self.var_pyramid.get()
            self.opt_settings["importance_sampling"]["enabled"] = (
                self.var_importance.get()
            )
            self.opt_settings["simulated_annealing"]["enabled"] = (
                self.var_annealing.get()
            )
            self.opt_settings["dynamic_freeze"]["enabled"] = self.var_freeze.get()
            self.opt_settings["error_weighting"]["enabled"] = self.var_weight.get()
            self.opt_settings["decaying_shape"]["enabled"] = self.var_decay.get()
            self.save_optimization_settings()
        except Exception:
            pass
        self.root.destroy()


# --- Main Entry Script ---
def main():
    preload = None
    if len(sys.argv) > 1:
        preload = sys.argv[1]

    root = tk.Tk()
    ForzaStudioGUI(root, preload_file=preload)
    root.mainloop()


if __name__ == "__main__":
    main()
