import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from gui.utils import global_log_buffer


class DialogsMixin:
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
            font=("Consolas", 9),
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

            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
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

    def open_text_generator(self):
        """Opens a modal for Text Vinyl generation."""
        try:
            from tools.text_generator import save_text_json
        except ImportError as e:
            messagebox.showerror("Error", f"Failed to load text_generator module:\n{e}")
            return

        top = tk.Toplevel(self.root)
        top.title("Text Vinyl Generator")
        top.geometry("400x200")
        top.configure(bg=self.bg_main)
        top.transient(self.root)
        top.grab_set()

        tk.Label(
            top,
            text="Enter text for vinyl:",
            bg=self.bg_main,
            fg=self.fg_primary,
            font=("Microsoft JhengHei", 10),
        ).pack(pady=15)
        text_entry = tk.Entry(top, width=40, font=("Microsoft JhengHei", 12))
        text_entry.pack(pady=10)

        def on_generate():
            txt = text_entry.get().strip()
            if not txt:
                return
            out_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "text_vinyl.json",
            )
            try:
                save_text_json(
                    txt, "arial.ttf", 100, out_path, color=(255, 255, 255, 255)
                )
                self.entry_file_path.delete(0, tk.END)
                self.entry_file_path.insert(0, out_path)
                self.on_file_changed()
                self.log_to_console(f"Text Vinyl generated at {out_path}\n")
                top.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(
            top,
            text="Generate JSON",
            command=on_generate,
            bg=self.color_green,
            fg=self.fg_primary,
            font=("Microsoft JhengHei", 10, "bold"),
            bd=0,
            padx=20,
            pady=5,
        ).pack(pady=20)
