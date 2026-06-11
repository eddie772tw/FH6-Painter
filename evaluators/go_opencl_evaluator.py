#!/usr/bin/env python3
import glob
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np
from PIL import Image

from evaluators.base_evaluator import BaseEvaluator


def get_project_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Since this file is in evaluators/go_opencl_evaluator.py, parent is root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GoOpenCLEvaluator(BaseEvaluator):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None):
        super().__init__(target_image, alpha_mask)
        self.generator_proc = None
        self.cancel_flag = False

    def get_name(self) -> str:
        return "Go OpenCL (GPU, Fastest)"

    def is_available(self) -> bool:
        project_root = get_project_root()
        go_binary_path = os.path.join(
            project_root, "tools", "bin", "forza-painter-geometrize-go.exe"
        )
        return os.path.exists(go_binary_path)

    def get_device_type(self) -> str:
        return "GPU"

    def search_best_shape(
        self, current_canvas: np.ndarray, batch_size: int, params: dict
    ) -> tuple:
        raise NotImplementedError(
            "Go-OpenCL binary engine does not support single-step shape searching from Python."
        )

    def draw_shape_on_canvas(
        self,
        canvas: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
        r: float,
        g: float,
        b: float,
        alpha: float,
    ) -> None:
        raise NotImplementedError(
            "Go-OpenCL binary engine does not support drawing shapes on canvas from Python."
        )

    def rebuild_canvas(
        self,
        canvas: np.ndarray,
        shapes_list: list,
        avg_r: float,
        avg_g: float,
        avg_b: float,
    ) -> None:
        # Fallback to Pure Python rebuild
        from evaluators.pure_python_evaluator import PurePythonEvaluator

        fallback = PurePythonEvaluator(self.target_image, self.alpha_mask)
        fallback.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)

    def run_redundancy_check(
        self, shapes_list: list, width: int, height: int, final_check: bool = False
    ) -> list:
        # Fallback to Pure Python redundancy check
        from evaluators.pure_python_evaluator import PurePythonEvaluator

        fallback = PurePythonEvaluator(self.target_image, self.alpha_mask)
        return fallback.run_redundancy_check(shapes_list, width, height, final_check)

    def init_uncovered_map(
        self, width: int, height: int, has_alpha: bool, bias: float
    ) -> np.ndarray:
        # Fallback to Pure Python uncovered map init
        from evaluators.pure_python_evaluator import PurePythonEvaluator

        fallback = PurePythonEvaluator(self.target_image, self.alpha_mask)
        return fallback.init_uncovered_map(width, height, has_alpha, bias)

    def update_uncovered_mask(
        self,
        uncovered_map: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
    ) -> None:
        # Fallback to Pure Python uncovered map update
        from evaluators.pure_python_evaluator import PurePythonEvaluator

        fallback = PurePythonEvaluator(self.target_image, self.alpha_mask)
        fallback.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta_rad)

    def cleanup(self) -> None:
        self.stop_generator()

    # --- Go-OpenCL End-to-End Execution & Lifetime Management ---
    def run_generator(
        self,
        img_path: str,
        output_json: str,
        profile_path: str,
        layers: int,
        resume_path: str = None,
        progress_callback=None,
        log_callback=None,
        preview_callback=None,
        on_success_callback=None,
        on_failed_callback=None,
    ):
        self.cancel_flag = False
        temp_resume_path = None
        try:
            project_root = get_project_root()
            go_bin = os.path.join(
                project_root, "tools", "bin", "forza-painter-geometrize-go.exe"
            )

            output_base = output_json.replace(".json", "")
            output_dir = os.path.dirname(output_json)
            preview_png = os.path.join(output_dir, "preview.png")

            # Ensure the output directory exists before spawning the Go binary
            os.makedirs(output_dir, exist_ok=True)

            if os.path.exists(preview_png):
                try:
                    os.unlink(preview_png)
                except OSError:
                    pass

            if resume_path:
                try:
                    import json

                    with open(resume_path, "r", encoding="utf-8") as f:
                        res_data = json.load(f)

                    shapes = res_data.get("shapes", [])
                    for s in shapes:
                        if "data" in s:
                            s["data"] = [int(round(float(x))) for x in s["data"]]

                    temp_resume_path = resume_path.replace(".json", "_go_compat.json")
                    with open(temp_resume_path, "w", encoding="utf-8") as f:
                        json.dump(res_data, f)

                    resume_path = temp_resume_path
                except Exception as e:
                    if log_callback:
                        log_callback(
                            f"[System Warning] Failed to create Go-compatible resume JSON: {e}\n"
                        )

            cmd = [
                go_bin,
                img_path,
                "-settings",
                profile_path,
                "-output",
                output_base,
                "-preview",
                preview_png,
            ]
            if resume_path:
                cmd.extend(["-resume", resume_path])

            if log_callback:
                log_callback("[System] Spawning Go-OpenCL binary process...\n")
                log_callback(f"[System] Command: {subprocess.list2cmdline(cmd)}\n")

            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            env = os.environ.copy()
            path_val = env.get("PATH", "")
            clean_paths = []
            for item in path_val.split(os.pathsep):
                item_lower = item.lower()
                if (
                    ".venv" in item_lower
                    or "venv" in item_lower
                    or "python" in item_lower
                ):
                    continue
                clean_paths.append(item)
            env["PATH"] = os.pathsep.join(clean_paths)

            self.generator_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
                env=env,
            )

            progress_re = re.compile(r"\[(\d+)/(\d+)\]\s+(.*)")
            start_time = time.time()
            last_progress_update = 0.0

            for line in self.generator_proc.stdout:
                if self.cancel_flag:
                    break
                line_str = line.strip()
                if not line_str:
                    continue

                # Echo to sys.stdout
                sys.stdout.write(f"{line_str}\n")
                sys.stdout.flush()

                match = progress_re.match(line_str)
                if match:
                    curr = int(match.group(1))
                    total = int(match.group(2))
                    now = time.time()
                    elapsed = now - start_time
                    speed = curr / elapsed if elapsed > 0 else 0.0
                    eta = (layers - curr) / speed if speed > 0 else 0.0

                    if progress_callback:
                        progress_callback(curr, total, speed, eta)

                    if now - last_progress_update >= 0.05 or curr == total:
                        last_progress_update = now
                        try:
                            pattern = os.path.join(output_dir, "preview.*.png")
                            files = glob.glob(pattern)
                            if files:
                                num_re = re.compile(r"preview\.(\d+)\.png")
                                valid_files = []
                                for f in files:
                                    m = num_re.search(os.path.basename(f))
                                    if m:
                                        valid_files.append((int(m.group(1)), f))
                                if valid_files:
                                    valid_files.sort(key=lambda x: x[0])
                                    _, latest_file = valid_files[-1]
                                    with Image.open(latest_file) as pil_img:
                                        arr = np.array(
                                            pil_img.convert("RGB"),
                                            dtype=np.float32,
                                        )
                                        if preview_callback:
                                            preview_callback(arr)
                                    # Cleanup older intermediate files
                                    for num, f in valid_files[:-1]:
                                        try:
                                            os.unlink(f)
                                        except OSError:
                                            pass
                        except Exception:
                            pass

            self.generator_proc.stdout.close()
            if self.cancel_flag:
                self.kill_generator_process()
            else:
                self.generator_proc.wait()
                res = self.generator_proc.returncode

                # Copy final preview
                try:
                    pattern = os.path.join(output_dir, "preview.*.png")
                    files = glob.glob(pattern)
                    if files:
                        num_re = re.compile(r"preview\.(\d+)\.png")
                        valid_files = []
                        for f in files:
                            m = num_re.search(os.path.basename(f))
                            if m:
                                valid_files.append((int(m.group(1)), f))
                        if valid_files:
                            valid_files.sort(key=lambda x: x[0])
                            _, latest_file = valid_files[-1]
                            shutil.copy2(latest_file, preview_png)
                            for num, f in valid_files:
                                try:
                                    os.unlink(f)
                                except OSError:
                                    pass
                except Exception:
                    pass

                if res != 0:
                    if on_failed_callback:
                        on_failed_callback(
                            f"Go Generator process exited with non-zero code {res}."
                        )
                    return

                if on_success_callback:
                    on_success_callback()

        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            err_msg = f"{e}\n\n[Traceback]\n{tb}"
            if on_failed_callback:
                on_failed_callback(err_msg)
        finally:
            self.generator_proc = None
            if temp_resume_path and os.path.exists(temp_resume_path):
                try:
                    os.unlink(temp_resume_path)
                except OSError:
                    pass

    def stop_generator(self):
        self.cancel_flag = True
        self.kill_generator_process()

    def kill_generator_process(self):
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
