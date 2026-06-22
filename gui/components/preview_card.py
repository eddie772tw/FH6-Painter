import tkinter as tk
from tkinter import ttk

from gui.components.base import create_card_header, draw_cyber_placeholder


class PreviewWorkbenchCard(ttk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, style="Card.TFrame", *args, **kwargs)
        self.app = app

        create_card_header(
            self,
            "4. LIVE SHAPE FITTING WORKBENCH",
            "Real-time canvas visualization of Numba JIT geometry fitting",
            app,
        )

        preview_body = tk.Frame(self, bg=app.bg_card)
        preview_body.pack(fill="both", expand=True, padx=15, pady=5)

        # Preview Canvas Container
        self.canvas_size = 380
        self.canvas_preview = tk.Canvas(
            preview_body,
            bg="#0E0E0E",
            bd=0,
            highlightthickness=1,
            highlightbackground=app.border_color,
        )
        self.canvas_preview.pack(fill="both", expand=True, pady=5)

        # Draw placeholder cyber graphics on start
        # (Moved to app.py after component instantiation to avoid AttributeError)

        # Live Metrics HUD (4 Slots)
        hud_frame = tk.Frame(preview_body, bg=app.bg_card)
        hud_frame.pack(fill="x", pady=(5, 5))

        # Column configuration
        for i in range(4):
            hud_frame.columnconfigure(i, weight=1)

        # Metric 1: Layer
        m1_card = tk.Frame(hud_frame, bg=app.bg_card)
        m1_card.grid(row=0, column=0, sticky="we")
        self.lbl_metric_layer = ttk.Label(
            m1_card, text="0 / 0", style="MetricVal.TLabel"
        )
        self.lbl_metric_layer.pack()
        ttk.Label(m1_card, text="LAYER PROGRESS", style="MetricLbl.TLabel").pack()

        # Metric 2: Speed
        m2_card = tk.Frame(hud_frame, bg=app.bg_card)
        m2_card.grid(row=0, column=1, sticky="we")
        self.lbl_metric_speed = ttk.Label(
            m2_card, text="0.0 L/s", style="MetricVal.TLabel"
        )
        self.lbl_metric_speed.pack()
        ttk.Label(m2_card, text="GENERATION SPEED", style="MetricLbl.TLabel").pack()

        # Metric 3: ETA
        m3_card = tk.Frame(hud_frame, bg=app.bg_card)
        m3_card.grid(row=0, column=2, sticky="we")
        self.lbl_metric_eta = ttk.Label(m3_card, text="0s", style="MetricVal.TLabel")
        self.lbl_metric_eta.pack()
        self.lbl_metric_eta_header = ttk.Label(
            m3_card, text="ESTIMATED REMAINING", style="MetricLbl.TLabel"
        )
        self.lbl_metric_eta_header.pack()

        # Metric 4: Progress %
        m4_card = tk.Frame(hud_frame, bg=app.bg_card)
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
        self.progress_bar.pack(fill="x", pady=(5, 0))

        # Timeline Canvas for Checkpoints
        self.timeline_canvas = tk.Canvas(
            preview_body, height=12, bg=app.bg_card, highlightthickness=0
        )
        self.timeline_canvas.pack(fill="x", pady=(0, 5))
