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
        types = FakeTypes()
        
        def kernel(self, func):
            # Pass-through decorator to bypass compile
            return func
            
        def field(self, *args, **kwargs):
            return None
    ti = FakeTi()

class TaichiEvaluator(BaseEvaluator):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None):
        super().__init__(target_image, alpha_mask)
        self.initialized = False
        if HAS_TAICHI:
            try:
                # 強制初始化為 Vulkan 後端，以完美相容 Windows 環境下的 AMD 及各大顯示卡
                ti.init(arch=ti.vulkan, log_level=ti.WARN)
                
                # 【VRAM 常駐設計】將目標影像和 Alpha 遮罩放入 GPU 全域記憶體
                self.ti_target = ti.ndarray(dtype=ti.f32, shape=target_image.shape)
                self.ti_target.from_numpy(target_image)
                
                if alpha_mask is not None:
                    self.ti_alpha = ti.ndarray(dtype=ti.f32, shape=alpha_mask.shape)
                    self.ti_alpha.from_numpy(alpha_mask)
                else:
                    self.ti_alpha = None
                    
                # 準備接收最終最佳解的 GPU 欄位空間 [error, x, y, rx, ry, theta, r, g, b, a]
                self.ti_best_result = ti.field(dtype=ti.f32, shape=10)
                self.initialized = True
            except Exception as e:
                print(f"[Taichi Backend Warning] Vulkan backend initialization failed: {e}")
                self.initialized = False

    def get_name(self) -> str:
        return "Taichi JIT (GPU - Vulkan)"

    def is_available(self) -> bool:
        return HAS_TAICHI and self.initialized

    def get_device_type(self) -> str:
        return "GPU"

    def search_best_shape(self, current_canvas: np.ndarray, batch_size: int, params: dict) -> tuple:
        if not self.is_available():
            raise RuntimeError("Taichi JIT Evaluator is not available or failed to initialize Vulkan backend.")
            
        # 1. 僅上傳極為輕量的目前 Canvas 狀態到 GPU
        ti_canvas = ti.ndarray(dtype=ti.f32, shape=current_canvas.shape)
        ti_canvas.from_numpy(current_canvas)
        
        # 2. 重置 GPU 全域最佳解誤差為無限大
        self.ti_best_result[0] = 99999999.0
        
        # 3. 呼叫 GPU 計算核心 (呼叫下方定義的 ti.kernel)
        # 註：此處目前為 GPU Vulkan 加速外掛架構骨架演示
        self._taichi_kernel_stub(ti_canvas, batch_size)
        
        # 4. 【PCIe 傳輸極小化】僅將獲勝的「1 個」最佳形狀參數與最低誤差讀回 CPU 記憶體
        best_data = self.ti_best_result.to_numpy()
        min_error = float(best_data[0])
        
        # 如果 GPU 計算未實作，提供模擬/隨機測試值以利調試
        if min_error >= 90000000.0:
            height, width, _ = self.target_image.shape
            x_c = np.random.uniform(0.0, float(width))
            y_c = np.random.uniform(0.0, float(height))
            r_x = np.random.uniform(2.0, max(10.0, min(width, height) / 3.0))
            r_y = np.random.uniform(2.0, max(10.0, min(width, height) / 3.0))
            theta = np.random.uniform(0.0, 2.0 * math.pi)
            best_shape_params = [x_c, y_c, r_x, r_y, theta, 128, 128, 128, 255]
            min_error = 1000.0
        else:
            best_shape_params = [
                float(best_data[1]), float(best_data[2]), float(best_data[3]), float(best_data[4]), # x_c, y_c, r_x, r_y
                float(best_data[5]), # theta
                int(best_data[6]), int(best_data[7]), int(best_data[8]), int(best_data[9]) # r, g, b, a
            ]
            
        return best_shape_params, min_error

    @ti.kernel
    def _taichi_kernel_stub(self, canvas: ti.types.ndarray(), batch_size: int):
        # Taichi 會自動將此 range-for 迴圈編譯並展開為百萬級別 GPU 平行 Threads
        for i in range(batch_size):
            # 這裡將實作高並行的隨機參數生成與橢圓擬合 Delta MSE 誤差估算
            # 最終透過 ti.atomic_min 將最低誤差歸約至 ti_best_result[0]
            pass

    def draw_shape_on_canvas(self, canvas: np.ndarray, x_c: float, y_c: float, r_x: float, r_y: float, theta_rad: float, r: float, g: float, b: float, alpha: float) -> None:
        # Fallback to numpy or implement in GPU
        from evaluators.pure_python_evaluator import draw_ellipse_py
        draw_ellipse_py(canvas, x_c, y_c, r_x, r_y, theta_rad, r, g, b, alpha)

    def rebuild_canvas(self, canvas: np.ndarray, shapes_list: list, avg_r: float, avg_g: float, avg_b: float) -> None:
        # Fallback to pure python rebuild helper
        from evaluators.pure_python_evaluator import PurePythonEvaluator
        py_eval = PurePythonEvaluator(self.target_image, self.alpha_mask)
        py_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)

    def run_redundancy_check(self, shapes_list: list, width: int, height: int, final_check: bool = False) -> list:
        # Fallback to pure python redundancy check helper
        from evaluators.pure_python_evaluator import PurePythonEvaluator
        py_eval = PurePythonEvaluator(self.target_image, self.alpha_mask)
        return py_eval.run_redundancy_check(shapes_list, width, height, final_check)

    def init_uncovered_map(self, width: int, height: int, has_alpha: bool, bias: float) -> np.ndarray:
        uncovered_map = np.ones((height, width), dtype=np.float32)
        if has_alpha and self.alpha_mask is not None:
            uncovered_map[self.alpha_mask > 10.0] = np.float32(bias)
        else:
            uncovered_map[:] = np.float32(bias)
        return uncovered_map

    def update_uncovered_mask(self, uncovered_map: np.ndarray, x_c: float, y_c: float, r_x: float, r_y: float, theta_rad: float) -> None:
        from evaluators.pure_python_evaluator import PurePythonEvaluator
        py_eval = PurePythonEvaluator(self.target_image, self.alpha_mask)
        py_eval.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta_rad)

    def cleanup(self) -> None:
        # 釋放 GPU 記憶體與對象
        pass
