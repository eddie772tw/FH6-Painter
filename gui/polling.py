import os
import time
import tkinter as tk
from tkinter import messagebox

import numpy as np
from PIL import Image, ImageTk


class PollingMixin:
    def poll_background_updates(self):
        """Cycles every 100ms in the main loop to repaint previews and handle metrics."""
        now_time = time.time()
        curr, total, speed, eta = self.latest_progress
        is_finished = (curr == total) if self.is_generating else True

        if self.need_preview_update and self.enable_preview:
            if (
                now_time - getattr(self, "last_canvas_draw_time", 0)
            ) >= 0.50 or is_finished:
                with self.preview_image_lock:
                    arr = (
                        self.latest_canvas_array.copy()
                        if self.latest_canvas_array is not None
                        else None
                    )
                    self.need_preview_update = False
                self.last_canvas_draw_time = now_time

                if arr is not None:
                    try:
                        arr_clipped = np.clip(arr, 0.0, 255.0).astype(np.uint8)
                        if arr.ndim == 3 and arr.shape[2] == 4:
                            arr_rgb = arr_clipped[:, :, :3].astype(np.float32)
                            alpha = arr_clipped[:, :, 3].astype(np.float32) / 255.0
                            alpha = np.expand_dims(alpha, axis=2)
                            bg_color = np.array([14.0, 14.0, 14.0], dtype=np.float32)
                            blended = (
                                arr_rgb * alpha + bg_color * (1.0 - alpha)
                            ).astype(np.uint8)
                            pil_img = Image.fromarray(blended)
                        else:
                            pil_img = Image.fromarray(arr_clipped)

                        resample_mode = (
                            Image.Resampling.NEAREST
                            if self.is_generating
                            else Image.Resampling.BILINEAR
                        )

                        canvas_w = self.canvas_preview.winfo_width()
                        canvas_h = self.canvas_preview.winfo_height()
                        if canvas_w <= 1 or canvas_h <= 1:
                            canvas_w = 380
                            canvas_h = 380

                        w, h = pil_img.size
                        scale = min(canvas_w / w, canvas_h / h)
                        new_w = max(1, int(w * scale))
                        new_h = max(1, int(h * scale))

                        pil_resized = pil_img.resize((new_w, new_h), resample_mode)
                        self.img_tk = ImageTk.PhotoImage(pil_resized)

                        self.render_meta = {
                            "scale": scale,
                            "cx": canvas_w / 2,
                            "cy": canvas_h / 2,
                            "w": new_w,
                            "h": new_h,
                            "orig_w": w,
                            "orig_h": h,
                        }

                        center_x = canvas_w / 2
                        center_y = canvas_h / 2
                        if getattr(self, "preview_image_id", None) is None:
                            self.canvas_preview.delete("all")
                            self.preview_image_id = self.canvas_preview.create_image(
                                center_x,
                                center_y,
                                anchor="center",
                                image=self.img_tk,
                            )
                        else:
                            try:
                                self.canvas_preview.itemconfig(
                                    self.preview_image_id, image=self.img_tk
                                )
                                self.canvas_preview.coords(
                                    self.preview_image_id, center_x, center_y
                                )
                            except Exception:
                                self.canvas_preview.delete("all")
                                self.preview_image_id = (
                                    self.canvas_preview.create_image(
                                        center_x,
                                        center_y,
                                        anchor="center",
                                        image=self.img_tk,
                                    )
                                )
                    except Exception as e:
                        self.log_to_console(f"\n[Preview Error] {e}\n")

        # 3. Update HUD Metrics
        if self.is_generating:
            curr, total, speed, eta = self.latest_progress
            self.lbl_metric_layer.configure(text=f"{curr} / {total}")
            self.lbl_metric_speed.configure(text=f"{speed:.1f} L/s")
            self.lbl_metric_eta.configure(text=f"{eta:.0f}s")
            pct = (curr * 100.0 / total) if total > 0 else 0.0
            self.lbl_metric_pct.configure(text=f"{pct:.1f}%")
            self.progress_bar["value"] = pct
            self.needs_checkpoint_scan = True
        else:
            if getattr(self, "needs_checkpoint_scan", True):
                self.scan_checkpoints()
                self.needs_checkpoint_scan = False

        # 4. Check Thread Completion for UX Automatic Transitions
        if getattr(self, "active_thread", None) and not self.active_thread.is_alive():
            self.active_thread = None

            self.unlock_ui()

            if self.is_generating:
                self.is_generating = False

                elapsed_time = time.time() - getattr(
                    self, "generation_start_time", time.time()
                )
                if hasattr(self, "lbl_metric_eta_header"):
                    self.lbl_metric_eta_header.configure(text="TOTAL DURATION")
                if hasattr(self, "lbl_metric_eta"):
                    self.lbl_metric_eta.configure(text=f"{elapsed_time:.1f}s")

                if self.cancel_generation_flag:
                    self.header.status_lbl.configure(text="GEN STOPPED", fg="#FFA500")
                    self.log_to_console(
                        "\n[System] Shape generation process stopped by user.\n"
                    )
                else:
                    self.header.status_lbl.configure(
                        text="GEN DONE", fg=self.color_green
                    )
                    self.log_to_console(
                        "\n[System] Shape generation process completed.\n"
                    )

                self.has_completed_generation = True
                self.update_roi_status_label()

                if self.auto_load_json_path and os.path.exists(
                    self.auto_load_json_path
                ):
                    self.log_to_console(
                        f"[UX Transition] Automatically loading generated JSON:\n-> {self.auto_load_json_path}\n"
                    )
                    self.entry_file_path.delete(0, tk.END)
                    self.entry_file_path.insert(
                        0, os.path.abspath(self.auto_load_json_path)
                    )
                    self.on_file_changed()
                    self.auto_load_json_path = None
                    self.btn_inject.focus_set()

            elif self.is_importing:
                self.is_importing = False
                result = getattr(self, "import_result", 1)
                if result == 0:
                    self.header.status_lbl.configure(
                        text="INJECT DONE", fg=self.color_blue
                    )
                    self.log_to_console(
                        "\n[System] Livery memory injection completed.\n"
                    )

                    imported_layers = self.val_layers.get()
                    messagebox.showinfo(
                        "導入成功 / Import Completed",
                        f"彩繪圖層注入成功！\n共成功導入 {imported_layers} 個幾何圖層至遊戲記憶體中。",
                    )
                else:
                    self.header.status_lbl.configure(text="INJECT ERROR", fg="#D32F2F")
                    self.log_to_console(
                        "\n[System] ERROR: Livery memory injection failed! Check log/terminal for details.\n"
                    )

                    from gui.components.base import draw_cyber_placeholder

                    draw_cyber_placeholder(self, text="INJECT FAILED")

                    messagebox.showerror(
                        "導入失敗 / Import Failed",
                        "彩繪圖層注入失敗！無任何級別的候選者通過驗證。\n\n"
                        "請點擊右上角「診斷主控台 / Show Logs」查看詳細驗證失敗原因。\n\n"
                        "常見疑難排解：\n"
                        "1. 確保您已進入編輯器並建立了正確數量的圓形圖層。\n"
                        "2. ⚠️ 確保所有圓形圖層都已「解除群組 (Ungrouped)」。\n"
                        "3. 嘗試退出編輯器再重新進入，並重新建立圖層。\n"
                        "4. 如果 Log 顯示 LastError=5 (Access Denied)，請以「系統管理員身分」重啟本程式。",
                    )

        if getattr(self, "root", None):
            self.root.after(100, self.poll_background_updates)

    def on_canvas_resize(self, event):
        """當預覽畫布大小改變時觸發重新整理"""
        if not self.enable_preview:
            self.canvas_preview.delete("all")
            self.preview_image_id = None
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
        elif getattr(self, "latest_canvas_array", None) is not None:
            self.need_preview_update = True
        else:
            from gui.components.base import draw_cyber_placeholder

            draw_cyber_placeholder(self)
