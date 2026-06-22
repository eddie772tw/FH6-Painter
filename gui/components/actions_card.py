import tkinter as tk
from tkinter import ttk

from gui.components.base import create_card_header


class ActionsCard(ttk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, style="Card.TFrame", *args, **kwargs)
        self.app = app

        create_card_header(
            self,
            "3. WORKSPACE ACTIONS",
            "Launch shape generation or memory injection pipeline",
            app,
        )

        actions_body = tk.Frame(self, bg=app.bg_card)
        actions_body.pack(fill="both", expand=True, padx=15, pady=8)

        # Start Generation Button (Green)
        self.btn_generate = tk.Button(
            actions_body,
            text="開始生成 JSON\nStart Generation",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=app.color_green,
            fg=app.fg_primary,
            activebackground=app.color_green_hover,
            activeforeground=app.fg_primary,
            bd=0,
            pady=10,
            command=app.start_generation,
        )
        self.btn_generate.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # Inject to Game Button (Blue)
        self.btn_inject = tk.Button(
            actions_body,
            text="注入至遊戲\nImport to Game",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=app.color_blue,
            fg=app.fg_primary,
            activebackground=app.color_blue_hover,
            activeforeground=app.fg_primary,
            bd=0,
            pady=10,
            command=app.start_injection,
        )
        self.btn_inject.pack(side="right", fill="both", expand=True, padx=(8, 0))
