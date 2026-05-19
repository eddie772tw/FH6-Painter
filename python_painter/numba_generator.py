import os
import sys
import time
import math
import json
from typing import Dict, Any, List
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.dirname(current_dir))
import numpy as np
from PIL import Image
import cv2
try:
    from numba import njit, prange
except ImportError:
    print('[Error] Numba is not installed. Please run: pip install numba')
    sys.exit(1)

@njit(fastmath=True)
def _evaluate_candidate(cx, cy, rx, ry, theta, target, canvas):
    grid_min = -1.0
    pixel_size = 2.0 / 256.0
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    half_w = np.sqrt((rx * cos_t) ** 2 + (ry * sin_t) ** 2)
    half_h = np.sqrt((rx * sin_t) ** 2 + (ry * cos_t) ** 2)
    min_px = int((cx - half_w - grid_min) / pixel_size)
    max_px = int((cx + half_w - grid_min) / pixel_size)
    min_py = int((cy - half_h - grid_min) / pixel_size)
    max_py = int((cy + half_h - grid_min) / pixel_size)
    min_px = max(0, min(255, min_px))
    max_px = max(0, min(255, max_px))
    min_py = max(0, min(255, min_py))
    max_py = max(0, min(255, max_py))
    inv_rx_sq = 1.0 / (rx * rx)
    inv_ry_sq = 1.0 / (ry * ry)
    sum_r = 0.0
    sum_g = 0.0
    sum_b = 0.0
    count = 0
    for py in range(min_py, max_py + 1):
        y_val = grid_min + py * pixel_size
        dy = y_val - cy
        for px in range(min_px, max_px + 1):
            x_val = grid_min + px * pixel_size
            dx = x_val - cx
            xp = dx * cos_t + dy * sin_t
            yp = -dx * sin_t + dy * cos_t
            if xp * xp * inv_rx_sq + yp * yp * inv_ry_sq <= 1.0:
                sum_r += target[0, py, px]
                sum_g += target[1, py, px]
                sum_b += target[2, py, px]
                count += 1
    if count == 0:
        return (0.0, 0.0, 0.0, 0.0)
    opt_r = sum_r / count
    opt_g = sum_g / count
    opt_b = sum_b / count
    delta_error = 0.0
    for py in range(min_py, max_py + 1):
        y_val = grid_min + py * pixel_size
        dy = y_val - cy
        for px in range(min_px, max_px + 1):
            x_val = grid_min + px * pixel_size
            dx = x_val - cx
            xp = dx * cos_t + dy * sin_t
            yp = -dx * sin_t + dy * cos_t
            if xp * xp * inv_rx_sq + yp * yp * inv_ry_sq <= 1.0:
                old_r = canvas[0, py, px]
                old_g = canvas[1, py, px]
                old_b = canvas[2, py, px]
                tr = target[0, py, px]
                tg = target[1, py, px]
                tb = target[2, py, px]
                old_err = (old_r - tr) ** 2 + (old_g - tg) ** 2 + (old_b - tb) ** 2
                new_err = (opt_r - tr) ** 2 + (opt_g - tg) ** 2 + (opt_b - tb) ** 2
                delta_error += new_err - old_err
    return (delta_error, opt_r, opt_g, opt_b)

@njit(fastmath=True, parallel=True)
def _find_best_random_shape(samples, target, canvas):
    deltas = np.zeros(samples, dtype=np.float32)
    cxs = np.zeros(samples, dtype=np.float32)
    cys = np.zeros(samples, dtype=np.float32)
    rxs = np.zeros(samples, dtype=np.float32)
    rys = np.zeros(samples, dtype=np.float32)
    thetas = np.zeros(samples, dtype=np.float32)
    rs = np.zeros(samples, dtype=np.float32)
    gs = np.zeros(samples, dtype=np.float32)
    bs = np.zeros(samples, dtype=np.float32)
    for i in prange(samples):
        cx = np.random.rand() * 2.0 - 1.0
        cy = np.random.rand() * 2.0 - 1.0
        rx = np.random.rand() * 0.4 + 0.005
        ry = np.random.rand() * 0.4 + 0.005
        theta = np.random.rand() * 2.0 * np.pi
        delta, r, g, b = _evaluate_candidate(cx, cy, rx, ry, theta, target, canvas)
        deltas[i] = delta
        cxs[i] = cx
        cys[i] = cy
        rxs[i] = rx
        rys[i] = ry
        thetas[i] = theta
        rs[i] = r
        gs[i] = g
        bs[i] = b
    best_idx = np.argmin(deltas)
    return (deltas[best_idx], cxs[best_idx], cys[best_idx], rxs[best_idx], rys[best_idx], thetas[best_idx], rs[best_idx], gs[best_idx], bs[best_idx])

