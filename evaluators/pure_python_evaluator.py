#!/usr/bin/env python3
import math
import numpy as np
from evaluators.base_evaluator import BaseEvaluator

def evaluate_candidate_py(target, canvas, x_c, y_c, r_x, r_y, theta, alpha, alpha_mask, check_contour, use_freeze=False, freeze_mask=None, use_weight=False, weight_map=None, use_uncovered=False, uncovered_map=None):
    """Pure Python version of evaluate_candidate."""
    height = target.shape[0]
    width = target.shape[1]
    
    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))
    
    x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    if (x_c - x_half < 0.0) or (x_c + x_half > np.float32(width)) or (y_c - y_half < 0.0) or (y_c + y_half > np.float32(height)):
        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
        
    min_x = max(0, int(x_c - x_half))
    max_x = min(width - 1, int(x_c + x_half))
    min_y = max(0, int(y_c - y_half))
    max_y = min(height - 1, int(y_c + y_half))
    
    inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
    inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
    
    count = 0
    sum_t_r = np.float32(0.0)
    sum_t_g = np.float32(0.0)
    sum_t_b = np.float32(0.0)
    
    sum_c_r = np.float32(0.0)
    sum_c_g = np.float32(0.0)
    sum_c_b = np.float32(0.0)
    
    sum_c2_r = np.float32(0.0)
    sum_c2_g = np.float32(0.0)
    sum_c2_b = np.float32(0.0)
    
    sum_ct_r = np.float32(0.0)
    sum_ct_g = np.float32(0.0)
    sum_ct_b = np.float32(0.0)
    
    for y in range(min_y, max_y + 1):
        dy = np.float32(y - y_c)
        dx_start = np.float32(min_x - x_c)
        rx = dx_start * cos_t + dy * sin_t
        ry = -dx_start * sin_t + dy * cos_t
        
        for x in range(min_x, max_x + 1):
            if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
                if check_contour:
                    if alpha_mask[y, x] <= 10.0:
                        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
                
                if use_freeze and freeze_mask[y, x] == 1:
                    return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
                        
                t_r = target[y, x, 0]
                t_g = target[y, x, 1]
                t_b = target[y, x, 2]
                
                c_r = canvas[y, x, 0]
                c_g = canvas[y, x, 1]
                c_b = canvas[y, x, 2]
                
                w = np.float32(1.0)
                if use_weight:
                    w = weight_map[y, x]
                if use_uncovered:
                    w = w * uncovered_map[y, x]
                
                count += w
                sum_t_r += t_r * w
                sum_t_g += t_g * w
                sum_t_b += t_b * w
                
                sum_c_r += c_r * w
                sum_c_g += c_g * w
                sum_c_b += c_b * w
                
                sum_c2_r += (c_r * c_r) * w
                sum_c2_g += (c_g * c_g) * w
                sum_c2_b += (c_b * c_b) * w
                
                sum_ct_r += (c_r * t_r) * w
                sum_ct_g += (c_g * t_g) * w
                sum_ct_b += (c_b * t_b) * w
                
            rx += cos_t
            ry -= sin_t
            
    if count == 0:
        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
        
    avg_r = sum_t_r / count
    avg_g = sum_t_g / count
    avg_b = sum_t_b / count
    
    a_f = np.float32(alpha / 255.0)
    a2_minus_2a = np.float32(a_f * a_f - 2.0 * a_f)
    two_a = np.float32(2.0 * a_f)
    two_a_one_minus_a = np.float32(2.0 * a_f * (1.0 - a_f))
    
    delta_r = a2_minus_2a * sum_c2_r + two_a * sum_ct_r + two_a_one_minus_a * avg_r * sum_c_r + a2_minus_2a * avg_r * sum_t_r
    delta_g = a2_minus_2a * sum_c2_g + two_a * sum_ct_g + two_a_one_minus_a * avg_g * sum_c_g + a2_minus_2a * avg_g * sum_t_g
    delta_b = a2_minus_2a * sum_c2_b + two_a * sum_ct_b + two_a_one_minus_a * avg_b * sum_c_b + a2_minus_2a * avg_b * sum_t_b
    
    total_delta_mse = delta_r + delta_g + delta_b
    
    return avg_r, avg_g, avg_b, total_delta_mse

