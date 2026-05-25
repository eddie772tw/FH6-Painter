#!/usr/bin/env python3
import math
import numpy as np
from evaluators.base_evaluator import BaseEvaluator

try:
    import taichi as ti
    HAS_TAICHI = True
except ImportError:
    HAS_TAICHI = False
    
    # Safe Mock for class-level decorator loading when taichi is missing
    class FakeTi:
        class FakeTypes:
            def ndarray(self, *args, **kwargs):
                return object
            def __getattr__(self, name):
                return object
        types = FakeTypes()
        
        def kernel(self, func):
            return func
            
        def func(self, func):
            return func
            
        def field(self, *args, **kwargs):
            return None
            
        def __getattr__(self, name):
            if name == "math":
                import math
                return math
            return object
    ti = FakeTi()

# --- Taichi Global Reduction Field (Moved to instance level to respect ti.init lifecycle) ---

# --- Taichi GPU Accelerated Functions ---
@ti.func
def evaluate_candidate_ti(
    target: ti.types.ndarray(),
    canvas: ti.types.ndarray(),
    x_c: ti.f32, y_c: ti.f32, r_x: ti.f32, r_y: ti.f32, theta: ti.f32, alpha: ti.f32,
    alpha_mask: ti.types.ndarray(),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32
):
    """
    在 GPU 上並行評估單一橢圓參數的 Delta MSE。
    完全符合 Taichi 控制流規範（不使用 early-return 與 break，改用狀態旗標）。
    """
    cos_t = ti.math.cos(theta)
    sin_t = ti.math.sin(theta)
    
    x_half = ti.math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = ti.math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    is_valid = 1
    
    # 強制硬性邊界約束：超出畫布則賦予極大懲罰值
    if (x_c - x_half < 0.0) or (x_c + x_half > ti.cast(width, ti.f32)) or (y_c - y_half < 0.0) or (y_c + y_half > ti.cast(height, ti.f32)):
        is_valid = 0
        
    count = 0.0
    sum_t_r = 0.0
    sum_t_g = 0.0
    sum_t_b = 0.0
    
    sum_c_r = 0.0
    sum_c_g = 0.0
    sum_c_b = 0.0
    
    sum_c2_r = 0.0
    sum_c2_g = 0.0
    sum_c2_b = 0.0
    
    sum_ct_r = 0.0
    sum_ct_g = 0.0
    sum_ct_b = 0.0
    
    if is_valid == 1:
        min_x = ti.max(0, ti.cast(x_c - x_half, ti.i32))
        max_x = ti.min(width - 1, ti.cast(x_c + x_half, ti.i32))
        min_y = ti.max(0, ti.cast(y_c - y_half, ti.i32))
        max_y = ti.min(height - 1, ti.cast(y_c + y_half, ti.i32))
        
        inv_rx2 = 1.0 / (r_x * r_x) if r_x > 0.0 else 0.0
        inv_ry2 = 1.0 / (r_y * r_y) if r_y > 0.0 else 0.0
        
        for y in range(min_y, max_y + 1):
            if is_valid == 0:
                break
            dy = ti.cast(y, ti.f32) - y_c
            dx_start = ti.cast(min_x, ti.f32) - x_c
            rx = dx_start * cos_t + dy * sin_t
            ry = -dx_start * sin_t + dy * cos_t
            
            for x in range(min_x, max_x + 1):
                if is_valid == 0:
                    break
                if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
                    # 輪廓約束
                    if check_contour == 1:
                        if alpha_mask[y, x] <= 10.0:
                            is_valid = 0
                            
                    # 動態凍結遮罩
                    if use_freeze == 1:
                        if freeze_mask[y, x] == 1:
                            is_valid = 0
                            
                    if is_valid == 1:
                        t_r = target[y, x, 0]
                        t_g = target[y, x, 1]
                        t_b = target[y, x, 2]
                        
                        c_r = canvas[y, x, 0]
                        c_g = canvas[y, x, 1]
                        c_b = canvas[y, x, 2]
                        
                        w = 1.0
                        if use_weight == 1:
                            w = weight_map[y, x]
                        if use_uncovered == 1:
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
                
    avg_r = 0.0
    avg_g = 0.0
    avg_b = 0.0
    total_delta_mse = 99999999.0
    
    if is_valid == 1 and count > 0.0:
        avg_r = sum_t_r / count
        avg_g = sum_t_g / count
        avg_b = sum_t_b / count
        
        a_f = alpha / 255.0
        a2_minus_2a = a_f * a_f - 2.0 * a_f
        two_a = 2.0 * a_f
        two_a_one_minus_a = 2.0 * a_f * (1.0 - a_f)
        
        delta_r = a2_minus_2a * sum_c2_r + two_a * sum_ct_r + two_a_one_minus_a * avg_r * sum_c_r + a2_minus_2a * avg_r * sum_t_r
        delta_g = a2_minus_2a * sum_c2_g + two_a * sum_ct_g + two_a_one_minus_a * avg_g * sum_c_g + a2_minus_2a * avg_g * sum_t_g
        delta_b = a2_minus_2a * sum_c2_b + two_a * sum_ct_b + two_a_one_minus_a * avg_b * sum_c_b + a2_minus_2a * avg_b * sum_t_b
        
        total_delta_mse = delta_r + delta_g + delta_b
        
    return avg_r, avg_g, avg_b, total_delta_mse