@njit(fastmath=True, parallel=True)
def _find_best_mutated_shape(samples, base_cx, base_cy, base_rx, base_ry, base_theta, base_delta, base_r, base_g, base_b, target, canvas):
    deltas = np.zeros(samples, dtype=np.float32)
    cxs = np.zeros(samples, dtype=np.float32)
    cys = np.zeros(samples, dtype=np.float32)
    rxs = np.zeros(samples, dtype=np.float32)
    rys = np.zeros(samples, dtype=np.float32)
    thetas = np.zeros(samples, dtype=np.float32)
    rs = np.zeros(samples, dtype=np.float32)
    gs = np.zeros(samples, dtype=np.float32)
    bs = np.zeros(samples, dtype=np.float32)
    mutate_rate = 0.08
    for i in prange(samples):
        cx = base_cx + np.random.randn() * mutate_rate
        cy = base_cy + np.random.randn() * mutate_rate
        rx = base_rx + np.random.randn() * mutate_rate
        ry = base_ry + np.random.randn() * mutate_rate
        theta = base_theta + np.random.randn() * mutate_rate
        cx = max(-1.0, min(1.0, cx))
        cy = max(-1.0, min(1.0, cy))
        rx = max(0.001, min(1.0, rx))
        ry = max(0.001, min(1.0, ry))
        delta, r, g, b = _evaluate_candidate(cx, cy, rx, ry, theta, target, canvas)
        deltas[i] = delta
        cxs[i] = cx
        cys[i] = cy
        rxs[i] = rx
        rys[i] = ry
        thetas[i] = theta
        rs[i] = r
        gs[i] = g
        bs[i] = b
    best_idx = np.argmin(deltas)
    if deltas[best_idx] < base_delta:
        return (deltas[best_idx], cxs[best_idx], cys[best_idx], rxs[best_idx], rys[best_idx], thetas[best_idx], rs[best_idx], gs[best_idx], bs[best_idx])
    return (base_delta, base_cx, base_cy, base_rx, base_ry, base_theta, base_r, base_g, base_b)

@njit(fastmath=True)
def _draw_shape_to_canvas(cx, cy, rx, ry, theta, r, g, b, canvas):
    grid_min = -1.0
    pixel_size = 2.0 / 256.0
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    half_w = np.sqrt((rx * cos_t) ** 2 + (ry * sin_t) ** 2)
    half_h = np.sqrt((rx * sin_t) ** 2 + (ry * cos_t) ** 2)
    min_px = int((cx - half_w - grid_min) / pixel_size)
    max_px = int((cx + half_w - grid_min) / pixel_size)
    min_py = int((cy - half_h - grid_min) / pixel_size)
    max_py = int((cy + half_h - grid_min) / pixel_size)
    min_px = max(0, min(255, min_px))
    max_px = max(0, min(255, max_px))
    min_py = max(0, min(255, min_py))
    max_py = max(0, min(255, max_py))
    inv_rx_sq = 1.0 / (rx * rx)
    inv_ry_sq = 1.0 / (ry * ry)
    for py in range(min_py, max_py + 1):
        y_val = grid_min + py * pixel_size
        dy = y_val - cy
        for px in range(min_px, max_px + 1):
            x_val = grid_min + px * pixel_size
            dx = x_val - cx
            xp = dx * cos_t + dy * sin_t
            yp = -dx * sin_t + dy * cos_t
            if xp * xp * inv_rx_sq + yp * yp * inv_ry_sq <= 1.0:
                canvas[0, py, px] = r
                canvas[1, py, px] = g
                canvas[2, py, px] = b

