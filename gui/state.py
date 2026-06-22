import os
import tkinter as tk
from tkinter import filedialog, messagebox

from gui.utils import create_tooltip, remove_tooltip


class StateMixin:
    def on_file_drop(self, files):
        if not files:
            return
        file_path = files[0].decode("gbk")
        self.entry_file_path.delete(0, tk.END)
        self.entry_file_path.insert(0, file_path)
        self.on_file_changed()
        if file_path.lower().endswith(".json"):
            self.log_to_console(
                f"Detected JSON file dropped: {file_path}. Ready to import.\n"
            )

    def toggle_preview_state(self):
        self.enable_preview = not self.enable_preview
        if self.enable_preview:
            self.header.btn_toggle_preview.configure(
                text="關閉預覽 / Disable Preview", fg=self.color_green
            )
            self.log_to_console("[System] 預覽功能已開啟。\n")
            if getattr(self, "latest_canvas_array", None) is not None:
                self.need_preview_update = True
        else:
            self.header.btn_toggle_preview.configure(
                text="開啟預覽 / Enable Preview", fg=self.fg_secondary
            )
            self.log_to_console("[System] 預覽功能已關閉。\n")
            self.canvas_preview.delete("all")
            self.preview_image_id = None

            self.selection_roi = None
            self.selection_rect_id = None
            if hasattr(self, "_update_roi_range_label"):
                self._update_roi_range_label()

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

    def on_profile_selected(self, event):
        idx = self.combo_profile.current()
        if 0 <= idx < len(self.profiles):
            p = self.profiles[idx]
            self.generator_card.lbl_profile_desc.configure(
                text=f"Description: {p['desc']}"
            )

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

    def on_engine_selected(self, event):
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
            self.generator_card.lbl_taichi_arch.grid(
                row=5, column=0, sticky="w", pady=4
            )
            self.generator_card.taichi_arch_container.grid(
                row=5, column=1, sticky="we", pady=4, padx=(10, 0)
            )
            self.generator_card.lbl_taichi_device.grid(
                row=6, column=0, sticky="w", pady=4
            )
            self.combo_taichi_device.grid(
                row=6, column=1, sticky="we", pady=4, padx=(10, 0)
            )

            self.combo_taichi_arch.configure(state="readonly")
            self.combo_taichi_device.configure(state="readonly")
            self.generator_card.chk_hybrid.configure(state="normal")
        else:
            self.generator_card.lbl_taichi_arch.grid_remove()
            self.generator_card.taichi_arch_container.grid_remove()
            self.generator_card.lbl_taichi_device.grid_remove()
            self.combo_taichi_device.grid_remove()

        if engine_code == "GO_OPENCL":
            self.opts_card.pack_forget()
            if hasattr(self, "roi_card"):
                self.roi_card.pack_forget()
                self.selection_roi = None
                if getattr(self, "selection_rect_id", None):
                    self.canvas_preview.delete(self.selection_rect_id)
                    self.selection_rect_id = None
                if hasattr(self, "_update_roi_range_label"):
                    self._update_roi_range_label()
        else:
            self.opts_card.pack_forget()
            if hasattr(self, "roi_card"):
                self.roi_card.pack_forget()
            self.opts_card.pack(fill="x", pady=(0, 8), ipady=4)
            if hasattr(self, "roi_card"):
                self.roi_card.pack(fill="x", pady=(0, 8), ipady=4)

    def browse_file(self):
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
        path = self.entry_file_path.get().strip()
        if not path:
            self.btn_generate.configure(state="disabled", bg=self.bg_card, fg="#555555")
            self.btn_inject.configure(state="disabled", bg=self.bg_card, fg="#555555")
            return

        ext = os.path.splitext(path.lower())[1]

        if ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
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

            if hasattr(self, "lbl_metric_eta_header"):
                self.lbl_metric_eta_header.configure(text="ESTIMATED REMAINING")
            if hasattr(self, "lbl_metric_eta"):
                self.lbl_metric_eta.configure(text="0s")

        elif ext == ".json":
            self.btn_inject.configure(
                state="normal", bg=self.color_blue, fg=self.fg_primary
            )

            json_dir = os.path.dirname(path)
            json_base = os.path.splitext(os.path.basename(path))[0]
            if json_base.endswith("_masked"):
                json_base = json_base[:-7]
            if json_base == "_temp_resume":
                json_base = ""

            found_img = None
            if json_base:
                import glob

                for img_ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]:
                    candidates = glob.glob(
                        os.path.join(json_dir, f"{json_base}*{img_ext}")
                    )
                    if candidates:
                        found_img = candidates[0]
                        break

            if found_img:
                self.last_generated_image_path = found_img

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
                remove_tooltip(self.btn_generate)
                self.has_completed_generation = True
                self.update_roi_status_label()
            else:
                self.btn_generate.configure(
                    state="disabled",
                    text="缺少原始圖片\nCannot Resume",
                    bg=self.color_blue_disabled,
                    fg="#888888",
                )
                create_tooltip(
                    self.btn_generate,
                    "找不到原始圖片。請將原始圖片放入與 JSON 相同的資料夾內，\n並確保其主檔名與 JSON 相同，才能夠重新啟動生成引擎。",
                )

            if os.path.exists(path):
                import json

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    shapes = data.get("shapes", [])
                    if len(shapes) > 0:
                        num_layers = max(0, len(shapes) - 1)
                        if num_layers > 0:
                            try:
                                total_layers = int(self.val_layers.get())
                            except ValueError:
                                total_layers = 1000
                            if hasattr(self, "lbl_metric_layer"):
                                self.lbl_metric_layer.configure(
                                    text=f"{num_layers} / {total_layers}"
                                )
                            if hasattr(self, "lbl_metric_pct"):
                                pct = (
                                    (num_layers * 100.0 / total_layers)
                                    if total_layers > 0
                                    else 0.0
                                )
                                self.lbl_metric_pct.configure(text=f"{pct:.1f}%")

                            if hasattr(self, "progress_bar"):
                                self.progress_bar["value"] = pct

                        header = shapes[0]
                        h_data = header.get("data", [0.0, 0.0, 600.0, 600.0])
                        h_color = header.get("color", [128, 128, 128, 0])
                        width = int(h_data[2]) if len(h_data) >= 3 else 600
                        height = int(h_data[3]) if len(h_data) >= 4 else 600
                        avg_r, avg_g, avg_b = h_color[0], h_color[1], h_color[2]

                        import copy

                        import numpy as np

                        from tools.fh6_painter_generator import scale_shapes_list

                        render_scale = 2.0
                        width_high = int(width * render_scale)
                        height_high = int(height * render_scale)

                        shapes_copied = copy.deepcopy(shapes)
                        scale_shapes_list(shapes_copied, render_scale)

                        canvas = np.zeros(
                            (height_high, width_high, 4), dtype=np.float32
                        )

                        try:
                            from evaluators import EvaluatorFactory

                            evaluator = EvaluatorFactory.create_evaluator(
                                "NUMBA",
                                np.zeros(
                                    (height_high, width_high, 3), dtype=np.float32
                                ),
                                None,
                            )
                            evaluator.rebuild_canvas(
                                canvas, shapes_copied, avg_r, avg_g, avg_b
                            )
                            evaluator.cleanup()
                        except ImportError:
                            pass  # If NO JIT available during frozen UI preview

                        with self.preview_image_lock:
                            self.latest_canvas_array = canvas.copy()
                            self.need_preview_update = True
                except Exception as e:
                    self.log_to_console(f"\n[Instant Preview Loader Error] {e}\n")

        else:
            self.btn_generate.configure(state="disabled", bg=self.bg_card, fg="#555555")
            self.btn_inject.configure(state="disabled", bg=self.bg_card, fg="#555555")

    def lock_ui(self):
        self.entry_file_path.configure(state="disabled")
        self.combo_profile.configure(state="disabled")
        self.combo_engine.configure(state="disabled")
        self.entry_layers.configure(state="disabled")
        self.entry_candidates.configure(state="disabled")
        self.entry_steps.configure(state="disabled")
        self.generator_card.chk_adv.configure(state="disabled")
        self.chk_pyramid.configure(state="disabled")
        self.chk_importance.configure(state="disabled")
        self.chk_annealing.configure(state="disabled")
        self.chk_freeze.configure(state="disabled")
        self.chk_weight.configure(state="disabled")
        self.chk_decay.configure(state="disabled")
        self.header.btn_benchmark.configure(state="disabled")
        self.generator_card.chk_hybrid.configure(state="disabled")
        self.btn_inject.configure(state="disabled")

        if self.is_generating:
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
        self.entry_file_path.configure(state="normal")
        self.combo_profile.configure(state="readonly")
        self.combo_engine.configure(state="readonly")
        self.entry_layers.configure(state="normal")
        self.entry_candidates.configure(state="normal")
        self.entry_steps.configure(state="normal")
        self.generator_card.chk_adv.configure(state="normal")
        self.chk_pyramid.configure(state="normal")
        self.chk_importance.configure(state="normal")
        self.chk_annealing.configure(state="normal")
        self.chk_freeze.configure(state="normal")
        self.chk_weight.configure(state="normal")
        self.chk_decay.configure(state="normal")
        self.header.btn_benchmark.configure(state="normal")
        self.on_engine_selected(None)

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

    def on_close(self):
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