def draw_ellipse_py(canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha):
    """Pure Python version of draw_ellipse."""
    height = canvas.shape[0]
    width = canvas.shape[1]
    
    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))
    
    x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    min_x = max(0, int(x_c - x_half))
    max_x = min(width - 1, int(x_c + x_half))
    min_y = max(0, int(y_c - y_half))
    max_y = min(height - 1, int(y_c + y_half))
    
    inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
    inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
    
    a_f = np.float32(alpha / 255.0)
    one_minus_a = np.float32(1.0 - a_f)
    
    r_val = np.float32(r)
    g_val = np.float32(g)
    b_val = np.float32(b)
    
    for y in range(min_y, max_y + 1):
        dy = np.float32(y - y_c)
        dx_start = np.float32(min_x - x_c)
        rx = dx_start * cos_t + dy * sin_t
        ry = -dx_start * sin_t + dy * cos_t
        
        for x in range(min_x, max_x + 1):
            if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
                canvas[y, x, 0] = canvas[y, x, 0] * one_minus_a + r_val * a_f
                canvas[y, x, 1] = canvas[y, x, 1] * one_minus_a + g_val * a_f
                canvas[y, x, 2] = canvas[y, x, 2] * one_minus_a + b_val * a_f
                if canvas.shape[2] == 4:
                    canvas[y, x, 3] = canvas[y, x, 3] * one_minus_a + np.float32(alpha)
            
            rx += cos_t
            ry -= sin_t