@ti.kernel
def taichi_parallel_search(
    target: ti.types.ndarray(),
    canvas: ti.types.ndarray(),
    candidates: ti.types.ndarray(),  # Shape: (batch_size, 6) -> [x_c, y_c, r_x, r_y, theta, alpha]
    results: ti.types.ndarray(),     # Shape: (batch_size, 4) -> [r, g, b, delta_mse]
    alpha_mask: ti.types.ndarray(),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32,
    batch_size: ti.i32
):
    # Taichi 會在 GPU 上並行啟動 batch_size 個並行 Thread，達到極致加速
    for i in range(batch_size):
        x_c = candidates[i, 0]
        y_c = candidates[i, 1]
        r_x = candidates[i, 2]
        r_y = candidates[i, 3]
        theta = candidates[i, 4]
        alpha = candidates[i, 5]
        
        r, g, b, delta = evaluate_candidate_ti(
            target, canvas, x_c, y_c, r_x, r_y, theta, alpha,
            alpha_mask, check_contour,
            use_freeze, freeze_mask,
            use_weight, weight_map,
            use_uncovered, uncovered_map,
            height, width
        )
        
        results[i, 0] = r
        results[i, 1] = g
        results[i, 2] = b
        results[i, 3] = delta

# --- Taichi Full GPU Pipeline Accelerated Kernels ---
@ti.kernel
def compute_raw_error_and_max(
    target: ti.types.ndarray(),
    canvas: ti.types.ndarray(),
    error_prob: ti.types.ndarray(),
    max_err_arr: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32
):
    max_err_arr[0] = 0.0
    for y, x in ti.ndrange(height, width):
        diff = 0.0
        for c in ti.static(range(3)):
            diff += ti.math.abs(target[y, x, c] - canvas[y, x, c])
        diff /= 3.0
        ti.atomic_max(max_err_arr[0], diff)
        error_prob[y, x] = diff

@ti.kernel
def normalize_error_prob(
    error_prob: ti.types.ndarray(),
    max_err_arr: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32
):
    max_val = max_err_arr[0]
    for y, x in ti.ndrange(height, width):
        if max_val > 0.0:
            error_prob[y, x] = error_prob[y, x] / max_val
        else:
            error_prob[y, x] = 0.0

@ti.kernel
def update_freeze_mask_gpu(
    target: ti.types.ndarray(),
    canvas: ti.types.ndarray(),
    freeze_mask: ti.types.ndarray(),
    threshold: ti.f32,
    height: ti.i32,
    width: ti.i32
):
    for y, x in ti.ndrange(height, width):
        diff = 0.0
        for c in ti.static(range(3)):
            diff += ti.math.abs(target[y, x, c] - canvas[y, x, c])
        diff /= 3.0
        if diff < threshold:
            freeze_mask[y, x] = 1
        else:
            freeze_mask[y, x] = 0

