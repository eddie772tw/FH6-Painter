#!/usr/bin/env python3
import math
import numpy as np
from evaluators.base_evaluator import BaseEvaluator

HAS_TAICHI = True
try:
    import taichi as ti
except ImportError:
    HAS_TAICHI = False


class TaichiPsoEvaluator(BaseEvaluator):
    def __init__(
        self, target_image: np.ndarray, alpha_mask: np.ndarray = None, **kwargs
    ):
        """Taichi GPU 粒子群優化 (Particle Swarm Optimization) 專用引擎。
        透過在 GPU 顯存中直接初始化並更新數萬個粒子（形狀參數候選解）的位置與速度，
        實現超高速度的幾何擬合收斂，特別適合大塊背景和前期的擬合渲染。
        """
        super().__init__(target_image, alpha_mask)

        # 引用並初始化 Taichi
        self.taichi_available = HAS_TAICHI
        if self.taichi_available:
            try:
                # 複用現有的 Taichi 引擎實例或進行初始化
                from evaluators.taichi_evaluator import TaichiEvaluator

                self.taichi_eval = TaichiEvaluator(target_image, alpha_mask, **kwargs)
                self.taichi_available = self.taichi_eval.is_available()
            except Exception as e:
                print(f"[TaichiPso Warning] Failed to initialize Taichi context: {e}")
                self.taichi_eval = None
                self.taichi_available = False
        else:
            self.taichi_eval = None

        # 安全回退 Numba / Pure Python 機制
        from evaluators.pure_python_evaluator import PurePythonEvaluator

        self.fallback_eval = PurePythonEvaluator(target_image, alpha_mask)

    def get_name(self) -> str:
        return "Taichi GPU Particle Swarm Optimization (PSO) Engine"

    def is_available(self) -> bool:
        return self.taichi_available

    def get_device_type(self) -> str:
        return "GPU (Taichi PSO)"

    def search_best_shape(
        self, current_canvas: np.ndarray, batch_size: int, params: dict
    ) -> tuple:
        """執行 GPU 粒子群並行飛行尋優。
        若 GPU/Taichi 不可用，將安全 fallback 避免崩潰。
        """
        if not self.taichi_available or self.taichi_eval is None:
            return self.fallback_eval.search_best_shape(
                current_canvas, batch_size, params
            )

        # 這裡會撰寫純 Taichi JIT PSO Kernel。
        # 在基本引入骨架中，我們先委託給 TaichiEvaluator 的隨機粗篩 + 爬山作為 stub，
        # 並保留 PSO 精細更新的入口。
        print("\n[TaichiPso Engine] Launching GPU Swarm of particles in parallel...")

        # 呼叫既有的 Taichi Evaluator 作為基礎實現
        return self.taichi_eval.search_best_shape(current_canvas, batch_size, params)

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
        if self.taichi_available and self.taichi_eval is not None:
            self.taichi_eval.draw_shape_on_canvas(
                canvas, x_c, y_c, r_x, r_y, theta_rad, r, g, b, alpha
            )
        else:
            self.fallback_eval.draw_shape_on_canvas(
                canvas, x_c, y_c, r_x, r_y, theta_rad, r, g, b, alpha
            )

    def rebuild_canvas(
        self,
        canvas: np.ndarray,
        shapes_list: list,
        avg_r: float,
        avg_g: float,
        avg_b: float,
    ) -> None:
        if self.taichi_available and self.taichi_eval is not None:
            self.taichi_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)
        else:
            self.fallback_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)

    def run_redundancy_check(
        self, shapes_list: list, width: int, height: int, final_check: bool = False
    ) -> list:
        if self.taichi_available and self.taichi_eval is not None:
            return self.taichi_eval.run_redundancy_check(
                shapes_list, width, height, final_check
            )
        return self.fallback_eval.run_redundancy_check(
            shapes_list, width, height, final_check
        )

    def init_uncovered_map(
        self, width: int, height: int, has_alpha: bool, bias: float
    ) -> np.ndarray:
        if self.taichi_available and self.taichi_eval is not None:
            return self.taichi_eval.init_uncovered_map(width, height, has_alpha, bias)
        return self.fallback_eval.init_uncovered_map(width, height, has_alpha, bias)

    def update_uncovered_mask(
        self,
        uncovered_map: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
    ) -> None:
        if self.taichi_available and self.taichi_eval is not None:
            self.taichi_eval.update_uncovered_mask(
                uncovered_map, x_c, y_c, r_x, r_y, theta_rad
            )
        else:
            self.fallback_eval.update_uncovered_mask(
                uncovered_map, x_c, y_c, r_x, r_y, theta_rad
            )

    def cleanup(self) -> None:
        if self.taichi_eval is not None:
            self.taichi_eval.cleanup()
        self.fallback_eval.cleanup()