@njit(fastmath=True)
def _find_redundant_shapes(cxs, cys, rxs, rys, thetas):
    num_shapes = len(cxs)
    visibility_map = np.full((256, 256), -1, dtype=np.int32)
    grid_min = -1.0
    pixel_size = 2.0 / 256.0
    for i in range(num_shapes):
        cx = cxs[i]
        cy = cys[i]
        rx = rxs[i]
        ry = rys[i]
        theta = thetas[i]
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        half_w = np.sqrt((rx * cos_t) ** 2 + (ry * sin_t) ** 2)
        half_h = np.sqrt((rx * sin_t) ** 2 + (ry * cos_t) ** 2)
        min_x = cx - half_w
        max_x = cx + half_w
        min_y = cy - half_h
        max_y = cy + half_h
        min_px = int((min_x - grid_min) / pixel_size)
        max_px = int((max_x - grid_min) / pixel_size)
        min_py = int((min_y - grid_min) / pixel_size)
        max_py = int((max_y - grid_min) / pixel_size)
        min_px = max(0, min(255, min_px))
        max_px = max(0, min(255, max_px))
        min_py = max(0, min(255, min_py))
        max_py = max(0, min(255, max_py))
        inv_rx_sq = 1.0 / (rx * rx)
        inv_ry_sq = 1.0 / (ry * ry)
        for py in range(min_py, max_py + 1):
            y_val = grid_min + py * pixel_size
            dy = y_val - cy
            for px in range(min_px, max_px + 1):
                x_val = grid_min + px * pixel_size
                dx = x_val - cx
                xp = dx * cos_t + dy * sin_t
                yp = -dx * sin_t + dy * cos_t
                if xp * xp * inv_rx_sq + yp * yp * inv_ry_sq <= 1.0:
                    visibility_map[py, px] = i
    visible_counts = np.zeros(num_shapes, dtype=np.int32)
    for py in range(256):
        for px in range(256):
            shape_idx = visibility_map[py, px]
            if shape_idx >= 0:
                visible_counts[shape_idx] += 1
    redundant = np.zeros(num_shapes, dtype=np.bool_)
    for i in range(num_shapes):
        if visible_counts[i] < 2:
            redundant[i] = True
    return redundant