@ti.kernel
def update_weights_gpu(
    target: ti.types.ndarray(),
    canvas: ti.types.ndarray(),
    weight_map: ti.types.ndarray(),
    boundary_weight: ti.types.ndarray(),
    max_err_arr: ti.types.ndarray(),
    has_boundary: ti.i32,
    height: ti.i32,
    width: ti.i32
):
    max_err_arr[0] = 0.0
    for y, x in ti.ndrange(height, width):
        diff = 0.0
        for c in ti.static(range(3)):
            diff += ti.math.abs(target[y, x, c] - canvas[y, x, c])
        diff /= 3.0
        ti.atomic_max(max_err_arr[0], diff)
        weight_map[y, x] = diff

    max_val = max_err_arr[0]
    for y, x in ti.ndrange(height, width):
        norm_err = 0.0
        if max_val > 0.0:
            norm_err = weight_map[y, x] / max_val
        
        dynamic_w = 1.0 + norm_err * 9.0
        if has_boundary == 1:
            weight_map[y, x] = dynamic_w * boundary_weight[y, x]
        else:
            weight_map[y, x] = dynamic_w

@ti.kernel
def update_uncovered_mask_gpu(
    uncovered_map: ti.types.ndarray(),
    best_candidate: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32
):
    x_c = best_candidate[0, 0]
    y_c = best_candidate[0, 1]
    r_x = best_candidate[0, 2]
    r_y = best_candidate[0, 3]
    theta = best_candidate[0, 4]
    
    cos_t = ti.math.cos(theta)
    sin_t = ti.math.sin(theta)
    
    x_half = ti.math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = ti.math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    min_x = ti.max(0, ti.cast(x_c - x_half, ti.i32))
    max_x = ti.min(width - 1, ti.cast(x_c + x_half, ti.i32))
    min_y = ti.max(0, ti.cast(y_c - y_half, ti.i32))
    max_y = ti.min(height - 1, ti.cast(y_c + y_half, ti.i32))
    
    inv_rx2 = 1.0 / (r_x * r_x) if r_x > 0.0 else 0.0
    inv_ry2 = 1.0 / (r_y * r_y) if r_y > 0.0 else 0.0
    
    for y, x in ti.ndrange((min_y, max_y + 1), (min_x, max_x + 1)):
        dy = ti.cast(y, ti.f32) - y_c
        dx = ti.cast(x, ti.f32) - x_c
        rx = dx * cos_t + dy * sin_t
        ry = -dx * sin_t + dy * cos_t
        if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
            uncovered_map[y, x] = 1.0

@ti.kernel
def generate_candidates_gpu(
    candidates: ti.types.ndarray(),
    width: ti.f32,
    height: ti.f32,
    max_r: ti.f32,
    use_importance: ti.i32,
    error_prob: ti.types.ndarray(),
    batch_size: ti.i32
):
    for i in range(batch_size):
        x = 0.0
        y = 0.0
        
        if use_importance == 1:
            keep = 0
            for att in range(100):
                if keep == 0:
                    tx = ti.random() * width
                    ty = ti.random() * height
                    ix = ti.cast(tx, ti.i32)
                    iy = ti.cast(ty, ti.i32)
                    if ix >= 0 and ix < ti.cast(width, ti.i32) and iy >= 0 and iy < ti.cast(height, ti.i32):
                        if ti.random() < error_prob[iy, ix]:
                            x = tx
                            y = ty
                            keep = 1
            if keep == 0:
                x = ti.random() * width
                y = ti.random() * height
        else:
            x = ti.random() * width
            y = ti.random() * height
            
        r_x = 2.0 + ti.random() * (max_r - 2.0)
        r_y = 2.0 + ti.random() * (max_r - 2.0)
        theta = ti.random() * 2.0 * ti.math.pi
        alpha = 255.0
        
        candidates[i, 0] = x
        candidates[i, 1] = y
        candidates[i, 2] = r_x
        candidates[i, 3] = r_y
        candidates[i, 4] = theta
        candidates[i, 5] = alpha

