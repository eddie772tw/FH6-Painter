import tkinter as tk
from tkinter import ttk

from gui.components.base import create_card_header


class InputSourceCard(ttk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, style="Card.TFrame", *args, **kwargs)
        self.app = app

        create_card_header(
            self,
            "1. INPUT SOURCE",
            "Select target image (PNG/JPG) or geometry JSON file",
            app,
        )

        input_body = tk.Frame(self, bg=app.bg_card)
        input_body.pack(fill="x", padx=15, pady=(5, 5))

        self.entry_file_path = tk.Entry(
            input_body,
            bg=app.bg_input,
            fg=app.fg_primary,
            insertbackground=app.fg_primary,
            font=("Microsoft JhengHei", 9),
            bd=0,
        )
        self.entry_file_path.pack(
            side="left", fill="x", expand=True, ipady=6, padx=(0, 5)
        )
        self.entry_file_path.bind("<KeyRelease>", lambda e: app.on_file_changed())

        btn_text = tk.Button(
            input_body,
            text="Text Vinyl",
            font=("Microsoft JhengHei", 9, "bold"),
            bg=app.color_btn_default,
            fg=app.fg_primary,
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=0,
            padx=12,
            command=app.open_text_generator,
        )
        btn_text.pack(side="right", padx=(5, 0), ipady=2)

        btn_browse = tk.Button(
            input_body,
            text="Browse",
            font=("Microsoft JhengHei", 9, "bold"),
            bg=app.color_btn_default,
            fg=app.fg_primary,
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=0,
            padx=12,
            command=app.browse_file,
        )
        btn_browse.pack(side="right", ipady=2)
