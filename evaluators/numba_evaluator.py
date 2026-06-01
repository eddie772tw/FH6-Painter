#!/usr/bin/env python3
import math

import numpy as np

from evaluators.base_evaluator import BaseEvaluator

try:
    from evaluators import numba_kernels_aot as numba_kernels
    HAS_NUMBA = True
except ImportError:
    try:
        import numba
        from evaluators import numba_kernels
        HAS_NUMBA = True
    except ImportError:
        HAS_NUMBA = False


class NumbaEvaluator(BaseEvaluator):
    def __init__(self, target_image: np.ndarray, alpha_mask: np.ndarray = None):
        super().__init__(target_image, alpha_mask)

    def get_name(self) -> str:
        return "Numba JIT (CPU Multithreading)"

    def is_available(self) -> bool:
        return HAS_NUMBA

    def get_device_type(self) -> str:
        return "CPU"

    def search_best_shape(
        self, current_canvas: np.ndarray, batch_size: int, params: dict
    ) -> tuple:
        if not HAS_NUMBA:
            raise RuntimeError("Numba is not installed or available.")

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

        # CPU 端動態平面拆分 Canvas 通道 (C-contiguous 2D planar arrays)
        canvas_r = np.ascontiguousarray(current_canvas[:, :, 0])
        canvas_g = np.ascontiguousarray(current_canvas[:, :, 1])
        canvas_b = np.ascontiguousarray(current_canvas[:, :, 2])

        x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = (
            numba_kernels.parallel_random_search(
                self.target_r,
                self.target_g,
                self.target_b,
                canvas_r,
                canvas_g,
                canvas_b,
                batch_size,
                width,
                height,
                max_r,
                alpha_mask,
                check_contour,
                params.get("use_importance", False),
                error_prob,
                params.get("use_freeze", False),
                freeze_mask,
                params.get("use_weight", False),
                weight_map,
                params.get("use_uncovered", False),
                uncovered_map,
            )
        )

        fallback_active = False
        if params.get("use_freeze", False) and delta >= 90000000.0:
            fallback_active = True
            x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = (
                numba_kernels.parallel_random_search(
                    self.target_r,
                    self.target_g,
                    self.target_b,
                    canvas_r,
                    canvas_g,
                    canvas_b,
                    batch_size,
                    width,
                    height,
                    max_r,
                    alpha_mask,
                    check_contour,
                    params.get("use_importance", False),
                    error_prob,
                    False,
                    freeze_mask,
                    params.get("use_weight", False),
                    weight_map,
                    params.get("use_uncovered", False),
                    uncovered_map,
                )
            )

        hill_climb_freeze = (
            params.get("use_freeze", False) if not fallback_active else False
        )
        x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta = (
            numba_kernels.serial_hill_climb(
                self.target_r,
                self.target_g,
                self.target_b,
                canvas_r,
                canvas_g,
                canvas_b,
                x_c,
                y_c,
                r_x,
                r_y,
                theta,
                alpha,
                r,
                g,
                b,
                delta,
                params.get("optimization_steps", 50),
                alpha_mask,
                check_contour,
                params.get("sa_enabled", False),
                params.get("sa_initial_temp", 5000.0),
                params.get("sa_cooling_rate", 0.95),
                max_r,
                hill_climb_freeze,
                freeze_mask,
                params.get("use_weight", False),
                weight_map,
                params.get("use_uncovered", False),
                uncovered_map,
            )
        )

        best_shape_params = [x_c, y_c, r_x, r_y, theta, r, g, b, alpha]
        return best_shape_params, delta

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
        if not HAS_NUMBA:
            raise RuntimeError("Numba is not installed or available.")
        numba_kernels.draw_ellipse(
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
        if not HAS_NUMBA:
            raise RuntimeError("Numba is not installed or available.")

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

        num_shapes = 0
        for s in shapes_list:
            if s["type"] == 32:
                num_shapes += 1

        shapes_data = np.zeros((num_shapes, 5), dtype=np.float32)
        shapes_color = np.zeros((num_shapes, 4), dtype=np.int32)

        idx = 0
        for s in shapes_list:
            if s["type"] == 32:
                data = s["data"]
                shapes_data[idx, 0] = data[0]
                shapes_data[idx, 1] = data[1]
                shapes_data[idx, 2] = data[2]
                shapes_data[idx, 3] = data[3]
                shapes_data[idx, 4] = math.radians(data[4])

                color = s["color"]
                shapes_color[idx, 0] = color[0]
                shapes_color[idx, 1] = color[1]
                shapes_color[idx, 2] = color[2]
                shapes_color[idx, 3] = color[3] if len(color) >= 4 else 255
                idx += 1

        numba_kernels.rebuild_canvas_jit(
            canvas, avg_r, avg_g, avg_b, avg_a, shapes_data, shapes_color
        )

    def run_redundancy_check(
        self, shapes_list: list, width: int, height: int, final_check: bool = False
    ) -> list:
        if not HAS_NUMBA:
            raise RuntimeError("Numba is not installed or available.")

        if len(shapes_list) <= 1:
            return shapes_list

        num_shapes = len(shapes_list)
        shapes_data = np.zeros((num_shapes, 5), dtype=np.float32)
        shapes_color = np.zeros((num_shapes, 4), dtype=np.int32)
        shapes_type = np.zeros(num_shapes, dtype=np.int32)

        for i, s in enumerate(shapes_list):
            s_type = s["type"]
            shapes_type[i] = s_type
            data = s["data"]
            if s_type == 32 and len(data) >= 5:
                shapes_data[i, 0] = data[0]
                shapes_data[i, 1] = data[1]
                shapes_data[i, 2] = data[2]
                shapes_data[i, 3] = data[3]
                shapes_data[i, 4] = math.radians(data[4])

            color = s["color"]
            if len(color) >= 4:
                shapes_color[i, 0] = color[0]
                shapes_color[i, 1] = color[1]
                shapes_color[i, 2] = color[2]
                shapes_color[i, 3] = color[3]

        visible_mask = numba_kernels.run_redundancy_check_jit(
            shapes_data, shapes_color, shapes_type, width, height
        )

        if not final_check:
            optimized_shapes = [
                shapes_list[i] for i in range(num_shapes) if visible_mask[i]
            ]
            removed_count = num_shapes - len(optimized_shapes)
            if removed_count > 0:
                print(
                    f"\n[Optimization] Removed {removed_count} redundant/occluded shapes! Conserved layers count: {len(optimized_shapes)}"
                )
            return optimized_shapes
        else:
            center_x = float(width) / 2.0
            center_y = float(height) / 2.0

            valid_shapes = []
            discarded_shapes = []

            for i in range(1, num_shapes):
                s = shapes_list[i]
                if visible_mask[i]:
                    valid_shapes.append(s)
                else:
                    reset_shape = {
                        "type": 32,
                        "data": [center_x, center_y, 0.01, 0.01, 0.0],
                        "color": [0, 0, 0, 255],
                        "score": 0.0,
                    }
                    discarded_shapes.append(reset_shape)

            final_shapes = [shapes_list[0]] + valid_shapes + discarded_shapes
            reset_count = len(discarded_shapes)

            if reset_count > 0:
                print(
                    f"\n[Optimization] Final check: reset {reset_count} redundant shapes to microscopic opaque shapes at center ({center_x:.1f}, {center_y:.1f}) pushed to top layers."
                )
            return final_shapes

    def init_uncovered_map(
        self, width: int, height: int, has_alpha: bool, bias: float
    ) -> np.ndarray:
        if not HAS_NUMBA:
            raise RuntimeError("Numba is not installed or available.")

        alpha_mask = self.alpha_mask
        return numba_kernels.init_uncovered_map(
            width, height, has_alpha, alpha_mask, bias
        )

    def update_uncovered_mask(
        self,
        uncovered_map: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
    ) -> None:
        if not HAS_NUMBA:
            raise RuntimeError("Numba is not installed or available.")
        numba_kernels.update_uncovered_mask(
            uncovered_map, x_c, y_c, r_x, r_y, theta_rad
        )

    def cleanup(self) -> None:
        pass