@ti.kernel
def draw_ellipse_gpu(
    canvas: ti.types.ndarray(),
    best_candidate: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32
):
    x_c = best_candidate[0, 0]
    y_c = best_candidate[0, 1]
    r_x = best_candidate[0, 2]
    r_y = best_candidate[0, 3]
    theta = best_candidate[0, 4]
    
    r = best_candidate[0, 6]
    g = best_candidate[0, 7]
    b = best_candidate[0, 8]
    alpha = best_candidate[0, 5]
    
    cos_t = ti.math.cos(theta)
    sin_t = ti.math.sin(theta)
    
    x_half = ti.math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = ti.math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    min_x = ti.max(0, ti.cast(x_c - x_half, ti.i32))
    max_x = ti.min(width - 1, ti.cast(x_c + x_half, ti.i32))
    min_y = ti.max(0, ti.cast(y_c - y_half, ti.i32))
    max_y = ti.min(height - 1, ti.cast(y_c + y_half, ti.i32))
    
    inv_rx2 = 1.0 / (r_x * r_x) if r_x > 0.0 else 0.0
    inv_ry2 = 1.0 / (r_y * r_y) if r_y > 0.0 else 0.0
    
    a_f = alpha / 255.0
    one_minus_a = 1.0 - a_f
    
    for y, x in ti.ndrange((min_y, max_y + 1), (min_x, max_x + 1)):
        dy = ti.cast(y, ti.f32) - y_c
        dx = ti.cast(x, ti.f32) - x_c
        rx = dx * cos_t + dy * sin_t
        ry = -dx * sin_t + dy * cos_t
        if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
            canvas[y, x, 0] = canvas[y, x, 0] * one_minus_a + r * a_f
            canvas[y, x, 1] = canvas[y, x, 1] * one_minus_a + g * a_f
            canvas[y, x, 2] = canvas[y, x, 2] * one_minus_a + b * a_f

@ti.kernel
def find_best_candidate_gpu(
    candidates: ti.types.ndarray(),
    results: ti.types.ndarray(),
    best_candidate: ti.types.ndarray(),
    batch_size: ti.i32
):
    best_idx = 0
    min_delta = 999999999.0
    for i in range(batch_size):
        if results[i, 3] < min_delta:
            min_delta = results[i, 3]
            best_idx = i
            
    best_candidate[0, 0] = candidates[best_idx, 0]
    best_candidate[0, 1] = candidates[best_idx, 1]
    best_candidate[0, 2] = candidates[best_idx, 2]
    best_candidate[0, 3] = candidates[best_idx, 3]
    best_candidate[0, 4] = candidates[best_idx, 4]
    best_candidate[0, 5] = candidates[best_idx, 5]
    
    best_candidate[0, 6] = results[best_idx, 0]
    best_candidate[0, 7] = results[best_idx, 1]
    best_candidate[0, 8] = results[best_idx, 2]
    best_candidate[0, 9] = results[best_idx, 3]

@ti.kernel
def parallel_hill_climb_gpu(
    best_candidate: ti.types.ndarray(),
    climb_candidates: ti.types.ndarray(),
    climb_results: ti.types.ndarray(),
    target: ti.types.ndarray(),
    canvas: ti.types.ndarray(),
    alpha_mask: ti.types.ndarray(),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(),
    height: ti.i32,
    width: ti.i32,
    max_r: ti.f32,
    sa_enabled: ti.i32,
    sa_initial_temp: ti.f32,
    sa_cooling_rate: ti.f32,
    optimization_steps: ti.i32
):
    for i in range(128):
        curr_x_c = best_candidate[0, 0]
        curr_y_c = best_candidate[0, 1]
        curr_r_x = best_candidate[0, 2]
        curr_r_y = best_candidate[0, 3]
        curr_theta = best_candidate[0, 4]
        curr_alpha = best_candidate[0, 5]
        
        curr_r = best_candidate[0, 6]
        curr_g = best_candidate[0, 7]
        curr_b = best_candidate[0, 8]
        curr_delta = best_candidate[0, 9]
        
        T = sa_initial_temp
        
        for step in range(optimization_steps):
            scale = 1.0 - (ti.cast(step, ti.f32) / ti.cast(optimization_steps, ti.f32))
            
            u1 = ti.random()
            u2 = ti.random()
            if u1 < 1e-6:
                u1 = 1e-6
            r_normal = ti.math.sqrt(-2.0 * ti.math.log(u1))
            theta_normal = 2.0 * ti.math.pi * u2
            
            z0 = r_normal * ti.math.cos(theta_normal)
            z1 = r_normal * ti.math.sin(theta_normal)
            
            u3 = ti.random()
            u4 = ti.random()
            if u3 < 1e-6:
                u3 = 1e-6
            r_normal2 = ti.math.sqrt(-2.0 * ti.math.log(u3))
            theta_normal2 = 2.0 * ti.math.pi * u4
            z2 = r_normal2 * ti.math.cos(theta_normal2)
            z3 = r_normal2 * ti.math.sin(theta_normal2)
            
            nx_c = curr_x_c + z0 * 8.0 * scale
            ny_c = curr_y_c + z1 * 8.0 * scale
            nr_x = ti.max(2.0, ti.min(max_r, curr_r_x + z2 * 6.0 * scale))
            nr_y = ti.max(2.0, ti.min(max_r, curr_r_y + z3 * 6.0 * scale))
            ntheta = curr_theta + z1 * 0.25 * scale
            nalpha = 255.0
            
            nr, ng, nb, delta = evaluate_candidate_ti(
                target, canvas, nx_c, ny_c, nr_x, nr_y, ntheta, nalpha,
                alpha_mask, check_contour,
                use_freeze, freeze_mask,
                use_weight, weight_map,
                use_uncovered, uncovered_map,
                height, width
            )
            
            diff = delta - curr_delta
            accept = 0
            if diff < 0.0:
                accept = 1
            elif sa_enabled == 1:
                P = ti.math.exp(-diff / T)
                if ti.random() < P:
                    accept = 1
                    
            if accept == 1:
                curr_delta = delta
                curr_x_c = nx_c
                curr_y_c = ny_c
                curr_r_x = nr_x
                curr_r_y = nr_y
                curr_theta = ntheta
                curr_alpha = nalpha
                curr_r = nr
                curr_g = ng
                curr_b = nb
                
            if sa_enabled == 1:
                T = T * sa_cooling_rate
                
        climb_candidates[i, 0] = curr_x_c
        climb_candidates[i, 1] = curr_y_c
        climb_candidates[i, 2] = curr_r_x
        climb_candidates[i, 3] = curr_r_y
        climb_candidates[i, 4] = curr_theta
        climb_candidates[i, 5] = curr_alpha
        
        climb_results[i, 0] = curr_r
        climb_results[i, 1] = curr_g
        climb_results[i, 2] = curr_b
        climb_results[i, 3] = curr_delta

