import os
import shutil
import sys
import threading
import time
from tkinter import messagebox

import numpy as np
from PIL import Image

from evaluators import EvaluatorFactory
from gui.utils import create_tooltip, get_project_root, remove_tooltip


class WorkersMixin:
    def start_generation(self):
        """Collects GUI configuration and starts the Numba shape generation loop on a worker thread."""
        if self.active_thread:
            return

        img_path = self.entry_file_path.get().strip()
        resume_path = None

        # If the input path is a JSON file but we have a stored image path, use the stored image path instead
        if img_path.lower().endswith(".json"):
            resume_path = img_path
            if getattr(self, "last_generated_image_path", None) and os.path.exists(
                self.last_generated_image_path
            ):
                img_path = self.last_generated_image_path
            else:
                messagebox.showerror(
                    "Error",
                    "Please select or generate from the original image first, then drop the JSON to resume.",
                )
                return
        else:
            # Store the current image path for future regeneration
            self.last_generated_image_path = img_path

        if not os.path.exists(img_path):
            messagebox.showerror("Error", f"Input file not found:\n{img_path}")
            return

        # Layers Limit Check
        try:
            layers = int(self.val_layers.get())
            if not (500 <= layers <= 3000):
                raise ValueError()
        except ValueError:
            messagebox.showerror(
                "Error",
                "Invalid Layers Limit.\nPlease enter an integer between 500 and 3000.",
            )
            return

        # Determine output JSON name and create a structured output folder under the project root
        img_base = os.path.splitext(os.path.basename(img_path))[0]
        project_root = get_project_root()
        output_dir = os.path.join(project_root, "output", img_base)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Copy original image to output directory
        if not img_path.lower().endswith(".json"):
            try:
                dest_img_path = os.path.join(output_dir, os.path.basename(img_path))
                if os.path.abspath(img_path) != os.path.abspath(dest_img_path):
                    shutil.copy2(img_path, dest_img_path)
                    # Update img_path to the copied one so next load points here
                    img_path = dest_img_path
                    self.last_generated_image_path = img_path
            except Exception as e:
                self.log_to_console(
                    f"[Warning] Failed to copy original image to output: {e}\n"
                )

        # Apply Region Mask (Alpha Masking) if ROI is defined and we are generating from an image (not resuming json)
        if self.selection_roi and not img_path.lower().endswith(".json"):
            try:
                with Image.open(img_path) as src_img:
                    src_img = src_img.convert("RGBA")
                    arr = np.array(src_img)
                    x1, y1, x2, y2 = self.selection_roi
                    if self.render_meta:
                        meta = self.render_meta
                        cx = meta["cx"]
                        cy = meta["cy"]
                        new_w = meta["w"]
                        new_h = meta["h"]

                        # Top-left corner of the image on the canvas
                        img_canvas_x = cx - new_w / 2.0
                        img_canvas_y = cy - new_h / 2.0

                        # Real scale between canvas display size and actual source image size
                        real_scale_x = new_w / float(arr.shape[1])
                        real_scale_y = new_h / float(arr.shape[0])

                        # Map canvas coordinates back to original image pixels
                        rx1 = int((x1 - img_canvas_x) / real_scale_x)
                        ry1 = int((y1 - img_canvas_y) / real_scale_y)
                        rx2 = int((x2 - img_canvas_x) / real_scale_x)
                        ry2 = int((y2 - img_canvas_y) / real_scale_y)
                    else:
                        rx1, ry1, rx2, ry2 = x1, y1, x2, y2

                    rx1 = max(0, min(rx1, arr.shape[1] - 1))
                    rx2 = max(0, min(rx2, arr.shape[1] - 1))
                    ry1 = max(0, min(ry1, arr.shape[0] - 1))
                    ry2 = max(0, min(ry2, arr.shape[0] - 1))

                    x_min, x_max = min(rx1, rx2), max(rx1, rx2)
                    y_min, y_max = min(ry1, ry2), max(ry1, ry2)

                    # Create a mask and apply to alpha channel
                    alpha_mask = np.zeros((arr.shape[0], arr.shape[1]), dtype=np.uint8)
                    shape_mode = self.var_roi_shape.get()

                    if shape_mode == "ellipse":
                        # Elliptical mask using distance equation
                        center_x = (x_min + x_max) / 2.0
                        center_y = (y_min + y_max) / 2.0
                        radius_x = (x_max - x_min) / 2.0
                        radius_y = (y_max - y_min) / 2.0
                        if radius_x > 0 and radius_y > 0:
                            yy, xx = np.ogrid[: arr.shape[0], : arr.shape[1]]
                            ellipse_dist = ((xx - center_x) / radius_x) ** 2 + (
                                (yy - center_y) / radius_y
                            ) ** 2
                            alpha_mask[ellipse_dist <= 1.0] = 255
                        mode_label = "橢圓"
                    else:
                        # Rectangle mask
                        alpha_mask[y_min : y_max + 1, x_min : x_max + 1] = 255
                        mode_label = "矩形"

                    # Combine existing alpha with our mask (bitwise AND basically)
                    arr[:, :, 3] = np.minimum(arr[:, :, 3], alpha_mask)

                    masked_img = Image.fromarray(arr)
                    masked_path = os.path.join(output_dir, f"{img_base}_masked.png")
                    masked_img.save(masked_path)
                    img_path = masked_path
                    self.log_to_console(
                        f"[Region Mask] {mode_label} Alpha mask applied. ROI: ({x_min},{y_min}) to ({x_max},{y_max})\n"
                    )
            except Exception as e:
                self.log_to_console(f"ERROR applying region mask: {e}\n")
        output_dir = os.path.join(project_root, "output", img_base)
        output_json = os.path.join(output_dir, f"{img_base}.json")
        self.auto_load_json_path = output_json

        # Determine profile INI path
        profile_idx = self.combo_profile.current()
        profile_path = (
            self.profiles[profile_idx]["path"]
            if 0 <= profile_idx < len(self.profiles)
            else None
        )

        # 動態同步「提早收斂」在 GUI 中的啟用狀態至優化設定中
        if "early_convergence" not in self.opt_settings:
            self.opt_settings["early_convergence"] = {}
        self.opt_settings["early_convergence"]["enabled"] = self.var_early_conv.get()

        # Override values
        candidates = None
        steps = None
        if self.show_adv.get():
            try:
                candidates = int(self.val_candidates.get())
                steps = int(self.val_steps.get())
            except ValueError:
                messagebox.showerror(
                    "Error", "Advanced Overrides must be valid integers."
                )
                return

        # Pre-reset preview metrics
        self.latest_progress = (0, layers, 0.0, 0.0)
        self.lbl_metric_layer.configure(text=f"0 / {layers}")
        self.lbl_metric_speed.configure(text="0.0 L/s")
        if hasattr(self, "lbl_metric_eta_header"):
            self.lbl_metric_eta_header.configure(text="ESTIMATED REMAINING")
        self.lbl_metric_eta.configure(text="0s")
        self.lbl_metric_pct.configure(text="0.0%")
        self.progress_bar["value"] = 0

        # Lock GUI controls
        self.cancel_generation_flag = False
        self.is_generating = True
        self.generation_start_time = time.time()
        self.lock_ui()
        self.status_lbl.configure(text="GENERATING", fg=self.color_green)

        self.log_to_console(
            "[System] Triggering high-performance Python shape generator...\n"
        )

        # Progress callback hook
        self.last_cb_update_time = 0.0

        def generator_cb(curr, total, speed, eta, canvas_arr):
            if self.cancel_generation_flag:
                return "ABORT"

            # 更新節流：限制拷貝頻率大約在 20Hz (每 50ms 一次) 或是最後一幀時強制拷貝
            now_time = time.time()
            if (now_time - self.last_cb_update_time >= 0.05) or (curr == total):
                with self.preview_image_lock:
                    self.latest_canvas_array = canvas_arr.copy()
                    self.latest_progress = (curr, total, speed, eta)
                    self.need_preview_update = True
                self.last_cb_update_time = now_time

            # 若為 Taichi/Numba 引擎，釋放 GIL 給 Tkinter 執行緒以保持 GUI 響應與終端機刷新，避免線程飢餓與 DWM 阻塞
            if engine_code == "TAICHI":
                time.sleep(0.002)
            elif engine_code == "NUMBA":
                # Numba 模式也釋放極小時間 (1ms) 給 CPU 進行排程，減少 DWM 阻塞，徹底解決 AMD GPU VCE 佔用問題
                time.sleep(0.001)
            return True

        # Determine JIT Engine to use
        engine_idx = self.combo_engine.current()
        engine_code = (
            self.available_evaluators[engine_idx]["code"]
            if 0 <= engine_idx < len(self.available_evaluators)
            else "NUMBA"
        )

        # 獲取 Taichi GPU 與後端架構設定及混合模式
        taichi_arch = self.combo_taichi_arch.get()
        taichi_device_id = self.combo_taichi_device.current()
        use_pure_gpu = not self.var_hybrid.get()

        # Launch Worker Thread in Safe Wrapper to prevent silent thread deaths
        if engine_code == "GO_OPENCL":
            self.active_thread = threading.Thread(
                target=self.safe_run_go_generator,
                args=(
                    img_path,
                    output_json,
                    profile_path,
                    layers,
                ),
                kwargs={
                    "resume_path": resume_path,
                },
                daemon=True,
            )
        else:
            self.active_thread = threading.Thread(
                target=self.safe_run_generator,
                args=(
                    img_path,
                    output_json,
                    profile_path,
                    layers,
                    candidates,
                    steps,
                    generator_cb,
                    self.opt_settings,
                    engine_code,
                ),
                kwargs={
                    "taichi_arch": taichi_arch,
                    "taichi_device_id": taichi_device_id,
                    "use_pure_gpu": use_pure_gpu,
                    "resume_path": resume_path,
                },
                daemon=True,
            )
        self.active_thread.start()

    def safe_run_generator(self, *args, **kwargs):
        """安全的外掛執行緒外殼，捕獲生圖引擎內部可能引發的所有異常"""
        try:
            from tools.fh6_painter_generator import run_generator

            res = run_generator(*args, **kwargs)
            if res != 0:
                self.root.after(
                    0,
                    lambda: self.on_generation_failed(
                        "Generator returned a non-zero exit code. Please inspect terminal diagnostics."
                    ),
                )
        except Exception as e:
            # 捕獲所有異常 (包括 Taichi 編譯、硬體相容性、CUDA/OpenGL 崩潰)
            import traceback

            tb = traceback.format_exc()
            err_msg = f"{e}\n\n[Traceback]\n{tb}"
            self.root.after(0, lambda msg=err_msg: self.on_generation_failed(msg))

    def safe_run_go_generator(
        self, img_path, output_json, profile_path, layers, resume_path=None
    ):
        """安全地調用 Go-OpenCL 二進位生成器（已標準化重構為 Evaluator 插件）"""
        try:
            # 獲取當前選定的 GoOpenCLEvaluator 類別並實例化之
            engine_idx = self.combo_engine.current()
            evaluator_cls = self.available_evaluators[engine_idx]["class"]

            # 使用目前的 canvas 圖像尺寸來實例化，以維持 BaseEvaluator 行為
            arr_shape = (2, 2, 3)
            if self.latest_canvas_array is not None:
                arr_shape = self.latest_canvas_array.shape

            evaluator = evaluator_cls(
                self.latest_canvas_array
                if self.latest_canvas_array is not None
                else np.zeros(arr_shape, dtype=np.float32)
            )

            self.current_go_evaluator = evaluator

            def on_progress(curr, total, speed, eta):
                with self.preview_image_lock:
                    self.latest_progress = (curr, total, speed, eta)

            def on_log(msg):
                self.log_to_console(msg)

            def on_preview(arr):
                with self.preview_image_lock:
                    self.latest_canvas_array = arr
                    self.need_preview_update = True

            def on_success():
                pass

            def on_failed(msg):
                self.root.after(0, lambda: self.on_generation_failed(msg))

            evaluator.run_generator(
                img_path=img_path,
                output_json=output_json,
                profile_path=profile_path,
                layers=layers,
                resume_path=resume_path,
                progress_callback=on_progress,
                log_callback=on_log,
                preview_callback=on_preview,
                on_success_callback=on_success,
                on_failed_callback=on_failed,
            )

        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            err_msg = f"{e}\n\n[Traceback]\n{tb}"
            self.root.after(0, lambda msg=err_msg: self.on_generation_failed(msg))
        finally:
            self.current_go_evaluator = None

    def kill_generator_process(self):
        """結束執行中的 Go 執行檔行程"""
        proc = getattr(self, "generator_proc", None)
        if proc is not None:
            try:
                if sys.platform == "win32":
                    import subprocess

                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5,
                    )
                else:
                    proc.terminate()
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    def on_generation_failed(self, error_message):
        """當生圖引擎異常崩潰時，優雅地通知使用者並完全重置 UI 狀態"""
        self.is_generating = False
        self.unlock_ui()
        self.status_lbl.configure(text="GEN ERROR", fg="#D32F2F")
        self.log_to_console(f"\n[ERROR] Generation thread failed:\n{error_message}\n")

        # 精緻高階錯誤提示視窗
        messagebox.showerror(
            "Livery Engine Error",
            f"An error occurred within the livery generation engine:\n\n{error_message}\n"
            "Suggestions:\n"
            "1. If using Taichi, try switching 'Taichi Arch GPU Mode' to 'Vulkan' (Recommended) or 'CPU'.\n"
            "2. Switch 'JIT Engine Plugin' to 'Numba JIT' for maximum baseline compatibility.",
        )

    def stop_generation(self):
        """Sets the cancellation flag to abort active shape generation."""
        if not self.is_generating or self.cancel_generation_flag:
            return

        self.cancel_generation_flag = True

        # 如果當前有運行中的 Go 評估器，調用它的 stop_generator 方法
        go_eval = getattr(self, "current_go_evaluator", None)
        if go_eval:
            go_eval.stop_generator()
        else:
            self.kill_generator_process()
        self.log_to_console(
            "\n[System] Stop requested. Gracefully finalizing current layer and saving progress...\n"
        )
        self.status_lbl.configure(text="STOPPING", fg="#FFA500")

        # Disable the stop button and show "Stopping..."
        self.btn_generate.configure(
            state="disabled", text="正在停止...\nStopping...", bg="#555555"
        )

    def run_importer_wrapper(self, **kwargs):
        """BACKGROUND THREAD: Invokes the actual run_importer logic and captures the return code."""
        self.import_result = None
        try:
            from tools.fh6_import_layer_table import run_importer

            self.import_result = run_importer(**kwargs)
        except Exception as e:
            self.import_result = 1
            print(
                f"Exception raised in background importer thread: {e}", file=sys.stderr
            )

    def start_injection(self):
        """Launches Win32 memory writing thread on the active game process."""
        if self.active_thread:
            return

        json_path = self.entry_file_path.get().strip()
        if not os.path.exists(json_path):
            messagebox.showerror("Error", f"Geometry JSON file not found:\n{json_path}")
            return

        # QoL 2: 載入 JSON 路徑時，自動解析 JSON 檔內的實體圖層數作為注入基準，免除手動設定
        if json_path.lower().endswith(".json") and os.path.exists(json_path):
            try:
                import json

                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                shapes = data.get("shapes", [])
                if len(shapes) > 0:
                    layers = len(shapes) - 1
                    self.val_layers.set(str(layers))
                else:
                    layers = 3000
            except Exception:
                try:
                    layers = int(self.val_layers.get())
                except ValueError:
                    layers = 3000
        else:
            try:
                layers = int(self.val_layers.get())
            except ValueError:
                layers = 3000

        # Confirm user opens ungrouped shapes
        confirm = messagebox.askyesno(
            "遊戲記憶體注入確認 / Game Injection Confirmation",
            "在開始注入前，請務必確認以下事項：\n\n"
            "1. 《極限競速：地平線 6》遊戲主程式 (forzahorizon6.exe) 正在運行中。\n"
            "2. 您目前已進入遊戲內的「彩繪貼圖組編輯器 (Vinyl Group Editor)」。\n"
            "3. ⚠️【極度重要】您在編輯器內建立的圓形圖層數量，必須「恰好精準等於」下方數值，不能多也不能少：\n"
            f"   👉 必須剛好是：{layers} 個未編組的圓形圖層！\n"
            "   （若圖層數量有任何偏差，記憶體搜尋將會失敗，且可能導致注入崩潰！）\n\n"
            "您是否確定要繼續執行記憶體注入？",
        )

        if not confirm:
            return

        # Lock UI
        self.lock_ui()
        self.is_importing = True
        self.status_lbl.configure(text="INJECTING", fg=self.color_blue)

        self.log_to_console(
            "[System] Opening Win32 process handles for forzahorizon6.exe...\n"
        )

        # Clean HUD Radar Canvas to signal injection
        self.draw_cyber_placeholder(text="INJECTING GEOMETRY")
        self.progress_bar["value"] = 0
        self.lbl_metric_pct.configure(text="HUD LOCKED")

        # Initialize result before starting thread
        self.import_result = None

        # Launch Worker Thread
        self.active_thread = threading.Thread(
            target=self.run_importer_wrapper,
            kwargs={
                "json_path": json_path,
                "layers": layers,
                "dry_run": False,
                "reverse": False,
                "include_header": False,
                "no_cache": False,
                "scale_div": 63.0,
                "coord_scale": 1.0,
                "max_candidates": 200000,
            },
            daemon=True,
        )
        self.active_thread.start()
