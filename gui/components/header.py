import tkinter as tk
import webbrowser


class HeaderBar(tk.Frame):
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, bg=app.bg_main, *args, **kwargs)
        self.app = app

        title_label = tk.Label(
            self,
            text="FH6 Painter",
            font=("Outfit", 18, "bold"),
            bg=app.bg_main,
            fg=app.color_green,
        )
        title_label.pack(side="left")

        subtitle_label = tk.Label(
            self,
            text="  |  FH6 ONE-STOP LIVERY ENGINE",
            font=("Microsoft JhengHei", 10, "bold"),
            bg=app.bg_main,
            fg=app.fg_secondary,
        )
        subtitle_label.pack(side="left", fill="y")

        self.status_lbl = tk.Label(
            self,
            text="READY",
            font=("Consolas", 10, "bold"),
            bg=app.bg_card,
            fg="#888888",
            padx=10,
            pady=2,
            bd=1,
            relief="solid",
        )
        self.status_lbl.pack(side="right")

        self.btn_show_logs = tk.Button(
            self,
            text="診斷主控台 / Show Logs",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=app.bg_card,
            fg=app.color_blue,
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=app.open_log_window,
        )
        self.btn_show_logs.pack(side="right", padx=(0, 10))

        self.btn_benchmark = tk.Button(
            self,
            text="效能測試 / Benchmark",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=app.bg_card,
            fg=app.color_blue,
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=app.run_benchmark_gui,
        )
        self.btn_benchmark.pack(side="right", padx=(0, 10))

        self.btn_market = tk.Button(
            self,
            text="前往市場 / Open Market",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=app.bg_card,
            fg="#F4A261",  # Orange tint for market
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=lambda: webbrowser.open("https://painter6.com"),
        )
        self.btn_market.pack(side="right", padx=(0, 10))

        self.btn_toggle_preview = tk.Button(
            self,
            text="關閉預覽 / Disable Preview",
            font=("Microsoft JhengHei", 8, "bold"),
            bg=app.bg_card,
            fg=app.color_green,
            activebackground=app.color_btn_default_hover,
            activeforeground=app.fg_primary,
            bd=1,
            relief="solid",
            highlightthickness=0,
            padx=8,
            pady=2,
            command=app.toggle_preview_state,
        )
        self.btn_toggle_preview.pack(side="right", padx=(0, 10))