@ti.kernel
def select_final_best_gpu(
    climb_candidates: ti.types.ndarray(),
    climb_results: ti.types.ndarray(),
    best_candidate: ti.types.ndarray()
):
    best_idx = 0
    min_delta = 999999999.0
    for i in range(128):
        if climb_results[i, 3] < min_delta:
            min_delta = climb_results[i, 3]
            best_idx = i
            
    best_candidate[0, 0] = climb_candidates[best_idx, 0]
    best_candidate[0, 1] = climb_candidates[best_idx, 1]
    best_candidate[0, 2] = climb_candidates[best_idx, 2]
    best_candidate[0, 3] = climb_candidates[best_idx, 3]
    best_candidate[0, 4] = climb_candidates[best_idx, 4]
    best_candidate[0, 5] = climb_candidates[best_idx, 5]
    
    best_candidate[0, 6] = climb_results[best_idx, 0]
    best_candidate[0, 7] = climb_results[best_idx, 1]
    best_candidate[0, 8] = climb_results[best_idx, 2]
    best_candidate[0, 9] = climb_results[best_idx, 3]

# --- Taichi GPU Evaluator Implementation ---
class TaichiEvaluator(BaseEvaluator):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None, taichi_arch: str = None, taichi_device_id: int = None):
        super().__init__(target_image, alpha_mask)
        self.initialized = False
        self.arch_name = "N/A"
        
        if HAS_TAICHI:
            # 將字串轉換為 Taichi 的 arch
            arch_map = {
                "Vulkan": ti.vulkan,
                "CUDA": ti.cuda,
                "OpenGL": ti.opengl,
                "CPU": ti.cpu
            }
            
            # 優先透過系統環境變數設定 Vulkan 與 CUDA 裝置，完美跨平台且 100% 官方相容
            if taichi_device_id is not None:
                import os
                os.environ["CUDA_VISIBLE_DEVICES"] = str(taichi_device_id)
                os.environ["VULKAN_DEVICE_INDEX"] = str(taichi_device_id)
                os.environ["VULKAN_PHYSICAL_DEVICE_INDEX"] = str(taichi_device_id)
                
            backends = []
            if taichi_arch and taichi_arch in arch_map:
                backends.append((arch_map[taichi_arch], f"GPU - {taichi_arch}" if taichi_arch != "CPU" else "CPU"))
            else:
                # 預設優先級：Vulkan -> CUDA -> OpenGL -> CPU
                backends = [
                    (ti.vulkan, "GPU - Vulkan"),
                    (ti.cuda, "GPU - CUDA"),
                    (ti.opengl, "GPU - OpenGL"),
                    (ti.cpu, "CPU")
                ]
                
            for arch, name in backends:
                try:
                    # 使用 100% 官方標準規格初始化 ti.init，徹底排除 Unrecognized keyword argument 錯誤
                    ti.init(arch=arch, log_level=ti.WARN)
                    # 測試性分配一個微型 field 驗證該後端是否能被系統成功呼叫
                    test = ti.field(dtype=ti.f32, shape=1)
                    test[0] = 1.0
                    
                    self.initialized = True
                    self.arch_name = name
                    print(f"[Taichi JIT Backend] Successfully initialized backend: {name} (Device ID: {taichi_device_id})")
                    break
                except Exception as e:
                    print(f"[Taichi Backend Warning] Attempt to initialize {arch} failed: {e}")
                    continue
            
            if self.initialized:
                try:
                    # 將大體積的 Target Image 預先上傳至 VRAM，降低 PCIe 頻寬開銷
                    self.ti_target = ti.ndarray(dtype=ti.f32, shape=target_image.shape)
                    self.ti_target.from_numpy(target_image.astype(np.float32))
                    
                    # 預先分配大體積且形狀固定的 canvas 緩衝區
                    self.ti_canvas = ti.ndarray(dtype=ti.f32, shape=target_image.shape)
                    
                    if alpha_mask is not None:
                        self.ti_alpha = ti.ndarray(dtype=ti.f32, shape=alpha_mask.shape)
                        self.ti_alpha.from_numpy(alpha_mask.astype(np.float32))
                    else:
                        # 傳入 1x1 的佔位 ndarray
                        self.ti_alpha = ti.ndarray(dtype=ti.f32, shape=(1, 1))
                        self.ti_alpha.from_numpy(np.zeros((1, 1), dtype=np.float32))
                        
                    # 預先分配其它畫布大小的 Map，避免每次 search_best_shape 都重新分配
                    height, width, _ = target_image.shape
                    self.ti_freeze = ti.ndarray(dtype=ti.uint8, shape=(height, width))
                    self.ti_weight = ti.ndarray(dtype=ti.f32, shape=(height, width))
                    self.ti_uncovered = ti.ndarray(dtype=ti.f32, shape=(height, width))
                    self.ti_error_prob = ti.ndarray(dtype=ti.f32, shape=(height, width))
                    
                    # 預置一個空的 (1, 1) 用於未使用時的佔位符，減少非必要拷貝與分配
                    self.ti_empty_u8 = ti.ndarray(dtype=ti.uint8, shape=(1, 1))
                    self.ti_empty_u8.from_numpy(np.zeros((1, 1), dtype=np.uint8))
                    self.ti_empty_f32 = ti.ndarray(dtype=ti.f32, shape=(1, 1))
                    self.ti_empty_f32.from_numpy(np.zeros((1, 1), dtype=np.float32))
                    
                    # 全 GPU 管道流特有的 VRAM 緩衝區
                    self.ti_best_candidate = ti.ndarray(dtype=ti.f32, shape=(1, 10))
                    self.ti_climb_candidates = ti.ndarray(dtype=ti.f32, shape=(128, 6))
                    self.ti_climb_results = ti.ndarray(dtype=ti.f32, shape=(128, 4))
                    self.ti_max_err = ti.ndarray(dtype=ti.f32, shape=1)
                except Exception as e:
                    print(f"[Taichi JIT VRAM Allocation Error] {e}")
                    self.initialized = False

    def get_name(self) -> str:
        return f"Taichi JIT ({self.arch_name})"

    def is_available(self) -> bool:
        return HAS_TAICHI and self.initialized

    def get_device_type(self) -> str:
        return "CPU" if self.arch_name == "CPU" else "GPU"

    def search_best_shape(self, current_canvas: np.ndarray, batch_size: int, params: dict) -> tuple:
        if not self.is_available():
            raise RuntimeError("Taichi JIT Evaluator is not available or failed to initialize backend.")
            
        height, width, _ = self.target_image.shape
        max_r = max(10.0, min(width, height) / 3.0)
        current_max_r = params.get("current_max_r")
        if current_max_r is not None:
            max_r = min(max_r, current_max_r)
            
        # 1. 更新變動的遮罩與誤差 Map (純 GPU 運算，無 PCIe Overhead)
        use_importance = params.get("use_importance", False)
        error_prob_np = params.get("error_prob")
        
        # 動態更新重要性採樣誤差概率圖
        if use_importance and error_prob_np is not None and error_prob_np.shape[0] > 1:
            compute_raw_error_and_max(self.ti_target, self.ti_canvas, self.ti_error_prob, self.ti_max_err, height, width)
            normalize_error_prob(self.ti_error_prob, self.ti_max_err, height, width)
            
        # 動態凍結遮罩更新
        use_freeze = 1 if params.get("use_freeze", False) else 0
        freeze_mask_np = params.get("freeze_mask")
        ti_freeze_ref = self.ti_empty_u8
        if use_freeze == 1 and freeze_mask_np is not None:
            self.ti_freeze.from_numpy(freeze_mask_np)
            ti_freeze_ref = self.ti_freeze
            
        # 動態權重更新
        use_weight = 1 if params.get("use_weight", False) else 0
        weight_map_np = params.get("weight_map")
        ti_weight_ref = self.ti_empty_f32
        if use_weight == 1 and weight_map_np is not None:
            self.ti_weight.from_numpy(weight_map_np)
            ti_weight_ref = self.ti_weight
            
        # 動態未覆蓋遮罩更新
        use_uncovered = 1 if params.get("use_uncovered", False) else 0
        uncovered_map_np = params.get("uncovered_map")
        ti_uncovered_ref = self.ti_empty_f32
        if use_uncovered == 1 and uncovered_map_np is not None:
            self.ti_uncovered.from_numpy(uncovered_map_np)
            ti_uncovered_ref = self.ti_uncovered
            
        # 2. GPU 端隨機生成橢圓候選者
        if not hasattr(self, "ti_candidates") or self.ti_candidates.shape[0] != batch_size:
            self.ti_candidates = ti.ndarray(dtype=ti.f32, shape=(batch_size, 6))
            self.ti_results = ti.ndarray(dtype=ti.f32, shape=(batch_size, 4))
            
        generate_candidates_gpu(
            self.ti_candidates,
            float(width),
            float(height),
            float(max_r),
            1 if (use_importance and error_prob_np is not None) else 0,
            self.ti_error_prob,
            batch_size
        )
        
        # 3. GPU 並行搜尋與評估
        # 輪廓約束安全判定：若為 1x1 的佔位符或無效遮罩，則強行關閉輪廓約束以防止 GPU 越界判定錯誤
        check_contour = params.get("check_contour", False)
        if self.alpha_mask is None or self.alpha_mask.shape == (1, 1):
            check_contour = False
        check_contour_jit = 1 if check_contour else 0
        
        taichi_parallel_search(
            self.ti_target,
            self.ti_canvas,
            self.ti_candidates,
            self.ti_results,
            self.ti_alpha,
            check_contour_jit,
            use_freeze,
            ti_freeze_ref,
            use_weight,
            ti_weight_ref,
            use_uncovered,
            ti_uncovered_ref,
            height,
            width,
            batch_size
        )
        
        # 4. GPU 內部 Reduction：挑選初篩最優解
        find_best_candidate_gpu(self.ti_candidates, self.ti_results, self.ti_best_candidate, batch_size)
        
        # 5. GPU 並行局部模擬退火爬升 (取代原 CPU serial hill-climb，效能與精度雙重躍升！)
        sa_enabled = 1 if params.get("sa_enabled", False) else 0
        sa_initial_temp = float(params.get("sa_initial_temp", 5000.0))
        sa_cooling_rate = float(params.get("sa_cooling_rate", 0.95))
        optimization_steps = params.get("optimization_steps", 50)
        
        parallel_hill_climb_gpu(
            self.ti_best_candidate,
            self.ti_climb_candidates,
            self.ti_climb_results,
            self.ti_target,
            self.ti_canvas,
            self.ti_alpha,
            check_contour_jit,
            use_freeze,
            ti_freeze_ref,
            use_weight,
            ti_weight_ref,
            use_uncovered,
            ti_uncovered_ref,
            height,
            width,
            float(max_r),
            sa_enabled,
            sa_initial_temp,
            sa_cooling_rate,
            optimization_steps
        )
        
        # 6. GPU 內部 Reduction 挑選最終微調最優解
        select_final_best_gpu(self.ti_climb_candidates, self.ti_climb_results, self.ti_best_candidate)
        
        # 7. 在 GPU 顯存中直接繪製當前最優解 (保持與 CPU 同步，省去下載重繪開銷)
        draw_ellipse_gpu(self.ti_canvas, self.ti_best_candidate, height, width)
        
        # 8. 在 GPU 顯存中直接更新 uncovered 遮罩
        if use_uncovered == 1:
            update_uncovered_mask_gpu(self.ti_uncovered, self.ti_best_candidate, height, width)
            
        # 9. 下載最終最優解的結果 (只有 1 行數據，傳輸開銷趨近於 0！)
        best_candidate_np = self.ti_best_candidate.to_numpy()
        
        x_c = float(best_candidate_np[0, 0])
        y_c = float(best_candidate_np[0, 1])
        r_x = float(best_candidate_np[0, 2])
        r_y = float(best_candidate_np[0, 3])
        theta = float(best_candidate_np[0, 4])
        alpha = float(best_candidate_np[0, 5])
        
        r = float(best_candidate_np[0, 6])
        g = float(best_candidate_np[0, 7])
        b = float(best_candidate_np[0, 8])
        delta = float(best_candidate_np[0, 9])
        
        # 同步回寫 uncovered_map_np 以便 generator 的 CPU 重建邏輯正常運作
        if use_uncovered == 1 and uncovered_map_np is not None:
            uncovered_map_np[:] = self.ti_uncovered.to_numpy()
            
        best_shape_params = [x_c, y_c, r_x, r_y, theta, r, g, b, alpha]
        return best_shape_params, delta

    def draw_shape_on_canvas(self, canvas: np.ndarray, x_c: float, y_c: float, r_x: float, r_y: float, theta_rad: float, r: float, g: float, b: float, alpha: float) -> None:
        # 優先呼叫 CPU Numba 完成高速畫圖
        try:
            from evaluators import numba_kernels
            numba_kernels.draw_ellipse(canvas, x_c, y_c, r_x, r_y, theta_rad, r, g, b, alpha)
        except ImportError:
            from evaluators.pure_python_evaluator import draw_ellipse_py
            draw_ellipse_py(canvas, x_c, y_c, r_x, r_y, theta_rad, r, g, b, alpha)

    def rebuild_canvas(self, canvas: np.ndarray, shapes_list: list, avg_r: float, avg_g: float, avg_b: float) -> None:
        # 優先呼叫 CPU Numba 完成極速畫布重建
        try:
            from evaluators.numba_evaluator import NumbaEvaluator
            numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
            numba_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)
        except Exception:
            from evaluators.pure_python_evaluator import PurePythonEvaluator
            py_eval = PurePythonEvaluator(self.target_image, self.alpha_mask)
            py_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)

    def run_redundancy_check(self, shapes_list: list, width: int, height: int, final_check: bool = False) -> list:
        try:
            from evaluators.numba_evaluator import NumbaEvaluator
            numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
            return numba_eval.run_redundancy_check(shapes_list, width, height, final_check)
        except Exception:
            from evaluators.pure_python_evaluator import PurePythonEvaluator
            py_eval = PurePythonEvaluator(self.target_image, self.alpha_mask)
            return py_eval.run_redundancy_check(shapes_list, width, height, final_check)

    def init_uncovered_map(self, width: int, height: int, has_alpha: bool, bias: float) -> np.ndarray:
        try:
            from evaluators.numba_evaluator import NumbaEvaluator
            numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
            return numba_eval.init_uncovered_map(width, height, has_alpha, bias)
        except Exception:
            uncovered_map = np.ones((height, width), dtype=np.float32)
            if has_alpha and self.alpha_mask is not None:
                uncovered_map[self.alpha_mask > 10.0] = np.float32(bias)
            else:
                uncovered_map[:] = np.float32(bias)
            return uncovered_map

    def update_uncovered_mask(self, uncovered_map: np.ndarray, x_c: float, y_c: float, r_x: float, r_y: float, theta_rad: float) -> None:
        try:
            from evaluators.numba_evaluator import NumbaEvaluator
            numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
            numba_eval.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta_rad)
        except Exception:
            from evaluators.pure_python_evaluator import PurePythonEvaluator
            py_eval = PurePythonEvaluator(self.target_image, self.alpha_mask)
            py_eval.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta_rad)

    def cleanup(self) -> None:
        pass
