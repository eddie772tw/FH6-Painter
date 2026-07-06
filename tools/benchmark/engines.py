#!/usr/bin/env python3
"""引擎端到端執行邏輯 — Python 引擎 (Numba/Taichi) 與 Go-OpenCL 引擎。"""

import os
import time

import numpy as np
from PIL import Image

try:
    import taichi as ti

    HAS_TAICHI = True
except ImportError:
    HAS_TAICHI = False

from benchmark.config import TARGET_SHAPES_COUNT


def run_python_engine_benchmark(
    evaluator, target_img, alpha_mask, batch_size, params, warmup=False, duration=60.0
):
    """執行 Numba / Taichi 引擎的端到端效能測試。"""
    h, w, c = target_img.shape

    # 影像填滿背景色邏輯
    target_work = target_img.copy()
    if alpha_mask is not None:
        fg_mask = alpha_mask > 127.0
        avg_r = np.mean(target_work[fg_mask, 0]) if np.any(fg_mask) else 128.0
        avg_g = np.mean(target_work[fg_mask, 1]) if np.any(fg_mask) else 128.0
        avg_b = np.mean(target_work[fg_mask, 2]) if np.any(fg_mask) else 128.0
        bg_mask = ~fg_mask
        target_work[bg_mask, 0] = avg_r
        target_work[bg_mask, 1] = avg_g
        target_work[bg_mask, 2] = avg_b
    else:
        avg_r = np.mean(target_work[:, :, 0])
        avg_g = np.mean(target_work[:, :, 1])
        avg_b = np.mean(target_work[:, :, 2])

    t_start = time.perf_counter()
    shapes_processed = 0
    final_mse = 999999.0

    if warmup:
        # 預熱僅跑 5 個 shape
        canvas = np.zeros_like(target_work)
        canvas[:, :, 0] = avg_r
        canvas[:, :, 1] = avg_g
        canvas[:, :, 2] = avg_b

        uncovered_map = evaluator.init_uncovered_map(w, h, alpha_mask is not None, 5.0)
        params_run = params.copy()
        params_run["uncovered_map"] = uncovered_map

        for _ in range(5):
            best_shape, _ = evaluator.search_best_shape(canvas, batch_size, params_run)
            x_c, y_c, r_x, r_y, theta, r, g, b, alpha = best_shape
            evaluator.draw_shape_on_canvas(
                canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha
            )
            evaluator.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta)
            if HAS_TAICHI:
                ti.sync()
        return 5, time.perf_counter() - t_start, 0.0

    # 正式測試
    elapsed = 0.0
    while elapsed < duration:
        canvas = np.zeros_like(target_work)
        canvas[:, :, 0] = avg_r
        canvas[:, :, 1] = avg_g
        canvas[:, :, 2] = avg_b

        uncovered_map = evaluator.init_uncovered_map(w, h, alpha_mask is not None, 5.0)
        params_run = params.copy()
        params_run["uncovered_map"] = uncovered_map

        aborted = False
        for _ in range(TARGET_SHAPES_COUNT):
            if time.perf_counter() - t_start >= duration:
                aborted = True
                break
            best_shape, _ = evaluator.search_best_shape(canvas, batch_size, params_run)
            x_c, y_c, r_x, r_y, theta, r, g, b, alpha = best_shape
            evaluator.draw_shape_on_canvas(
                canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha
            )
            evaluator.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta)
            if HAS_TAICHI:
                ti.sync()
            shapes_processed += 1

        elapsed = time.perf_counter() - t_start
        if not aborted:
            final_mse = np.mean((canvas - target_work) ** 2)

    return shapes_processed, elapsed, final_mse


def run_go_engine_benchmark(
    evaluator,
    target_img,
    alpha_mask,
    profile_path,
    project_root,
    warmup=False,
    duration=60.0,
):
    """執行 Go-OpenCL 引擎的端到端效能測試。"""
    h, w, c = target_img.shape

    # 建立臨時目錄
    temp_dir = os.path.join(project_root, "tools", "bin")
    os.makedirs(temp_dir, exist_ok=True)

    # 動態產生臨時的 ini 檔案，設定 stopAt = TARGET_SHAPES_COUNT
    temp_ini_path = os.path.join(temp_dir, "temp_profile.ini")
    ini_lines = []
    if profile_path and os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("stopAt"):
                    ini_lines.append(f"stopAt = {TARGET_SHAPES_COUNT}\n")
                else:
                    ini_lines.append(line)
    else:
        ini_lines.append(f"stopAt = {TARGET_SHAPES_COUNT}\n")
    with open(temp_ini_path, "w", encoding="utf-8") as f:
        f.writelines(ini_lines)

    # 將 NumPy 陣列儲存成臨時 PNG 圖片
    temp_img_path = os.path.join(temp_dir, "temp_target.png")
    if alpha_mask is not None:
        rgba = np.zeros((h, w, 4), dtype=np.float32)
        rgba[:, :, :3] = target_img
        rgba[:, :, 3] = alpha_mask
        pil_img = Image.fromarray(np.clip(rgba, 0.0, 255.0).astype(np.uint8), "RGBA")
    else:
        pil_img = Image.fromarray(
            np.clip(target_img, 0.0, 255.0).astype(np.uint8), "RGB"
        )
    pil_img.save(temp_img_path)

    t_start = time.perf_counter()
    shapes_processed = 0
    final_mse = 999999.0

    if warmup:
        temp_json_path = os.path.join(temp_dir, "temp_out.json")
        evaluator.run_generator(
            img_path=temp_img_path,
            output_json=temp_json_path,
            profile_path=temp_ini_path,
            layers=TARGET_SHAPES_COUNT,
        )
        return TARGET_SHAPES_COUNT, time.perf_counter() - t_start, 0.0

    # 正式測試
    elapsed = 0.0
    while elapsed < duration:
        temp_json_path = os.path.join(temp_dir, "temp_out.json")
        preview_png = os.path.join(temp_dir, "preview.png")
        if os.path.exists(preview_png):
            try:
                os.unlink(preview_png)
            except Exception:
                pass

        evaluator.run_generator(
            img_path=temp_img_path,
            output_json=temp_json_path,
            profile_path=temp_ini_path,
            layers=TARGET_SHAPES_COUNT,
        )

        shapes_processed += TARGET_SHAPES_COUNT
        elapsed = time.perf_counter() - t_start

        # 讀取 final preview 圖片做正確性驗證
        if os.path.exists(preview_png):
            try:
                with Image.open(preview_png) as pil_prev:
                    prev_arr = np.array(pil_prev.convert("RGB"), dtype=np.float32)
                    if prev_arr.shape[:2] != target_img.shape[:2]:
                        pil_prev_resized = pil_prev.resize(
                            (w, h), Image.Resampling.LANCZOS
                        )
                        prev_arr = np.array(
                            pil_prev_resized.convert("RGB"), dtype=np.float32
                        )
                    final_mse = np.mean((prev_arr - target_img) ** 2)
            except Exception as e:
                print(f"      [Warning] Failed to calculate Go-OpenCL final MSE: {e}")

    # 清除臨時檔案
    for path in [
        temp_ini_path,
        temp_img_path,
        os.path.join(temp_dir, "temp_out.json"),
        os.path.join(temp_dir, "temp_out.json.json"),
    ]:
        if os.path.exists(path):
            try:
                os.unlink(path)
            except Exception:
                pass

    return shapes_processed, elapsed, final_mse