class PurePythonEvaluator(BaseEvaluator):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None):
        super().__init__(target_image, alpha_mask)

    def get_name(self) -> str:
        return "Pure Python (Baseline)"

    def is_available(self) -> bool:
        return True

    def get_device_type(self) -> str:
        return "CPU"

    def search_best_shape(self, current_canvas: np.ndarray, batch_size: int, params: dict) -> tuple:
        height, width, _ = self.target_image.shape
        max_r = max(10.0, min(width, height) / 3.0)
        current_max_r = params.get("current_max_r")
        if current_max_r is not None:
            max_r = min(max_r, current_max_r)
            
        alpha_mask = self.alpha_mask
        check_contour = params.get("check_contour", False)
        if alpha_mask is None or alpha_mask.shape == (1, 1):
            check_contour = False
            if alpha_mask is None:
                alpha_mask = np.zeros((1, 1), dtype=np.float32)
                
        error_prob = params.get("error_prob")
        if error_prob is None:
            error_prob = np.zeros((1, 1), dtype=np.float32)
            
        freeze_mask = params.get("freeze_mask")
        if freeze_mask is None:
            freeze_mask = np.zeros((1, 1), dtype=np.uint8)
            
        weight_map = params.get("weight_map")
        if weight_map is None:
            weight_map = np.ones((1, 1), dtype=np.float32)
            
        uncovered_map = params.get("uncovered_map")
        if uncovered_map is None:
            uncovered_map = np.ones((1, 1), dtype=np.float32)

        # 1. Serial/Normal Random Search in Pure Python
        use_importance = params.get("use_importance", False)
        if use_importance and error_prob.shape[0] > 1:
            x_c_arr = np.zeros(batch_size, dtype=np.float32)
            y_c_arr = np.zeros(batch_size, dtype=np.float32)
            for i in range(batch_size):
                keep = False
                for att in range(100):
                    x = np.float32(np.random.uniform(0.0, float(width)))
                    y = np.float32(np.random.uniform(0.0, float(height)))
                    ix = int(x)
                    iy = int(y)
                    if ix >= 0 and ix < width and iy >= 0 and iy < height:
                        prob = error_prob[iy, ix]
                        if np.random.uniform(0.0, 1.0) < prob:
                            x_c_arr[i] = x
                            y_c_arr[i] = y
                            keep = True
                            break
                if not keep:
                    x_c_arr[i] = np.float32(np.random.uniform(0.0, float(width)))
                    y_c_arr[i] = np.float32(np.random.uniform(0.0, float(height)))
        else:
            x_c_arr = np.random.uniform(0.0, float(width), batch_size).astype(np.float32)
            y_c_arr = np.random.uniform(0.0, float(height), batch_size).astype(np.float32)
            
        r_x_arr = np.random.uniform(2.0, max_r, batch_size).astype(np.float32)
        r_y_arr = np.random.uniform(2.0, max_r, batch_size).astype(np.float32)
        theta_arr = np.random.uniform(0.0, 2.0 * math.pi, batch_size).astype(np.float32)
        alpha_arr = np.full(batch_size, 255.0, dtype=np.float32)
        
        deltas = np.zeros(batch_size, dtype=np.float32)
        colors = np.zeros((batch_size, 3), dtype=np.float32)
        
        for i in range(batch_size):
            r, g, b, delta = evaluate_candidate_py(
                self.target_image, current_canvas, 
                x_c_arr[i], y_c_arr[i], 
                r_x_arr[i], r_y_arr[i], 
                theta_arr[i], int(alpha_arr[i]),
                alpha_mask, check_contour,
                params.get("use_freeze", False), freeze_mask,
                params.get("use_weight", False), weight_map,
                params.get("use_uncovered", False), uncovered_map
            )
            deltas[i] = np.float32(delta)
            colors[i, 0] = np.float32(r)
            colors[i, 1] = np.float32(g)
            colors[i, 2] = np.float32(b)
            
        best_idx = np.argmin(deltas)
        x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = (
            x_c_arr[best_idx], y_c_arr[best_idx], 
            r_x_arr[best_idx], r_y_arr[best_idx], 
            theta_arr[best_idx], int(alpha_arr[best_idx]),
            colors[best_idx, 0], colors[best_idx, 1], colors[best_idx, 2],
            deltas[best_idx]
        )
        
        # Fallback active
        fallback_active = False
        if params.get("use_freeze", False) and delta >= 90000000.0:
            fallback_active = True
            for i in range(batch_size):
                r, g, b, delta = evaluate_candidate_py(
                    self.target_image, current_canvas, 
                    x_c_arr[i], y_c_arr[i], 
                    r_x_arr[i], r_y_arr[i], 
                    theta_arr[i], int(alpha_arr[i]),
                    alpha_mask, check_contour,
                    False, freeze_mask,
                    params.get("use_weight", False), weight_map,
                    params.get("use_uncovered", False), uncovered_map
                )
                deltas[i] = np.float32(delta)
                colors[i, 0] = np.float32(r)
                colors[i, 1] = np.float32(g)
                colors[i, 2] = np.float32(b)
            best_idx = np.argmin(deltas)
            x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = (
                x_c_arr[best_idx], y_c_arr[best_idx], 
                r_x_arr[best_idx], r_y_arr[best_idx], 
                theta_arr[best_idx], int(alpha_arr[best_idx]),
                colors[best_idx, 0], colors[best_idx, 1], colors[best_idx, 2],
                deltas[best_idx]
            )
            
        # 2. Local Serial Hill-Climbing Optimization Phase in Pure Python
        hill_climb_freeze = params.get("use_freeze", False) if not fallback_active else False
        
        curr_x_c = np.float32(x_c)
        curr_y_c = np.float32(y_c)
        curr_r_x = np.float32(r_x)
        curr_r_y = np.float32(r_y)
        curr_theta = np.float32(theta)
        curr_alpha = int(alpha)
        curr_r = np.float32(r)
        curr_g = np.float32(g)
        curr_b = np.float32(b)
        curr_delta = np.float32(delta)
        
        T = np.float32(params.get("sa_initial_temp", 5000.0))
        c_rate = np.float32(params.get("sa_cooling_rate", 0.95))
        max_r_f = np.float32(max_r)
        sa_enabled = params.get("sa_enabled", False)
        optimization_steps = params.get("optimization_steps", 50)
        
        for step in range(optimization_steps):
            scale = np.float32(1.0 - (step / optimization_steps))
            
            nx_c = curr_x_c + np.float32(np.random.normal(0.0, 8.0 * scale))
            ny_c = curr_y_c + np.float32(np.random.normal(0.0, 8.0 * scale))
            nr_x = max(np.float32(2.0), min(max_r_f, curr_r_x + np.float32(np.random.normal(0.0, 6.0 * scale))))
            nr_y = max(np.float32(2.0), min(max_r_f, curr_r_y + np.float32(np.random.normal(0.0, 6.0 * scale))))
            ntheta = curr_theta + np.float32(np.random.normal(0.0, 0.25 * scale))
            nalpha = 255
            
            nr, ng, nb, delta = evaluate_candidate_py(
                self.target_image, current_canvas, nx_c, ny_c, nr_x, nr_y, ntheta, nalpha, alpha_mask, check_contour,
                hill_climb_freeze, freeze_mask, params.get("use_weight", False), weight_map, params.get("use_uncovered", False), uncovered_map
            )
            
            diff = delta - curr_delta
            accept = False
            if diff < 0:
                accept = True
            elif sa_enabled:
                P = math.exp(-float(diff) / float(T))
                if np.random.uniform(0.0, 1.0) < P:
                    accept = True
                    
            if accept:
                curr_delta = np.float32(delta)
                curr_x_c = nx_c
                curr_y_c = ny_c
                curr_r_x = nr_x
                curr_r_y = nr_y
                curr_theta = ntheta
                curr_alpha = nalpha
                curr_r = np.float32(nr)
                curr_g = np.float32(ng)
                curr_b = np.float32(nb)
                
            if sa_enabled:
                T = T * c_rate
                
        best_shape_params = [float(curr_x_c), float(curr_y_c), float(curr_r_x), float(curr_r_y), float(curr_theta), int(curr_r), int(curr_g), int(curr_b), curr_alpha]
        return best_shape_params, float(curr_delta)

    def draw_shape_on_canvas(self, canvas: np.ndarray, x_c: float, y_c: float, r_x: float, r_y: float, theta_rad: float, r: float, g: float, b: float, alpha: float) -> None:
        draw_ellipse_py(canvas, x_c, y_c, r_x, r_y, theta_rad, r, g, b, alpha)

    def rebuild_canvas(self, canvas: np.ndarray, shapes_list: list, avg_r: float, avg_g: float, avg_b: float) -> None:
        avg_a = 255.0
        if len(shapes_list) > 0:
            header = shapes_list[0]
            h_color = header.get("color", [128, 128, 128, 255])
            avg_a = h_color[3] if len(h_color) >= 4 else 255.0

        if len(shapes_list) <= 1:
            canvas[:, :, 0] = avg_r
            canvas[:, :, 1] = avg_g
            canvas[:, :, 2] = avg_b
            if canvas.shape[2] == 4:
                canvas[:, :, 3] = avg_a
            return
            
        # Draw backward using pure python loop
        canvas[:, :, 0] = avg_r
        canvas[:, :, 1] = avg_g
        canvas[:, :, 2] = avg_b
        if canvas.shape[2] == 4:
            canvas[:, :, 3] = avg_a
            
        for s in shapes_list:
            if s["type"] == 32:
                data = s["data"]
                color = s["color"]
                x_c, y_c, r_x, r_y, theta_deg = data
                r, g, b = color[0], color[1], color[2]
                alpha = color[3] if len(color) >= 4 else 255
                draw_ellipse_py(canvas, x_c, y_c, r_x, r_y, math.radians(theta_deg), r, g, b, alpha)

    def run_redundancy_check(self, shapes_list: list, width: int, height: int, final_check: bool = False) -> list:
        if len(shapes_list) <= 1:
            return shapes_list
            
        num_shapes = len(shapes_list)
        visible_mask = np.ones(num_shapes, dtype=np.bool_)
        occlusion = np.zeros((height, width), dtype=np.float32)
        
        # Walk backward from top to bottom
        for i in range(num_shapes - 1, -1, -1):
            s = shapes_list[i]
            s_type = s["type"]
            
            if s_type == 1:
                visible_mask[i] = True
                occlusion[:, :] = 1.0
                continue
                
            data = s["data"]
            color = s["color"]
            x_c, y_c, r_x, r_y, theta_deg = data
            theta = math.radians(theta_deg)
            alpha = color[3] if len(color) >= 4 else 255
            a_f = np.float32(alpha / 255.0)
            
            cos_t = np.float32(math.cos(theta))
            sin_t = np.float32(math.sin(theta))
            
            x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
            y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
            
            min_x = max(0, int(x_c - x_half))
            max_x = min(width - 1, int(x_c + x_half))
            min_y = max(0, int(y_c - y_half))
            max_y = min(height - 1, int(y_c + y_half))
            
            inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
            inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
            
            has_contribution = False
            
            for y in range(min_y, max_y + 1):
                dy = np.float32(y - y_c)
                dx_start = np.float32(min_x - x_c)
                rx = dx_start * cos_t + dy * sin_t
                ry = -dx_start * sin_t + dy * cos_t
                
                for x in range(min_x, max_x + 1):
                    if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
                        if occlusion[y, x] < 0.999:
                            has_contribution = True
                            occlusion[y, x] += (1.0 - occlusion[y, x]) * a_f
                            
                    rx += cos_t
                    ry -= sin_t
                    
            if not has_contribution:
                visible_mask[i] = False
                
        if not final_check:
            optimized_shapes = [shapes_list[i] for i in range(num_shapes) if visible_mask[i]]
            removed_count = num_shapes - len(optimized_shapes)
            if removed_count > 0:
                print(f"\n[Optimization] Removed {removed_count} redundant/occluded shapes! Conserved layers count: {len(optimized_shapes)}")
            return optimized_shapes
        else:
            final_shapes = []
            reset_count = 0
            final_shapes.append(shapes_list[0])
            for i in range(1, num_shapes):
                s = shapes_list[i]
                if visible_mask[i]:
                    final_shapes.append(s)
                else:
                    reset_shape = {
                        "type": 32,
                        "data": [-1000.0, -1000.0, 0.01, 0.01, 0.0],
                        "color": [0, 0, 0, 255],
                        "score": 0.0
                    }
                    final_shapes.append(reset_shape)
                    reset_count += 1
            if reset_count > 0:
                print(f"\n[Optimization] Final check: reset {reset_count} redundant shapes to off-screen microscopic opaque shapes.")
            return final_shapes

    def init_uncovered_map(self, width: int, height: int, has_alpha: bool, bias: float) -> np.ndarray:
        uncovered_map = np.ones((height, width), dtype=np.float32)
        if has_alpha and self.alpha_mask is not None:
            for y in range(height):
                for x in range(width):
                    if self.alpha_mask[y, x] > 10.0:
                        uncovered_map[y, x] = np.float32(bias)
        else:
            uncovered_map[:] = np.float32(bias)
        return uncovered_map

    def update_uncovered_mask(self, uncovered_map: np.ndarray, x_c: float, y_c: float, r_x: float, r_y: float, theta_rad: float) -> None:
        height = uncovered_map.shape[0]
        width = uncovered_map.shape[1]
        
        cos_t = np.float32(math.cos(theta_rad))
        sin_t = np.float32(math.sin(theta_rad))
        
        x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
        y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
        
        min_x = max(0, int(x_c - x_half))
        max_x = min(width - 1, int(x_c + x_half))
        min_y = max(0, int(y_c - y_half))
        max_y = min(height - 1, int(y_c + y_half))
        
        inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
        inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
        
        for y in range(min_y, max_y + 1):
            dy = np.float32(y - y_c)
            dx_start = np.float32(min_x - x_c)
            rx = dx_start * cos_t + dy * sin_t
            ry = -dx_start * sin_t + dy * cos_t
            
            for x in range(min_x, max_x + 1):
                if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
                    uncovered_map[y, x] = np.float32(1.0)
                
                rx += cos_t
                ry -= sin_t

    def cleanup(self) -> None:
        pass
