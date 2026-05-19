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
def _evaluate_candidate(cx, cy, rx, ry, theta, target, canvas, alpha_mask):
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
                if alpha_mask[py, px] > 0.5:
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
                if alpha_mask[py, px] > 0.5:
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
def _find_best_random_shape(samples, target, canvas, alpha_mask):
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
        delta, r, g, b = _evaluate_candidate(cx, cy, rx, ry, theta, target, canvas, alpha_mask)
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
def _find_best_mutated_shape(samples, base_cx, base_cy, base_rx, base_ry, base_theta, base_delta, base_r, base_g, base_b, target, canvas, alpha_mask):
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
        delta, r, g, b = _evaluate_candidate(cx, cy, rx, ry, theta, target, canvas, alpha_mask)
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
            pil_img = Image.open(img_path)
        except Exception as e:
            print(f'[Error] Failed to read target image: {e}')
            return False

        # Detect alpha channel
        has_alpha = pil_img.mode in ('RGBA', 'LA', 'PA')
        if has_alpha:
            pil_img = pil_img.convert('RGBA')
            # Check if the image actually has any transparent pixels
            alpha_data = pil_img.split()[3]
            if alpha_data.getextrema()[0] >= 250:
                # All pixels are essentially fully opaque — treat as RGB
                has_alpha = False
                pil_img = pil_img.convert('RGB')
                print('[Alpha] Image has RGBA format but is fully opaque. Using standard RGB mode.')
            else:
                print('[Alpha] Transparent background detected. Alpha-aware optimization enabled.')
        else:
            pil_img = pil_img.convert('RGB')

        orig_w, orig_h = pil_img.size
        max_dim = float(max(orig_w, orig_h))
        offset_x = (max_dim - orig_w) / 2.0
        offset_y = (max_dim - orig_h) / 2.0

        if has_alpha:
            # For RGBA: extract RGB and Alpha separately, pad with transparent black
            rgb_img = pil_img.convert('RGB')
            alpha_channel = pil_img.split()[3]  # Get alpha as grayscale

            # Pad RGB to square with black (doesn't matter, masked out)
            square_rgb = Image.new('RGB', (int(max_dim), int(max_dim)), (0, 0, 0))
            square_rgb.paste(rgb_img, (int(offset_x), int(offset_y)))

            # Pad Alpha to square with 0 (fully transparent)
            square_alpha = Image.new('L', (int(max_dim), int(max_dim)), 0)
            square_alpha.paste(alpha_channel, (int(offset_x), int(offset_y)))

            resized_rgb = square_rgb.resize((256, 256), Image.Resampling.LANCZOS)
            resized_alpha = square_alpha.resize((256, 256), Image.Resampling.LANCZOS)

            target = np.array(resized_rgb).astype(np.float32).transpose(2, 0, 1) / 255.0
            alpha_mask = np.array(resized_alpha).astype(np.float32) / 255.0

            # Compute mean color only over opaque pixels
            opaque_pixels = alpha_mask > 0.5
            opaque_count = np.sum(opaque_pixels)
            if opaque_count > 0:
                mean_r = np.sum(target[0] * opaque_pixels) / opaque_count
                mean_g = np.sum(target[1] * opaque_pixels) / opaque_count
                mean_b = np.sum(target[2] * opaque_pixels) / opaque_count
            else:
                mean_r = mean_g = mean_b = 0.0

            opaque_ratio = opaque_count / (256.0 * 256.0)
            print(f'[Alpha] Opaque pixel coverage: {opaque_ratio * 100.0:.1f}%')
        else:
            # Original RGB path
            mean_color = pil_img.resize((1, 1), Image.Resampling.LANCZOS).getpixel((0, 0))
            square_img = Image.new('RGB', (int(max_dim), int(max_dim)), mean_color)
            square_img.paste(pil_img, (int(offset_x), int(offset_y)))

            pil_img_resized = square_img.resize((256, 256), Image.Resampling.LANCZOS)
            target = np.array(pil_img_resized).astype(np.float32).transpose(2, 0, 1) / 255.0
            alpha_mask = np.ones((256, 256), dtype=np.float32)  # All opaque

            mean_r = np.mean(target[0])
            mean_g = np.mean(target[1])
            mean_b = np.mean(target[2])

        canvas = np.zeros_like(target)
        canvas[0, :, :] = mean_r
        canvas[1, :, :] = mean_g
        canvas[2, :, :] = mean_b

        # Background shape: only emit for opaque images
        if has_alpha:
            shapes_json_bg = None
            print('[Alpha] No background layer will be generated (transparent mode).')
        else:
            shapes_json_bg = {'type': 1, 'data': [0.0, 0.0, float(orig_w), float(orig_h)], 'color': [int(mean_r * 255.0), int(mean_g * 255.0), int(mean_b * 255.0), 0]}

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
            delta, cx, cy, rx, ry, theta, r, g, b = _find_best_random_shape(self.random_samples, target, canvas, alpha_mask)
            if delta < 0.0:
                delta, cx, cy, rx, ry, theta, r, g, b = _find_best_mutated_shape(self.mutated_samples, cx, cy, rx, ry, theta, delta, r, g, b, target, canvas, alpha_mask)
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
                    if has_alpha:
                        # Render checkerboard behind transparent areas for preview
                        checker = np.zeros((256, 256, 3), dtype=np.uint8)
                        for cy_c in range(256):
                            for cx_c in range(256):
                                if ((cy_c // 8) + (cx_c // 8)) % 2 == 0:
                                    checker[cy_c, cx_c] = [200, 200, 200]
                                else:
                                    checker[cy_c, cx_c] = [150, 150, 150]
                        alpha_3d = alpha_mask[:, :, np.newaxis]
                        display_img = (display_img.astype(np.float32) * alpha_3d + checker.astype(np.float32) * (1.0 - alpha_3d)).astype(np.uint8)
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
        shapes_json = []
        if shapes_json_bg is not None:
            shapes_json.append(shapes_json_bg)
        for s in active_shapes:
            cx, cy, rx, ry, theta, r, g, b = s
            x_json = float((cx + 1.0) / 2.0 * max_dim - offset_x)
            y_json = float((cy + 1.0) / 2.0 * max_dim - offset_y)
            sx_json = float(rx * max_dim)
            sy_json = float(ry * max_dim)
            rot_json = float(theta * 180.0 / math.pi % 360.0)
            if rot_json < 0.0:
                rot_json += 360.0
            col_r = max(0, min(255, int(r * 255.0)))
            col_g = max(0, min(255, int(g * 255.0)))
            col_b = max(0, min(255, int(b * 255.0)))
            shapes_json.append({'type': 16, 'data': [x_json, y_json, sx_json, sy_json, rot_json], 'color': [col_r, col_g, col_b, 255]})
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