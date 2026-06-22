import tkinter as tk
from tkinter import ttk

from gui.components.base import create_card_header
from gui.utils import Tooltip


class OptimizationsCard(ttk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, style="Card.TFrame", *args, **kwargs)
        self.app = app

        create_card_header(
            self,
            "2.5 ADVANCED OPTIMIZATIONS",
            "Toggle high-performance optimization algorithms",
            app,
        )

        opts_body = tk.Frame(self, bg=app.bg_card)
        opts_body.pack(fill="x", padx=15, pady=5)
        opts_body.columnconfigure(0, weight=1)
        opts_body.columnconfigure(1, weight=1)

        self.var_pyramid = tk.BooleanVar(
            value=app.opt_settings["image_pyramid"]["enabled"]
        )
        self.var_importance = tk.BooleanVar(
            value=app.opt_settings["importance_sampling"]["enabled"]
        )
        self.var_annealing = tk.BooleanVar(
            value=app.opt_settings["simulated_annealing"]["enabled"]
        )
        self.var_freeze = tk.BooleanVar(
            value=app.opt_settings["dynamic_freeze"]["enabled"]
        )
        self.var_weight = tk.BooleanVar(
            value=app.opt_settings["error_weighting"]["enabled"]
        )
        self.var_decay = tk.BooleanVar(
            value=app.opt_settings["decaying_shape"]["enabled"]
        )

        self.chk_pyramid = tk.Checkbutton(
            opts_body,
            text="漸進式像素採樣 (Progressive Sampling)",
            variable=self.var_pyramid,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_opt_changed,
        )
        self.chk_pyramid.grid(row=0, column=0, sticky="w", pady=3)

        self.chk_freeze = tk.Checkbutton(
            opts_body,
            text="動態凍結遮罩 (Dynamic Freeze)",
            variable=self.var_freeze,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_opt_changed,
        )
        self.chk_freeze.grid(row=0, column=1, sticky="w", pady=3)

        self.chk_importance = tk.Checkbutton(
            opts_body,
            text="錯誤驅動重點採樣 (Importance)",
            variable=self.var_importance,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_opt_changed,
        )
        self.chk_importance.grid(row=1, column=0, sticky="w", pady=3)

        self.chk_weight = tk.Checkbutton(
            opts_body,
            text="區域誤差加權 (Error Weighting)",
            variable=self.var_weight,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_opt_changed,
        )
        self.chk_weight.grid(row=1, column=1, sticky="w", pady=3)

        self.chk_annealing = tk.Checkbutton(
            opts_body,
            text="解析解最佳色彩 (Analytical Color)",
            variable=self.var_annealing,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_opt_changed,
        )
        self.chk_annealing.grid(row=2, column=0, sticky="w", pady=3)

        self.chk_decay = tk.Checkbutton(
            opts_body,
            text="衰減式形狀限縮 (Decaying Shape)",
            variable=self.var_decay,
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=app.on_opt_changed,
        )
        self.chk_decay.grid(row=2, column=1, sticky="w", pady=3)

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
