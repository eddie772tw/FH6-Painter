import os
import tkinter as tk
from tkinter import ttk

from gui.components.base import create_card_header
from gui.utils import get_project_root


class GeneratorSettingsCard(ttk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, style="Card.TFrame", *args, **kwargs)
        self.app = app

        create_card_header(
            self,
            "2. GENERATOR SETTINGS",
            "Configure livery shape reconstruction thresholds",
            app,
        )

        params_body = tk.Frame(self, bg=app.bg_card)
        params_body.pack(fill="x", padx=15, pady=5)

        # Profile Dropdown
        tk.Label(
            params_body,
            text="Speed/Quality Profile:",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.combo_profile = ttk.Combobox(
            params_body,
            values=[p["name"] for p in app.profiles],
            state="readonly",
            width=35,
        )
        self.combo_profile.grid(row=0, column=1, sticky="we", pady=4, padx=(10, 0))
        self.combo_profile.current(0)
        self.combo_profile.bind("<<ComboboxSelected>>", app.on_profile_selected)

        # Profile Description Label
        self.lbl_profile_desc = tk.Label(
            params_body,
            text="...",
            font=("Microsoft JhengHei", 8, "italic"),
            bg=app.bg_card,
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
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=2, column=0, sticky="w", pady=4)

        self.val_layers = tk.StringVar(value="2000")

        layers_container = tk.Frame(params_body, bg=app.bg_card)
        layers_container.grid(row=2, column=1, sticky="w", pady=4, padx=(10, 0))

        self.entry_layers = tk.Entry(
            layers_container,
            textvariable=self.val_layers,
            bg=app.bg_input,
            fg=app.fg_primary,
            insertbackground=app.fg_primary,
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
            bg=app.bg_card,
            fg=app.color_blue,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            padx=10,
        )
        self.chk_early_conv.pack(side="left")

        lbl_limits_tip = tk.Label(
            params_body,
            text="FH6 Game Limits: Bumper up to 1000 | Left/Right/Top up to 3000",
            font=("Microsoft JhengHei", 8),
            bg=app.bg_card,
            fg=app.color_blue,
        )
        lbl_limits_tip.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 8))

        # JIT Engine Plugin Dropdown
        tk.Label(
            params_body,
            text="JIT Engine Plugin:",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=4, column=0, sticky="w", pady=4)

        evaluator_names = []
        for e in app.available_evaluators:
            if e["available"]:
                evaluator_names.append(e["name"])
            else:
                evaluator_names.append(f"{e['name']} (Unavailable)")

        self.combo_engine = ttk.Combobox(
            params_body, values=evaluator_names, state="readonly", width=35
        )
        self.combo_engine.grid(row=4, column=1, sticky="we", pady=4, padx=(10, 0))

        default_idx = 0
        for idx, e in enumerate(app.available_evaluators):
            if e["code"] == "NUMBA" and e["available"]:
                default_idx = idx
                break
        self.combo_engine.current(default_idx)
        self.combo_engine.bind("<<ComboboxSelected>>", app.on_engine_selected)

        # Taichi Arch
        self.lbl_taichi_arch = tk.Label(
            params_body,
            text="Taichi Arch GPU Mode:",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        )
        self.lbl_taichi_arch.grid(row=5, column=0, sticky="w", pady=4)

        self.taichi_arch_container = tk.Frame(params_body, bg=app.bg_card)
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
            bg=app.bg_card,
            fg=app.color_blue,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            padx=10,
        )
        self.chk_hybrid.pack(side="left")

        # Taichi Device
        self.lbl_taichi_device = tk.Label(
            params_body,
            text="Taichi GPU Device:",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        )
        self.lbl_taichi_device.grid(row=6, column=0, sticky="w", pady=4)

        self.combo_taichi_device = ttk.Combobox(
            params_body,
            values=[f"({idx}) {gpu}" for idx, gpu in enumerate(app.gpu_list)],
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
            bg=app.bg_card,
            fg=app.fg_secondary,
            selectcolor=app.bg_card,
            activebackground=app.bg_card,
            activeforeground=app.fg_primary,
            bd=0,
            command=self.toggle_advanced_panel,
        )
        self.chk_adv.grid(row=7, column=0, columnspan=2, sticky="w", pady=4)

        self.adv_frame = tk.Frame(params_body, bg=app.bg_card)

        tk.Label(
            self.adv_frame,
            text="Candidates (Samples):",
            font=("Microsoft JhengHei", 9),
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.val_candidates = tk.StringVar(value="20000")
        self.entry_candidates = tk.Entry(
            self.adv_frame,
            textvariable=self.val_candidates,
            bg=app.bg_input,
            fg=app.fg_primary,
            insertbackground=app.fg_primary,
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
            bg=app.bg_card,
            fg=app.fg_secondary,
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.val_steps = tk.StringVar(value="200")
        self.entry_steps = tk.Entry(
            self.adv_frame,
            textvariable=self.val_steps,
            bg=app.bg_input,
            fg=app.fg_primary,
            insertbackground=app.fg_primary,
            font=("Consolas", 9),
            bd=0,
            width=12,
        )
        self.entry_steps.grid(
            row=1, column=1, sticky="w", pady=4, padx=(10, 0), ipady=3
        )

    def toggle_advanced_panel(self):
        if self.show_adv.get():
            self.adv_frame.grid(row=8, column=0, columnspan=2, sticky="we", pady=(5, 0))
        else:
            self.adv_frame.grid_forget()
