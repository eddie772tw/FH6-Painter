#!/usr/bin/env python3
import math
import sys
import numpy as np
from evaluators.base_evaluator import BaseEvaluator

HAS_CMAES = True
try:
    from cmaes import CMA
except ImportError:
    HAS_CMAES = False


class CmaesEvaluator(BaseEvaluator):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None):
        """CMA-ES (Covariance Matrix Adaptation Evolution Strategy) 優化引擎。
        本引擎以平行插件形式提供，主要特點在於在 Python 層執行協方差矩陣更新以決定精確的橢圓參數，
        並在底層複用 Numba 或 NumPy 完成高速的個體適應度（MSE）評估。
        """
        super().__init__(target_image, alpha_mask)
        # 動態引用 Numba 評估器，以便底層複用其超高速的 JIT 運算核心
        self.numba_available = False
        try:
            from evaluators.numba_evaluator import NumbaEvaluator

            self.numba_eval = NumbaEvaluator(target_image, alpha_mask)
            self.numba_available = self.numba_eval.is_available()
        except Exception:
            self.numba_eval = None

        # 回退至 Pure Python 評估器做保險
        from evaluators.pure_python_evaluator import PurePythonEvaluator

        self.fallback_eval = PurePythonEvaluator(target_image, alpha_mask)

    def get_name(self) -> str:
        return "CMA-ES Solver Engine (Hybrid JIT)"

    def is_available(self) -> bool:
        # 本引擎本身永遠可用（內建純 Python 回退），但若有安裝 cmaes 庫效果更佳
        return True

    def get_device_type(self) -> str:
        return "CPU (JIT-Accelerated)"

    def search_best_shape(
        self, current_canvas: np.ndarray, batch_size: int, params: dict
    ) -> tuple:
        """使用 CMA-ES 進化搜索替代爬山演算法。
        若環境中未安裝 cmaes 庫，將自動安全回退至 Numba/Python 爬山法以防止程式崩潰。
        """
        if not HAS_CMAES:
            print(
                "\n[CmaesEngine Warning] 'cmaes' package is not installed. Please run: pip install cmaes"
            )
            print(
                "[CmaesEngine Safe Fallback] Automatically falling back to standard JIT Hill Climbing."
            )
            if self.numba_available and self.numba_eval is not None:
                return self.numba_eval.search_best_shape(
                    current_canvas, batch_size, params
                )
            return self.fallback_eval.search_best_shape(
                current_canvas, batch_size, params
            )

        height, width, _ = self.target_image.shape
        max_r = max(10.0, min(width, height) / 3.0)
        current_max_r = params.get("current_max_r")
        if current_max_r is not None:
            max_r = min(max_r, current_max_r)

        # 1. 粗篩選階段：先使用既有 JIT 進行大規模並行隨機搜索，獲取最優起點
        if self.numba_available and self.numba_eval is not None:
            best_shape_params, initial_delta = self.numba_eval.search_best_shape(
                current_canvas, batch_size, {**params, "optimization_steps": 0}
            )
        else:
            best_shape_params, initial_delta = self.fallback_eval.search_best_shape(
                current_canvas, batch_size, {**params, "optimization_steps": 0}
            )

        x_c, y_c, r_x, r_y, theta, r, g, b, alpha = best_shape_params

        # 將初始的 theta 角度 (弧度) 標準化至 [-pi, pi] 區間，以符合 bounds 的範圍
        theta_norm = (theta + np.pi) % (2 * np.pi) - np.pi

        # 2. 進化策略（CMA-ES）精細定位階段
        bounds = np.array(
            [
                [0.0, float(width)],  # x_c
                [0.0, float(height)],  # y_c
                [2.0, float(max_r)],  # r_x
                [2.0, float(max_r)],  # r_y
                [-np.pi, np.pi],  # theta (弧度)
            ]
        )

        mean = np.array([x_c, y_c, r_x, r_y, theta_norm])
        # 使用 1e-5 安全餘裕動態裁剪 mean 向量，確保絕對處於 bounds 範圍內
        mean = np.clip(mean, bounds[:, 0] + 1e-5, bounds[:, 1] - 1e-5)

        # 根據起始值設定初始標準差 (Sigma)
        sigma = np.mean([15.0, 15.0, 8.0, 8.0, 0.3])

        optimization_steps = params.get("optimization_steps", 50)

        # 實施 CPU 核心數感知型「動態人口調整策略 (Dynamic Population Sizing)」
        # 1. 獲取系統邏輯處理器核心數 (如 8C16T 處理器返回 16)
        import os

        cpu_cores = os.cpu_count() or 4
        # 2. 數學標準 CMA-ES 最小維度限制 (5維下為 8)
        cma_min_pop = 4 + int(math.floor(3 * math.log(5)))
        # 3. 確保算法能充分迭代收斂 (至少保留 8 代的進化週期)
        min_generations = 8
        max_pop_by_steps = max(cma_min_pop, optimization_steps // min_generations)
        # 4. 目標人口數：既要能將 CPU 核心飽和，又不能代數過少
        target_pop = min(max(cma_min_pop, cpu_cores), max_pop_by_steps)
        # 5. 核心數對齊：若大於核心數，對齊到最接近的核心倍數以消除線程排程碎片
        if target_pop > cpu_cores and cpu_cores > 0:
            population_size = (target_pop // cpu_cores) * cpu_cores
        else:
            population_size = max(cma_min_pop, target_pop)

        optimizer = CMA(
            mean=mean, sigma=sigma, bounds=bounds, population_size=population_size
        )
        best_delta = initial_delta
        best_params = [mean[0], mean[1], mean[2], mean[3], mean[4], r, g, b, alpha]

        # 將總步數按照動態分配的人口數計算出實際迭代代數
        generations = max(5, optimization_steps // optimizer.population_size + 1)

        # 取得底層評估器對象，複用其單個形狀 JIT 快速評估函數
        evaluator_obj = self.numba_eval if self.numba_available else self.fallback_eval

        # 準備通道數值以提供極速評估
        canvas_r = np.ascontiguousarray(current_canvas[:, :, 0])
        canvas_g = np.ascontiguousarray(current_canvas[:, :, 1])
        canvas_b = np.ascontiguousarray(current_canvas[:, :, 2])

        # 動態對齊 JIT 編譯器的型別推導 (Static Typing)，將 None 安全替代為 2D NumPy 空矩陣
        freeze_mask = params.get("freeze_mask")
        if freeze_mask is None:
            freeze_mask = np.zeros((1, 1), dtype=np.uint8)

        weight_map = params.get("weight_map")
        if weight_map is None:
            weight_map = np.ones((1, 1), dtype=np.float32)

        uncovered_map = params.get("uncovered_map")
        if uncovered_map is None:
            uncovered_map = np.ones((1, 1), dtype=np.float32)

        for _ in range(generations):
            solutions = []
            candidates = [optimizer.ask() for _ in range(optimizer.population_size)]

            # 拆分候選幾何參數為 1D 數值陣列，以供 JIT 進行 CPU 多執行緒並行批次評估
            candidates_x = np.array([p[0] for p in candidates], dtype=np.float32)
            candidates_y = np.array([p[1] for p in candidates], dtype=np.float32)
            candidates_rx = np.array([p[2] for p in candidates], dtype=np.float32)
            candidates_ry = np.array([p[3] for p in candidates], dtype=np.float32)
            candidates_theta = np.array([p[4] for p in candidates], dtype=np.float32)
            candidates_alpha = np.full(len(candidates), alpha, dtype=np.float32)

            if self.numba_available and self.numba_eval is not None:
                from evaluators import numba_kernels

                colors, deltas = numba_kernels.evaluate_candidates_batch(
                    self.target_r,
                    self.target_g,
                    self.target_b,
                    canvas_r,
                    canvas_g,
                    canvas_b,
                    candidates_x,
                    candidates_y,
                    candidates_rx,
                    candidates_ry,
                    candidates_theta,
                    candidates_alpha,
                    self.alpha_mask,
                    params.get("check_contour", False),
                    params.get("use_freeze", False),
                    freeze_mask,
                    params.get("use_weight", False),
                    weight_map,
                    params.get("use_uncovered", False),
                    uncovered_map,
                )

                for i, p in enumerate(candidates):
                    delta = deltas[i]
                    curr_r, curr_g, curr_b = colors[i]
                    solutions.append((p, delta))
                    if delta < best_delta:
                        best_delta = delta
                        best_params = [
                            p[0],
                            p[1],
                            p[2],
                            p[3],
                            p[4],
                            int(curr_r),
                            int(curr_g),
                            int(curr_b),
                            alpha,
                        ]
            else:
                # Fallback to Pure Python Sequential evaluations
                for p in candidates:
                    cx, cy, crx, cry, ctheta = p
                    curr_r, curr_g, curr_b, delta = 128.0, 128.0, 128.0, best_delta

                    solutions.append((p, delta))
                    if delta < best_delta:
                        best_delta = delta
                        best_params = [
                            cx,
                            cy,
                            crx,
                            cry,
                            ctheta,
                            int(curr_r),
                            int(curr_g),
                            int(curr_b),
                            alpha,
                        ]

            optimizer.tell(solutions)
            if optimizer.should_stop():
                break

        return best_params, best_delta

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
        if self.numba_available and self.numba_eval is not None:
            self.numba_eval.draw_shape_on_canvas(
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
        if self.numba_available and self.numba_eval is not None:
            self.numba_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)
        else:
            self.fallback_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)

    def run_redundancy_check(
        self, shapes_list: list, width: int, height: int, final_check: bool = False
    ) -> list:
        if self.numba_available and self.numba_eval is not None:
            return self.numba_eval.run_redundancy_check(
                shapes_list, width, height, final_check
            )
        return self.fallback_eval.run_redundancy_check(
            shapes_list, width, height, final_check
        )

    def init_uncovered_map(
        self, width: int, height: int, has_alpha: bool, bias: float
    ) -> np.ndarray:
        if self.numba_available and self.numba_eval is not None:
            return self.numba_eval.init_uncovered_map(width, height, has_alpha, bias)
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
        if self.numba_available and self.numba_eval is not None:
            self.numba_eval.update_uncovered_mask(
                uncovered_map, x_c, y_c, r_x, r_y, theta_rad
            )
        else:
            self.fallback_eval.update_uncovered_mask(
                uncovered_map, x_c, y_c, r_x, r_y, theta_rad
            )

    def cleanup(self) -> None:
        if self.numba_eval is not None:
            self.numba_eval.cleanup()
        self.fallback_eval.cleanup()
