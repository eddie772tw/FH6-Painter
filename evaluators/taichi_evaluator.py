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
                    
                    # 預置一個空的 (1, 1) 用於未使用時的佔位符，減少非必要拷貝與分配
                    self.ti_empty_u8 = ti.ndarray(dtype=ti.uint8, shape=(1, 1))
                    self.ti_empty_u8.from_numpy(np.zeros((1, 1), dtype=np.uint8))
                    self.ti_empty_f32 = ti.ndarray(dtype=ti.f32, shape=(1, 1))
                    self.ti_empty_f32.from_numpy(np.zeros((1, 1), dtype=np.float32))
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
            
        # 1. 處理並生成隨機橢圓參數 (在 CPU 上使用 NumPy 高速產生)
        use_importance = params.get("use_importance", False)
        error_prob = params.get("error_prob")
        
        if use_importance and error_prob is not None and error_prob.shape[0] > 1:
            x_c_arr = np.zeros(batch_size, dtype=np.float32)
            y_c_arr = np.zeros(batch_size, dtype=np.float32)
            # Rejection Sampling
            for i in range(batch_size):
                keep = False
                for att in range(100):
                    x = np.random.uniform(0.0, float(width))
                    y = np.random.uniform(0.0, float(height))
                    ix = int(x)
                    iy = int(y)
                    if 0 <= ix < width and 0 <= iy < height:
                        if np.random.uniform(0.0, 1.0) < error_prob[iy, ix]:
                            x_c_arr[i] = x
                            y_c_arr[i] = y
                            keep = True
                            break
                if not keep:
                    x_c_arr[i] = np.random.uniform(0.0, float(width))
                    y_c_arr[i] = np.random.uniform(0.0, float(height))
        else:
            x_c_arr = np.random.uniform(0.0, float(width), batch_size).astype(np.float32)
            y_c_arr = np.random.uniform(0.0, float(height), batch_size).astype(np.float32)
            
        r_x_arr = np.random.uniform(2.0, max_r, batch_size).astype(np.float32)
        r_y_arr = np.random.uniform(2.0, max_r, batch_size).astype(np.float32)
        theta_arr = np.random.uniform(0.0, 2.0 * math.pi, batch_size).astype(np.float32)
        alpha_arr = np.full(batch_size, 255.0, dtype=np.float32)
        
        # 拼接成候選矩陣
        candidates = np.stack([x_c_arr, y_c_arr, r_x_arr, r_y_arr, theta_arr, alpha_arr], axis=1).astype(np.float32)
        
        # 2. 上傳變動的 canvas 到 VRAM，直接重用 self.ti_canvas 緩衝區
        self.ti_canvas.from_numpy(current_canvas)
        
        # 快取與動態調整 ti_candidates 和 ti_results，避免每次都重新分配
        if not hasattr(self, "ti_candidates") or self.ti_candidates.shape[0] != batch_size:
            self.ti_candidates = ti.ndarray(dtype=ti.f32, shape=(batch_size, 6))
            self.ti_results = ti.ndarray(dtype=ti.f32, shape=(batch_size, 4))
            
        self.ti_candidates.from_numpy(candidates)
        
        # 3. 處理其它遮罩與加權 Map 的 VRAM 更新 (重用機制)
        check_contour = 1 if (self.alpha_mask is not None and params.get("check_contour", False)) else 0
        
        use_freeze = 1 if params.get("use_freeze", False) else 0
        freeze_mask = params.get("freeze_mask")
        ti_freeze_ref = self.ti_empty_u8
        if use_freeze == 1 and freeze_mask is not None:
            self.ti_freeze.from_numpy(freeze_mask)
            ti_freeze_ref = self.ti_freeze
            
        use_weight = 1 if params.get("use_weight", False) else 0
        weight_map = params.get("weight_map")
        ti_weight_ref = self.ti_empty_f32
        if use_weight == 1 and weight_map is not None:
            self.ti_weight.from_numpy(weight_map)
            ti_weight_ref = self.ti_weight
            
        use_uncovered = 1 if params.get("use_uncovered", False) else 0
        uncovered_map = params.get("uncovered_map")
        ti_uncovered_ref = self.ti_empty_f32
        if use_uncovered == 1 and uncovered_map is not None:
            self.ti_uncovered.from_numpy(uncovered_map)
            ti_uncovered_ref = self.ti_uncovered
        
        # 4. 啟動 GPU 並行搜尋核
        taichi_parallel_search(
            self.ti_target,
            self.ti_canvas,
            self.ti_candidates,
            self.ti_results,
            self.ti_alpha,
            check_contour,
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
        
        # 5. 回讀 GPU 計算結果，並在 CPU 端以極速挑選最優解
        results_np = self.ti_results.to_numpy()
        deltas = results_np[:, 3]
        best_idx = np.argmin(deltas)
        
        x_c = float(candidates[best_idx, 0])
        y_c = float(candidates[best_idx, 1])
        r_x = float(candidates[best_idx, 2])
        r_y = float(candidates[best_idx, 3])
        theta = float(candidates[best_idx, 4])
        alpha = float(candidates[best_idx, 5])
        
        r = float(results_np[best_idx, 0])
        g = float(results_np[best_idx, 1])
        b = float(results_np[best_idx, 2])
        delta = float(deltas[best_idx])
        
        # 6. Hill-Climbing 爬升優化 (優先與 CPU 版本的 Numba 爬升優化對接，確保極限精準度)
        try:
            from evaluators import numba_kernels
            HAS_NUMBA_KERNELS = True
        except ImportError:
            HAS_NUMBA_KERNELS = False
            
        if HAS_NUMBA_KERNELS:
            # 傳遞給 CPU Numba JIT 完成最後精細的串行微調爬升
            hill_climb_freeze = params.get("use_freeze", False)
            freeze_mask_np = freeze_mask if freeze_mask is not None else np.zeros((1, 1), dtype=np.uint8)
            weight_map_np = weight_map if weight_map is not None else np.ones((1, 1), dtype=np.float32)
            uncovered_map_np = uncovered_map if uncovered_map is not None else np.ones((1, 1), dtype=np.float32)
            alpha_mask_np = self.alpha_mask if self.alpha_mask is not None else np.zeros((1, 1), dtype=np.float32)
            
            x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta = numba_kernels.serial_hill_climb(
                self.target_image, current_canvas, x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta,
                params.get("optimization_steps", 50), alpha_mask_np, check_contour == 1,
                params.get("sa_enabled", False), params.get("sa_initial_temp", 5000.0), params.get("sa_cooling_rate", 0.95),
                max_r, hill_climb_freeze, freeze_mask_np,
                use_weight == 1, weight_map_np,
                use_uncovered == 1, uncovered_map_np
            )
            
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