class NumbaImageGenerator:

    def __init__(self, random_samples: int, mutated_samples: int):
        self.random_samples = random_samples
        self.mutated_samples = mutated_samples

    def optimize_image(self, img_path: str, target_layers: int, output_json: str) -> bool:
        print('\n' + '=' * 80)
        print('    FORZA PAINTER ULTRA-PERFORMANCE NUMBA MULTI-THREAD CPU SOLVER ACTIVE')
        print('=' * 80)
        try:
            pil_img = Image.open(img_path).convert('RGB')
        except Exception as e:
            print(f'[Error] Failed to read target image: {e}')
            return False
        pil_img_resized = pil_img.resize((256, 256), Image.Resampling.LANCZOS)
        target = np.array(pil_img_resized).astype(np.float32).transpose(2, 0, 1) / 255.0
        mean_r = np.mean(target[0])
        mean_g = np.mean(target[1])
        mean_b = np.mean(target[2])
        canvas = np.zeros_like(target)
        canvas[0, :, :] = mean_r
        canvas[1, :, :] = mean_g
        canvas[2, :, :] = mean_b
        shapes_json_bg = {'type': 1, 'data': [0.0, 0.0, 3000.0, 3000.0], 'color': [int(mean_r * 255.0), int(mean_g * 255.0), int(mean_b * 255.0), 0]}
        print(f'Target layers to solve: {target_layers} ellipses')
        print(f'Optimization pipeline: {self.random_samples} random / {self.mutated_samples} mutations per shape')
        print('Compiling LLVM JIT Multi-Thread kernels and Solving...')
        try:
            cv2.namedWindow('Forza Painter - Numba Engine', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Forza Painter - Numba Engine', 512, 512)
        except Exception as e:
            print(f'[Warning] Failed to initialize preview window: {e}')
        start_time = time.perf_counter()
        active_shapes = []
        total_generated = 0
        last_redundancy_check = 0
        while len(active_shapes) < target_layers:
            delta, cx, cy, rx, ry, theta, r, g, b = _find_best_random_shape(self.random_samples, target, canvas)
            if delta < 0.0:
                delta, cx, cy, rx, ry, theta, r, g, b = _find_best_mutated_shape(self.mutated_samples, cx, cy, rx, ry, theta, delta, r, g, b, target, canvas)
            if delta < 0.0:
                _draw_shape_to_canvas(cx, cy, rx, ry, theta, r, g, b, canvas)
                active_shapes.append((cx, cy, rx, ry, theta, r, g, b))
            total_generated += 1
            if len(active_shapes) >= 500 and len(active_shapes) % 500 == 0 and (len(active_shapes) != last_redundancy_check):
                last_redundancy_check = len(active_shapes)
                cxs = np.array([s[0] for s in active_shapes], dtype=np.float32)
                cys = np.array([s[1] for s in active_shapes], dtype=np.float32)
                rxs = np.array([s[2] for s in active_shapes], dtype=np.float32)
                rys = np.array([s[3] for s in active_shapes], dtype=np.float32)
                thetas = np.array([s[4] for s in active_shapes], dtype=np.float32)
                redundant_mask = _find_redundant_shapes(cxs, cys, rxs, rys, thetas)
                num_redundant = np.sum(redundant_mask)
                if num_redundant > 0:
                    new_active = []
                    for i in range(len(redundant_mask)):
                        if not redundant_mask[i]:
                            new_active.append(active_shapes[i])
                    print(f'  [Optimization] Found and eliminated {num_redundant} completely covered shapes. Recovered {num_redundant} free slots for more detail!')
                    active_shapes = new_active
            if len(active_shapes) % 10 == 0 or len(active_shapes) == target_layers:
                try:
                    display_img = (np.clip(canvas.transpose(1, 2, 0), 0.0, 1.0) * 255.0).astype(np.uint8)
                    display_img = cv2.cvtColor(display_img, cv2.COLOR_RGB2BGR)
                    cv2.imshow('Forza Painter - Numba Engine', display_img)
                    key = cv2.waitKey(1) & 255
                    if key == 27 or key == ord('q'):
                        print('\n[User Abort] Esc/Q pressed. Stopping early and saving current progress...')
                        break
                    if cv2.getWindowProperty('Forza Painter - Numba Engine', cv2.WND_PROP_VISIBLE) < 1:
                        print('\n[User Abort] Window closed. Stopping early and saving current progress...')
                        break
                except Exception:
                    pass
            if len(active_shapes) % 50 == 0 or len(active_shapes) == target_layers:
                progress = len(active_shapes) / target_layers * 100.0
                print(f'  [Progress] Shape {len(active_shapes):04d}/{target_layers:04d} active ({progress:.1f}%) | Delta L2 Improvement: {delta:+.6f}')
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        print(f'\n[Complete] Successfully generated {total_generated} candidates (filtered to strictly the best {target_layers}) in {elapsed:.2f} seconds!')
        print(f'Solving Speed: {total_generated / elapsed:.2f} shape evaluations per second.')
        shapes_json = [shapes_json_bg]
        for s in active_shapes:
            cx, cy, rx, ry, theta, r, g, b = s
            x_json = float((cx + 1.0) / 2.0 * 2000.0)
            y_json = float((cy + 1.0) / 2.0 * 2000.0)
            sx_json = float(rx * 2000.0)
            sy_json = float(ry * 2000.0)
            rot_json = float(theta * 180.0 / math.pi % 360.0)
            if rot_json < 0.0:
                rot_json += 360.0
            col_r = max(0, min(255, int(r * 255.0)))
            col_g = max(0, min(255, int(g * 255.0)))
            col_b = max(0, min(255, int(b * 255.0)))
            shapes_json.append({'type': 102, 'data': [x_json, y_json, sx_json, sy_json, rot_json], 'color': [col_r, col_g, col_b, 255]})
        output_root = {'shapes': shapes_json}
        try:
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump(output_root, f, indent=4)
            print(f'[Exporter] Successfully exported vector layers to: {output_json}')
            try:
                cv2.destroyAllWindows()
            except:
                pass
            return True
        except Exception as e:
            print(f'[Error] Failed to write output JSON: {e}')
            try:
                cv2.destroyAllWindows()
            except:
                pass
            return False