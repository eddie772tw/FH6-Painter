import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import windnd
except ImportError:
    windnd = None

sys.path.append(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
)
try:
    import numpy as np
    from PIL import Image, ImageTk

    from evaluators import EvaluatorFactory

    HAS_LIBS = True
except ImportError as e:
    HAS_LIBS = False
    IMPORT_ERROR = str(e)

from gui.canvas_roi import CanvasROIMixin
from gui.components.actions_card import ActionsCard
from gui.components.generator_card import GeneratorSettingsCard
from gui.components.header import HeaderBar
from gui.components.input_card import InputSourceCard
from gui.components.optimizations_card import OptimizationsCard
from gui.components.preview_card import PreviewWorkbenchCard
from gui.components.roi_card import RegionPaintingCard
from gui.dialogs import DialogsMixin
from gui.polling import PollingMixin
from gui.settings import SettingsMixin
from gui.state import StateMixin
from gui.timeline import TimelineMixin
from gui.utils import scan_gpus, scan_profiles, setup_logging
from gui.workers import WorkersMixin


class ForzaStudioGUI(
    StateMixin,
    PollingMixin,
    TimelineMixin,
    CanvasROIMixin,
    WorkersMixin,
    SettingsMixin,
    DialogsMixin,
):
    def __init__(self, root, preload_file=None):
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
                print(
                    "\n====================================================================\n"
                )
            except Exception as ex:
                print(f"[Diagnostic Error] Failed to run engine check: {ex}")

        self.root = root
        self.root.title("FH6 Painter - Shape Generator & Importer")
        self.root.geometry("1216x863")
        self.root.minsize(1216, 863)

        self.bg_main = "#121212"
        self.bg_card = "#1E1E1E"
        self.bg_input = "#151515"
        self.border_color = "#2A2A2A"
        self.fg_primary = "#FFFFFF"
        self.fg_secondary = "#A0A0A0"

        self.color_green = "#4CAF50"
        self.color_green_hover = "#45a049"
        self.color_green_disabled = "#1E3822"

        self.color_blue = "#2196F3"
        self.color_blue_hover = "#0b7dda"
        self.color_blue_disabled = "#132D42"

        self.color_btn_default = "#2C2C2C"
        self.color_btn_default_hover = "#3A3A3A"

        self.root.configure(bg=self.bg_main)

        self.preview_image_lock = threading.Lock()
        self.latest_canvas_array = None
        self.latest_progress = (0, 100, 0.0, 0.0)
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
        self.has_completed_generation = False

        self.profiles = scan_profiles()
        self.gpu_list = scan_gpus()

        if (
            HAS_LIBS
            and "EvaluatorFactory" in globals()
            and EvaluatorFactory is not None
        ):
            self.available_evaluators = EvaluatorFactory.get_available_evaluators()
        else:
            from gui.utils import get_project_root

            go_binary_path = os.path.join(
                get_project_root(), "tools", "bin", "forza-painter-geometrize-go.exe"
            )
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
                    "available": os.path.exists(go_binary_path),
                },
            ]

        self.load_optimization_settings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.apply_styles()
        self.build_ui()

        self.root.after(100, self.poll_background_updates)

        if windnd:
            if hasattr(windnd, "hook_dropfiles"):
                windnd.hook_dropfiles(self.root, self.on_file_drop)
            elif hasattr(windnd, "hook_drop"):
                windnd.hook_drop(self.root, self.on_file_drop)

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

    def apply_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(".", background=self.bg_main, foreground=self.fg_primary)

        style.configure(
            "Card.TFrame", background=self.bg_card, borderwidth=1, relief="flat"
        )
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

        style.configure(
            "Custom.Horizontal.TProgressbar",
            thickness=10,
            background=self.color_green,
            troughcolor=self.bg_input,
            borderwidth=0,
        )

    def build_ui(self):
        main_container = tk.Frame(self.root, bg=self.bg_main)
        main_container.pack(fill="both", expand=True, padx=15, pady=10)

        # Header
        self.header = HeaderBar(main_container, app=self)
        self.header.pack(fill="x", pady=(0, 10))

        workspace = tk.Frame(main_container, bg=self.bg_main)
        workspace.pack(fill="both", expand=True)

        left_panel = tk.Frame(workspace, bg=self.bg_main, width=480)
        left_panel.pack(side="left", fill="y", expand=False, padx=(0, 10))
        left_panel.pack_propagate(False)

        right_panel = tk.Frame(workspace, bg=self.bg_main, width=680)
        right_panel.pack(side="right", fill="both", expand=True)
        right_panel.pack_propagate(False)

        # Left Panel Cards
        self.input_card = InputSourceCard(left_panel, app=self)
        self.input_card.pack(fill="x", pady=(0, 8), ipady=4)

        self.generator_card = GeneratorSettingsCard(left_panel, app=self)
        self.generator_card.pack(fill="x", pady=(0, 8), ipady=4)

        self.opts_card = OptimizationsCard(left_panel, app=self)
        self.opts_card.pack(fill="x", pady=(0, 8), ipady=4)

        self.roi_card = RegionPaintingCard(left_panel, app=self)
        self.roi_card.pack(fill="x", pady=(0, 8), ipady=4)

        # Right Panel Cards
        self.actions_card = ActionsCard(right_panel, app=self)
        self.actions_card.pack(side="bottom", fill="x", pady=(5, 0), ipady=4)

        self.preview_workbench = PreviewWorkbenchCard(right_panel, app=self)
        self.preview_workbench.pack(
            side="top", fill="both", expand=True, pady=(0, 5), ipady=5
        )

        from gui.components.base import draw_cyber_placeholder

        draw_cyber_placeholder(self)

        # Bind events
        self.on_engine_selected(None)
        self.on_file_changed()

        # Canvas ROI hooks
        self.canvas_preview.bind("<Configure>", self.on_canvas_resize)
        self.canvas_preview.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas_preview.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas_preview.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas_preview.bind("<Button-3>", self.on_canvas_right_click)

        # Timeline hooks
        self.progress_bar.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.available_checkpoints = {}
        self.selection_start_x = 0
        self.selection_start_y = 0
        self.selection_rect_id = None
        self.selection_roi = None
        self.render_meta = None

    def log_to_console(self, text):
        if sys.stdout is not None:
            sys.stdout.write(text)
            sys.stdout.flush()

    # --- Property Facades for backwards compatibility with Mixins and Tests ---
    @property
    def entry_file_path(self):
        return self.input_card.entry_file_path

    @property
    def status_lbl(self):
        return self.header.status_lbl

    @property
    def combo_profile(self):
        return self.generator_card.combo_profile

    @property
    def combo_engine(self):
        return self.generator_card.combo_engine

    @property
    def combo_taichi_arch(self):
        return self.generator_card.combo_taichi_arch

    @property
    def combo_taichi_device(self):
        return self.generator_card.combo_taichi_device

    @property
    def val_layers(self):
        return self.generator_card.val_layers

    @property
    def entry_layers(self):
        return self.generator_card.entry_layers

    @property
    def val_candidates(self):
        return self.generator_card.val_candidates

    @property
    def entry_candidates(self):
        return self.generator_card.entry_candidates

    @property
    def val_steps(self):
        return self.generator_card.val_steps

    @property
    def entry_steps(self):
        return self.generator_card.entry_steps

    @property
    def show_adv(self):
        return self.generator_card.show_adv

    @property
    def var_hybrid(self):
        return self.generator_card.var_hybrid

    @property
    def var_early_conv(self):
        return self.generator_card.var_early_conv

    @property
    def card_opts(self):
        return self.opts_card

    @property
    def lbl_taichi_arch(self):
        return self.generator_card.lbl_taichi_arch

    @property
    def taichi_arch_container(self):
        return self.generator_card.taichi_arch_container

    @property
    def lbl_taichi_device(self):
        return self.generator_card.lbl_taichi_device

    @property
    def var_pyramid(self):
        return self.opts_card.var_pyramid

    @property
    def var_importance(self):
        return self.opts_card.var_importance

    @property
    def var_annealing(self):
        return self.opts_card.var_annealing

    @property
    def var_freeze(self):
        return self.opts_card.var_freeze

    @property
    def var_weight(self):
        return self.opts_card.var_weight

    @property
    def var_decay(self):
        return self.opts_card.var_decay

    @property
    def chk_pyramid(self):
        return self.opts_card.chk_pyramid

    @property
    def chk_importance(self):
        return self.opts_card.chk_importance

    @property
    def chk_annealing(self):
        return self.opts_card.chk_annealing

    @property
    def chk_freeze(self):
        return self.opts_card.chk_freeze

    @property
    def chk_weight(self):
        return self.opts_card.chk_weight

    @property
    def chk_decay(self):
        return self.opts_card.chk_decay

    @property
    def var_roi_enabled(self):
        return self.roi_card.var_roi_enabled

    @property
    def var_roi_shape(self):
        return self.roi_card.var_roi_shape

    @property
    def val_rewind_layer(self):
        return self.roi_card.val_rewind_layer

    @property
    def lbl_roi_range(self):
        return self.roi_card.lbl_roi_range

    @property
    def lbl_roi_status(self):
        return self.roi_card.lbl_roi_status

    @property
    def lbl_rewind_hint(self):
        return self.roi_card.lbl_rewind_hint

    @property
    def btn_generate(self):
        return self.actions_card.btn_generate

    @property
    def btn_inject(self):
        return self.actions_card.btn_inject

    @property
    def canvas_preview(self):
        return self.preview_workbench.canvas_preview

    @property
    def progress_bar(self):
        return self.preview_workbench.progress_bar

    @property
    def timeline_canvas(self):
        return self.preview_workbench.timeline_canvas

    @property
    def lbl_metric_layer(self):
        return self.preview_workbench.lbl_metric_layer

    @property
    def lbl_metric_speed(self):
        return self.preview_workbench.lbl_metric_speed

    @property
    def lbl_metric_eta(self):
        return self.preview_workbench.lbl_metric_eta

    @property
    def lbl_metric_eta_header(self):
        return self.preview_workbench.lbl_metric_eta_header

    @property
    def lbl_metric_pct(self):
        return self.preview_workbench.lbl_metric_pct


def main():
    setup_logging()
    preload = None
    if len(sys.argv) > 1:
        preload = sys.argv[1]

    root = tk.Tk()
    ForzaStudioGUI(root, preload_file=preload)
    root.mainloop()


if __name__ == "__main__":
    main()
