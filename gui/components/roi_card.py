import tkinter as tk
from tkinter import ttk

from gui.components.base import create_card_header


class RegionPaintingCard(ttk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, style="Card.TFrame", *args, **kwargs)
        self.app = app

        create_card_header(
            self,
            "2.8 REGION PAINTING",
            "Restrict generation to a selected canvas region",
            app,
        )

        roi_body = tk.Frame(self, bg=app.bg_card)
        roi_body.pack(fill="x", padx=15, pady=5)
        roi_body.columnconfigure(1, weight=1)

        # Row 0: Enable/Disable toggle
        tk.Label(
            roi_body,
            text="區域繪製：",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=0, column=0, sticky="w", pady=3)

        roi_toggle_frame = tk.Frame(roi_body, bg=app.bg_card)
        roi_toggle_frame.grid(row=0, column=1, sticky="w", pady=3, padx=(10, 0))

        self.var_roi_enabled = tk.BooleanVar(value=True)
        self.chk_roi_enabled = tk.Checkbutton(
            roi_toggle_frame,
            text="",
            variable=self.var_roi_enabled,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_roi_toggle_changed,
        )
        self.chk_roi_enabled.pack(side="left")

        self.lbl_roi_status = tk.Label(
            roi_toggle_frame,
            text="等待首次生成完成",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg="#888888",
        )
        self.lbl_roi_status.pack(side="left", padx=(2, 0))

        # Row 1: Shape mode selector
        tk.Label(
            roi_body,
            text="框選模式：",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=1, column=0, sticky="w", pady=3)

        shape_mode_frame = tk.Frame(roi_body, bg=app.bg_card)
        shape_mode_frame.grid(row=1, column=1, sticky="w", pady=3, padx=(10, 0))

        self.var_roi_shape = tk.StringVar(value="rectangle")
        self.rb_rect = tk.Radiobutton(
            shape_mode_frame,
            text="矩形 (Rectangle)",
            variable=self.var_roi_shape,
            value="rectangle",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_roi_shape_changed,
        )
        self.rb_rect.pack(side="left")

        self.rb_ellipse = tk.Radiobutton(
            shape_mode_frame,
            text="橢圓 (Ellipse)",
            variable=self.var_roi_shape,
            value="ellipse",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_roi_shape_changed,
        )
        self.rb_ellipse.pack(side="left", padx=(10, 0))

        # Row 1.5: Minimal Require Layers
        tk.Label(
            roi_body,
            text="最小輪廓層數：",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=2, column=0, sticky="w", pady=3)

        min_layers_frame = tk.Frame(roi_body, bg=app.bg_card)
        min_layers_frame.grid(row=2, column=1, sticky="w", pady=3, padx=(10, 0))

        self.var_roi_min_layers = tk.StringVar(value="500")
        self.entry_roi_min_layers = tk.Entry(
            min_layers_frame,
            textvariable=self.var_roi_min_layers,
            width=8,
            font=("Consolas", 10),
            bg=app.bg_window,
            fg=app.fg_primary,
            insertbackground=app.fg_primary,
            relief="flat",
        )
        self.entry_roi_min_layers.pack(side="left")

        tk.Label(
            min_layers_frame,
            text="未達此層數前強制全圖生成",
            font=("Microsoft JhengHei", 8),
            bg=app.bg_card,
            fg="#888888",
        ).pack(side="left", padx=(5, 0))

        # Row 3: Selected range display
        tk.Label(
            roi_body,
            text="選取範圍：",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=3, column=0, sticky="w", pady=3)

        self.lbl_roi_range = tk.Label(
            roi_body,
            text="尚未選取",
            font=("Consolas", 9),
            bg=app.bg_card,
            fg="#888888",
        )
        self.lbl_roi_range.grid(row=3, column=1, sticky="w", pady=3, padx=(10, 0))

        self.lbl_roi_hint = tk.Label(
            roi_body,
            text="提示：在預覽畫布上拖曳框選區域，右鍵清除",
            font=("Microsoft JhengHei", 8),
            bg=app.bg_card,
            fg="#666666",
        )
        self.lbl_roi_hint.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # Row 5: Manual rewind layer input
        tk.Label(
            roi_body,
            text="回朔層數：",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=5, column=0, sticky="w", pady=3)

        rewind_frame = tk.Frame(roi_body, bg=app.bg_card)
        rewind_frame.grid(row=5, column=1, sticky="w", pady=3, padx=(10, 0))

        self.val_rewind_layer = tk.StringVar(value="")
        self.entry_rewind_layer = tk.Entry(
            rewind_frame,
            textvariable=self.val_rewind_layer,
            bg=app.bg_input,
            fg=app.fg_primary,
            insertbackground=app.fg_primary,
            font=("Consolas", 10),
            bd=0,
            width=8,
        )
        self.entry_rewind_layer.pack(side="left", ipady=3)

        self.btn_rewind_go = tk.Button(
            rewind_frame,
            text="回朔 / Rewind",
            font=("Microsoft JhengHei", 9, "bold"),
            bg=app.color_btn_default,
            fg=app.fg_primary,
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=0,
            padx=8,
            command=app.on_manual_rewind,
        )
        self.btn_rewind_go.pack(side="left", padx=(8, 0), ipady=1)

        self.lbl_rewind_hint = tk.Label(
            rewind_frame,
            text="",
            font=("Microsoft JhengHei", 8),
            bg=app.bg_card,
            fg="#888888",
        )
        self.lbl_rewind_hint.pack(side="left", padx=(8, 0))
