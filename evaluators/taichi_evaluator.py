#!/usr/bin/env python3
import os
import sys

import numpy as np

# PyInstaller environment source-inspect hook for Taichi Lang JIT
if getattr(sys, "frozen", False):
    physical_py_file = os.path.join(sys._MEIPASS, "evaluators", "taichi_evaluator.py")
    if os.path.exists(physical_py_file):
        __file__ = physical_py_file
        if "evaluators.taichi_evaluator" in sys.modules:
            sys.modules["evaluators.taichi_evaluator"].__file__ = physical_py_file

from evaluators.base_evaluator import BaseEvaluator

try:
    import taichi as ti

    HAS_TAICHI = True
except ImportError:
    HAS_TAICHI = False

    # Mock ti module for decorator loading when taichi is not installed
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


@ti.func
def evaluate_candidate_ti(
    target_r: ti.types.ndarray(),
    target_g: ti.types.ndarray(),
    target_b: ti.types.ndarray(),
    canvas_r: ti.types.ndarray(),
    canvas_g: ti.types.ndarray(),
    canvas_b: ti.types.ndarray(),
    x_c: ti.f32,
    y_c: ti.f32,
    r_x: ti.f32,
    r_y: ti.f32,
    theta: ti.f32,
    alpha: ti.f32,
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
):
    """Evaluates a single ellipse candidate on GPU using planar Target/Canvas channels and scanline solvers."""
    cos_t = ti.math.cos(theta)
    sin_t = ti.math.sin(theta)

    x_half = ti.math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
    y_half = ti.math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

    is_valid = 1

    if (
        (x_c - x_half < 0.0)
        or (x_c + x_half > ti.cast(width, ti.f32))
        or (y_c - y_half < 0.0)
        or (y_c + y_half > ti.cast(height, ti.f32))
    ):
        is_valid = 0

    count = 0.0
    count_transparent = 0.0
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

        sin_cos = sin_t * cos_t
        a = inv_rx2 * cos_t * cos_t + inv_ry2 * sin_t * sin_t
        b_coeff = sin_cos * (inv_rx2 - inv_ry2)
        inv_rx2_ry2 = inv_rx2 * inv_ry2

        # Precompute division (1.0 / a) to avoid expensive division inside tight loops
        inv_a = 1.0 / a if a > 0.0 else 0.0

        # Validation Pass (Scalar constraints check)
        if check_contour == 1 or use_freeze == 1:
            dy = ti.cast(min_y, ti.f32) - y_c
            b_val = dy * b_coeff
            discriminant = a - dy * dy * inv_rx2_ry2
            disc_step_1 = -2.0 * dy * inv_rx2_ry2
            disc_step_2 = -inv_rx2_ry2

            y = min_y
            while y <= max_y and is_valid == 1:
                if discriminant >= 0.0:
                    sqrt_d = ti.math.sqrt(discriminant)
                    dx_min = (-b_val - sqrt_d) * inv_a
                    dx_max = (-b_val + sqrt_d) * inv_a
                    x_start = ti.max(min_x, ti.cast(ti.math.ceil(x_c + dx_min), ti.i32))
                    x_end = ti.min(max_x, ti.cast(ti.math.floor(x_c + dx_max), ti.i32))

                    x = x_start
                    while x <= x_end and is_valid == 1:
                        if check_contour == 1 and alpha_mask[y, x] <= 10.0:
                            count_transparent += 1.0
                        if use_freeze == 1 and freeze_mask[y, x] == 1:
                            is_valid = 0
                        x += 1

                b_val += b_coeff
                discriminant += disc_step_1 + disc_step_2
                disc_step_1 -= 2.0 * inv_rx2_ry2
                y += 1

        # Accumulation Pass (Perfect for coalesced parallel loads)
        if is_valid == 1:
            if use_weight == 0 and use_uncovered == 0:
                dy = ti.cast(min_y, ti.f32) - y_c
                b_val = dy * b_coeff
                discriminant = a - dy * dy * inv_rx2_ry2
                disc_step_1 = -2.0 * dy * inv_rx2_ry2
                disc_step_2 = -inv_rx2_ry2

                y = min_y
                while y <= max_y:
                    if discriminant >= 0.0:
                        sqrt_d = ti.math.sqrt(discriminant)
                        dx_min = (-b_val - sqrt_d) * inv_a
                        dx_max = (-b_val + sqrt_d) * inv_a
                        x_start = ti.max(
                            min_x, ti.cast(ti.math.ceil(x_c + dx_min), ti.i32)
                        )
                        x_end = ti.min(
                            max_x, ti.cast(ti.math.floor(x_c + dx_max), ti.i32)
                        )

                        x = x_start
                        while x <= x_end:
                            t_r = target_r[y, x]
                            t_g = target_g[y, x]
                            t_b = target_b[y, x]

                            c_r = canvas_r[y, x]
                            c_g = canvas_g[y, x]
                            c_b = canvas_b[y, x]

                            count += 1.0
                            sum_t_r += t_r
                            sum_t_g += t_g
                            sum_t_b += t_b

                            sum_c_r += c_r
                            sum_c_g += c_g
                            sum_c_b += c_b

                            sum_c2_r += c_r * c_r
                            sum_c2_g += c_g * c_g
                            sum_c2_b += c_b * c_b

                            sum_ct_r += c_r * t_r
                            sum_ct_g += c_g * t_g
                            sum_ct_b += c_b * t_b
                            x += 1

                    b_val += b_coeff
                    discriminant += disc_step_1 + disc_step_2
                    disc_step_1 -= 2.0 * inv_rx2_ry2
                    y += 1
            else:
                dy = ti.cast(min_y, ti.f32) - y_c
                b_val = dy * b_coeff
                discriminant = a - dy * dy * inv_rx2_ry2
                disc_step_1 = -2.0 * dy * inv_rx2_ry2
                disc_step_2 = -inv_rx2_ry2

                y = min_y
                while y <= max_y:
                    if discriminant >= 0.0:
                        sqrt_d = ti.math.sqrt(discriminant)
                        dx_min = (-b_val - sqrt_d) * inv_a
                        dx_max = (-b_val + sqrt_d) * inv_a
                        x_start = ti.max(
                            min_x, ti.cast(ti.math.ceil(x_c + dx_min), ti.i32)
                        )
                        x_end = ti.min(
                            max_x, ti.cast(ti.math.floor(x_c + dx_max), ti.i32)
                        )

                        x = x_start
                        while x <= x_end:
                            t_r = target_r[y, x]
                            t_g = target_g[y, x]
                            t_b = target_b[y, x]

                            c_r = canvas_r[y, x]
                            c_g = canvas_g[y, x]
                            c_b = canvas_b[y, x]

                            w = 1.0
                            if use_weight == 1:
                                w = weight_map[y, x]
                            if use_uncovered == 1:
                                w = w * uncovered_map[y, x]

                            count += w
                            sum_t_r += t_r * w
                            sum_t_g += t_g * w
                            sum_t_b += t_b * w

                            c_r_w = c_r * w
                            c_g_w = c_g * w
                            c_b_w = c_b * w

                            sum_c_r += c_r_w
                            sum_c_g += c_g_w
                            sum_c_b += c_b_w

                            sum_c2_r += c_r * c_r_w
                            sum_c2_g += c_g * c_g_w
                            sum_c2_b += c_b * c_b_w

                            sum_ct_r += t_r * c_r_w
                            sum_ct_g += t_g * c_g_w
                            sum_ct_b += t_b * c_b_w
                            x += 1

                    b_val += b_coeff
                    discriminant += disc_step_1 + disc_step_2
                    disc_step_1 -= 2.0 * inv_rx2_ry2
                    y += 1

    avg_r = 0.0
    avg_g = 0.0
    avg_b = 0.0
    total_delta_mse = 99999999.0

    if is_valid == 1 and count > 0.0:
        if check_contour == 1 and (count_transparent * 100.0 > count):
            is_valid = 0
        inv_count = 1.0 / count
        avg_r = sum_t_r * inv_count
        avg_g = sum_t_g * inv_count
        avg_b = sum_t_b * inv_count

        a_f = alpha * 0.00392156862745098
        a2_minus_2a = a_f * a_f - 2.0 * a_f
        two_a = 2.0 * a_f
        two_a_one_minus_a = 2.0 * a_f * (1.0 - a_f)

        delta_r = (
            a2_minus_2a * sum_c2_r
            + two_a * sum_ct_r
            + two_a_one_minus_a * avg_r * sum_c_r
            + a2_minus_2a * avg_r * sum_t_r
        )
        delta_g = (
            a2_minus_2a * sum_c2_g
            + two_a * sum_ct_g
            + two_a_one_minus_a * avg_g * sum_c_g
            + a2_minus_2a * avg_g * sum_t_g
        )
        delta_b = (
            a2_minus_2a * sum_c2_b
            + two_a * sum_ct_b
            + two_a_one_minus_a * avg_b * sum_c_b
            + a2_minus_2a * avg_b * sum_t_b
        )

        total_delta_mse = delta_r + delta_g + delta_b

        pass

    return avg_r, avg_g, avg_b, total_delta_mse


@ti.kernel
def taichi_parallel_search(
    target_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    candidates: ti.types.ndarray(
        dtype=ti.f32, ndim=2
    ),  # Shape: (batch_size, 6) -> [x_c, y_c, r_x, r_y, theta, alpha]
    results: ti.types.ndarray(
        dtype=ti.f32, ndim=2
    ),  # Shape: (batch_size, 4) -> [r, g, b, delta_mse]
    alpha_mask: ti.types.ndarray(dtype=ti.f32, ndim=2),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(dtype=ti.uint8, ndim=2),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
    batch_size: ti.i32,
):
    ti.loop_config(block_dim=256)
    for i in range(batch_size):
        # Force access to prevent JIT compiler from optimizing out unused ndarray arguments on some Vulkan drivers
        if i == -1:
            results[0, 0] = (
                alpha_mask[0, 0]
                + ti.cast(freeze_mask[0, 0], ti.f32)
                + weight_map[0, 0]
                + uncovered_map[0, 0]
                + target_r[0, 0]
                + target_g[0, 0]
                + target_b[0, 0]
                + canvas_r[0, 0]
                + canvas_g[0, 0]
                + canvas_b[0, 0]
                + candidates[0, 0]
            )
        x_c = candidates[i, 0]
        y_c = candidates[i, 1]
        r_x = candidates[i, 2]
        r_y = candidates[i, 3]
        theta = candidates[i, 4]
        alpha = candidates[i, 5]

        r, g, b, delta = evaluate_candidate_ti(
            target_r,
            target_g,
            target_b,
            canvas_r,
            canvas_g,
            canvas_b,
            x_c,
            y_c,
            r_x,
            r_y,
            theta,
            alpha,
            alpha_mask,
            check_contour,
            use_freeze,
            freeze_mask,
            use_weight,
            weight_map,
            use_uncovered,
            uncovered_map,
            height,
            width,
        )

        results[i, 0] = r
        results[i, 1] = g
        results[i, 2] = b
        results[i, 3] = delta


@ti.kernel
def compute_raw_error_and_max(
    target: ti.types.ndarray(dtype=ti.f32, ndim=3),
    canvas: ti.types.ndarray(dtype=ti.f32, ndim=3),
    error_prob: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
) -> ti.f32:
    max_err = 0.0
    for y, x in ti.ndrange(height, width):
        diff = 0.0
        for c in ti.static(range(3)):
            diff += ti.abs(target[y, x, c] - canvas[y, x, c])
        # Multiply by precomputed inverse of 3.0 to save on expensive division operation
        diff *= 0.3333333333333333
        ti.atomic_max(max_err, diff)
        error_prob[y, x] = diff
    return max_err


@ti.kernel
def normalize_error_prob(
    error_prob: ti.types.ndarray(dtype=ti.f32, ndim=2),
    max_val: ti.f32,
    height: ti.i32,
    width: ti.i32,
):
    # Precompute division for normalization to convert slow div to fast mul inside the loop
    inv_max_val = 1.0 / max_val if max_val > 0.0 else 0.0
    for y, x in ti.ndrange(height, width):
        if max_val > 0.0:
            error_prob[y, x] = error_prob[y, x] * inv_max_val
        else:
            error_prob[y, x] = 0.0


@ti.kernel
def split_canvas_to_planar_gpu(
    canvas: ti.types.ndarray(dtype=ti.f32, ndim=3),
    canvas_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
):
    for y, x in ti.ndrange(height, width):
        canvas_r[y, x] = canvas[y, x, 0]
        canvas_g[y, x] = canvas[y, x, 1]
        canvas_b[y, x] = canvas[y, x, 2]


@ti.kernel
def update_freeze_mask_gpu(
    target: ti.types.ndarray(dtype=ti.f32, ndim=3),
    canvas: ti.types.ndarray(dtype=ti.f32, ndim=3),
    freeze_mask: ti.types.ndarray(dtype=ti.uint8, ndim=2),
    threshold: ti.f32,
    height: ti.i32,
    width: ti.i32,
):
    for y, x in ti.ndrange(height, width):
        diff = 0.0
        for c in ti.static(range(3)):
            diff += ti.abs(target[y, x, c] - canvas[y, x, c])
        diff *= 0.3333333333333333
        if diff < threshold:
            freeze_mask[y, x] = 1
        else:
            freeze_mask[y, x] = 0


@ti.kernel
def update_uncovered_mask_gpu(
    uncovered_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    best_candidate: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
):
    # Force access to prevent JIT compiler from optimizing out unused ndarray arguments on some Vulkan drivers
    if height == -1:
        uncovered_map[0, 0] = best_candidate[0, 0]

    x_c = best_candidate[0, 0]
    y_c = best_candidate[0, 1]
    r_x = best_candidate[0, 2]
    r_y = best_candidate[0, 3]
    theta = best_candidate[0, 4]

    cos_t = ti.math.cos(theta)
    sin_t = ti.math.sin(theta)

    x_half = ti.math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
    y_half = ti.math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

    min_x = ti.max(0, ti.cast(x_c - x_half, ti.i32))
    max_x = ti.min(width - 1, ti.cast(x_c + x_half, ti.i32))
    min_y = ti.max(0, ti.cast(y_c - y_half, ti.i32))
    max_y = ti.min(height - 1, ti.cast(y_c + y_half, ti.i32))

    inv_rx2 = 1.0 / (r_x * r_x) if r_x > 0.0 else 0.0
    inv_ry2 = 1.0 / (r_y * r_y) if r_y > 0.0 else 0.0

    sin_cos = sin_t * cos_t
    a = inv_rx2 * cos_t * cos_t + inv_ry2 * sin_t * sin_t
    b_coeff = sin_cos * (inv_rx2 - inv_ry2)
    inv_rx2_ry2 = inv_rx2 * inv_ry2

    # Analytical scanline solver: Convert 2D pixel-by-pixel boundary check to 1D start/end bounds calculation
    # Also hoists inverse division outside the loop for performance
    inv_a = 1.0 / a if a > 0.0 else 0.0

    dy = ti.cast(min_y, ti.f32) - y_c
    b_val = dy * b_coeff
    discriminant = a - dy * dy * inv_rx2_ry2
    disc_step_1 = -2.0 * dy * inv_rx2_ry2
    disc_step_2 = -inv_rx2_ry2

    for y in range(min_y, max_y + 1):
        if discriminant >= 0.0:
            sqrt_d = ti.math.sqrt(discriminant)
            dx_min = (-b_val - sqrt_d) * inv_a
            dx_max = (-b_val + sqrt_d) * inv_a
            x_start = ti.max(min_x, ti.cast(ti.math.ceil(x_c + dx_min), ti.i32))
            x_end = ti.min(max_x, ti.cast(ti.math.floor(x_c + dx_max), ti.i32))
            for x in range(x_start, x_end + 1):
                uncovered_map[y, x] = 1.0

        b_val += b_coeff
        discriminant += disc_step_1 + disc_step_2
        disc_step_1 -= 2.0 * inv_rx2_ry2


@ti.kernel
def generate_candidates_gpu(
    candidates: ti.types.ndarray(dtype=ti.f32, ndim=2),
    width: ti.f32,
    height: ti.f32,
    max_r: ti.f32,
    use_importance: ti.i32,
    error_prob: ti.types.ndarray(dtype=ti.f32, ndim=2),
    batch_size: ti.i32,
):
    ti.loop_config(block_dim=256)
    for i in range(batch_size):
        # Force access to prevent JIT compiler from optimizing out error_prob descriptor
        if i == -1:
            candidates[0, 0] = error_prob[0, 0]
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
                    if (
                        ix >= 0
                        and ix < ti.cast(width, ti.i32)
                        and iy >= 0
                        and iy < ti.cast(height, ti.i32)
                    ):
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
    canvas: ti.types.ndarray(dtype=ti.f32, ndim=3),
    best_candidate: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
):
    # Force access to prevent JIT compiler from optimizing out unused ndarray arguments on some Vulkan drivers
    if height == -1:
        canvas[0, 0, 0] = best_candidate[0, 0]

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

    x_half = ti.math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
    y_half = ti.math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

    min_x = ti.max(0, ti.cast(x_c - x_half, ti.i32))
    max_x = ti.min(width - 1, ti.cast(x_c + x_half, ti.i32))
    min_y = ti.max(0, ti.cast(y_c - y_half, ti.i32))
    max_y = ti.min(height - 1, ti.cast(y_c + y_half, ti.i32))

    inv_rx2 = 1.0 / (r_x * r_x) if r_x > 0.0 else 0.0
    inv_ry2 = 1.0 / (r_y * r_y) if r_y > 0.0 else 0.0

    a_f = alpha * 0.00392156862745098
    one_minus_a = 1.0 - a_f

    sin_cos = sin_t * cos_t
    a = inv_rx2 * cos_t * cos_t + inv_ry2 * sin_t * sin_t
    b_coeff = sin_cos * (inv_rx2 - inv_ry2)
    inv_rx2_ry2 = inv_rx2 * inv_ry2

    inv_a = 1.0 / a if a > 0.0 else 0.0

    dy = ti.cast(min_y, ti.f32) - y_c
    b_val = dy * b_coeff
    discriminant = a - dy * dy * inv_rx2_ry2
    disc_step_1 = -2.0 * dy * inv_rx2_ry2
    disc_step_2 = -inv_rx2_ry2

    for y in range(min_y, max_y + 1):
        if discriminant >= 0.0:
            sqrt_d = ti.math.sqrt(discriminant)
            dx_min = (-b_val - sqrt_d) * inv_a
            dx_max = (-b_val + sqrt_d) * inv_a
            x_start = ti.max(min_x, ti.cast(ti.math.ceil(x_c + dx_min), ti.i32))
            x_end = ti.min(max_x, ti.cast(ti.math.floor(x_c + dx_max), ti.i32))

            for x in range(x_start, x_end + 1):
                canvas[y, x, 0] = canvas[y, x, 0] * one_minus_a + r * a_f
                canvas[y, x, 1] = canvas[y, x, 1] * one_minus_a + g * a_f
                canvas[y, x, 2] = canvas[y, x, 2] * one_minus_a + b * a_f

        b_val += b_coeff
        discriminant += disc_step_1 + disc_step_2
        disc_step_1 -= 2.0 * inv_rx2_ry2


@ti.kernel
def find_best_candidate_gpu(
    candidates: ti.types.ndarray(dtype=ti.f32, ndim=2),
    results: ti.types.ndarray(dtype=ti.f32, ndim=2),
    best_candidate: ti.types.ndarray(dtype=ti.f32, ndim=2),
    batch_size: ti.i32,
):
    for _ in range(1):
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
    best_candidate: ti.types.ndarray(dtype=ti.f32, ndim=2),
    climb_candidates: ti.types.ndarray(dtype=ti.f32, ndim=2),
    climb_results: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    alpha_mask: ti.types.ndarray(dtype=ti.f32, ndim=2),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(dtype=ti.uint8, ndim=2),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
    max_r: ti.f32,
    sa_enabled: ti.i32,
    sa_initial_temp: ti.f32,
    sa_cooling_rate: ti.f32,
    optimization_steps: ti.i32,
):
    for i in range(128):
        # Force access to prevent JIT compiler from optimizing out unused ndarray arguments on some Vulkan drivers
        if i == -1:
            climb_results[0, 0] = (
                alpha_mask[0, 0]
                + ti.cast(freeze_mask[0, 0], ti.f32)
                + weight_map[0, 0]
                + uncovered_map[0, 0]
                + target_r[0, 0]
                + target_g[0, 0]
                + target_b[0, 0]
                + canvas_r[0, 0]
                + canvas_g[0, 0]
                + canvas_b[0, 0]
                + climb_candidates[0, 0]
                + best_candidate[0, 0]
            )
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
        inv_opt_steps = (
            1.0 / ti.cast(optimization_steps, ti.f32) if optimization_steps > 0 else 0.0
        )

        for step in range(optimization_steps):
            scale = 1.0 - (ti.cast(step, ti.f32) * inv_opt_steps)

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
                target_r,
                target_g,
                target_b,
                canvas_r,
                canvas_g,
                canvas_b,
                nx_c,
                ny_c,
                nr_x,
                nr_y,
                ntheta,
                nalpha,
                alpha_mask,
                check_contour,
                use_freeze,
                freeze_mask,
                use_weight,
                weight_map,
                use_uncovered,
                uncovered_map,
                height,
                width,
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
    climb_candidates: ti.types.ndarray(dtype=ti.f32, ndim=2),
    climb_results: ti.types.ndarray(dtype=ti.f32, ndim=2),
    best_candidate: ti.types.ndarray(dtype=ti.f32, ndim=2),
):
    for _ in range(1):
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


@ti.func
def lcg_step(seed: ti.uint32) -> ti.uint32:
    return seed * ti.cast(1664525, ti.uint32) + ti.cast(1013904223, ti.uint32)


@ti.kernel
def copy_pbest_gpu(
    src_x: ti.types.ndarray(dtype=ti.f32, ndim=2),
    dst_x: ti.types.ndarray(dtype=ti.f32, ndim=2),
    src_fit: ti.types.ndarray(dtype=ti.f32, ndim=1),
    dst_fit: ti.types.ndarray(dtype=ti.f32, ndim=1),
):
    for i in range(128):
        dst_fit[i] = src_fit[i]
        for j in ti.static(range(6)):
            dst_x[i, j] = src_x[i, j]


@ti.kernel
def taichi_pso_epoch_gpu(
    particles_x: ti.types.ndarray(dtype=ti.f32, ndim=2),
    particles_v: ti.types.ndarray(dtype=ti.f32, ndim=2),
    pbest_x: ti.types.ndarray(dtype=ti.f32, ndim=2),
    pbest_fit: ti.types.ndarray(dtype=ti.f32, ndim=1),
    pbest_x_old: ti.types.ndarray(dtype=ti.f32, ndim=2),
    pbest_fit_old: ti.types.ndarray(dtype=ti.f32, ndim=1),
    seeds: ti.types.ndarray(dtype=ti.uint32, ndim=1),
    target_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    alpha_mask: ti.types.ndarray(dtype=ti.f32, ndim=2),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(dtype=ti.uint8, ndim=2),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
    max_r: ti.f32,
    step_offset: ti.i32,
    total_steps: ti.i32,
):
    ti.loop_config(block_dim=128)
    for i in range(128):
        # Force access to prevent JIT compiler from optimizing out unused ndarray arguments
        if i == -1:
            pbest_fit[0] = (
                alpha_mask[0, 0]
                + ti.cast(freeze_mask[0, 0], ti.f32)
                + weight_map[0, 0]
                + uncovered_map[0, 0]
                + target_r[0, 0]
                + target_g[0, 0]
                + target_b[0, 0]
                + canvas_r[0, 0]
                + canvas_g[0, 0]
                + canvas_b[0, 0]
                + particles_x[0, 0]
                + particles_v[0, 0]
                + pbest_x[0, 0]
            )

        x_c = particles_x[i, 0]
        y_c = particles_x[i, 1]
        r_x = particles_x[i, 2]
        r_y = particles_x[i, 3]
        theta = particles_x[i, 4]
        alpha = particles_x[i, 5]

        vx = particles_v[i, 0]
        vy = particles_v[i, 1]
        vrx = particles_v[i, 2]
        vry = particles_v[i, 3]
        vtheta = particles_v[i, 4]

        seed = seeds[i]

        # 每個 epoch 內部跑 5 步
        for local_step in range(5):
            t = step_offset + local_step
            scale = 1.0 - (ti.cast(t, ti.f32) / ti.cast(total_steps, ti.f32))

            # 動態參數調整
            w = 0.5 * scale + 0.1
            c1 = 2.0
            c2 = 0.1
            is_collapsing = 0
            if t >= total_steps - 5:
                w = 0.0
                c1 = 0.0
                c2 = 1.0
                is_collapsing = 1
            elif t >= ti.cast(total_steps, ti.f32) * 0.7:
                c1 = 0.0
                c2 = 3.0

            l_x = pbest_x_old[i, 0]
            l_y = pbest_x_old[i, 1]
            l_rx = pbest_x_old[i, 2]
            l_ry = pbest_x_old[i, 3]
            l_theta = pbest_x_old[i, 4]

            if t < ti.cast(total_steps, ti.f32) * 0.7:
                # Ring Topology 尋找左右鄰居中最優的
                idx_prev = (i - 1 + 128) % 128
                idx_next = (i + 1) % 128
                min_f = pbest_fit_old[i]
                best_idx = i
                if pbest_fit_old[idx_prev] < min_f:
                    min_f = pbest_fit_old[idx_prev]
                    best_idx = idx_prev
                if pbest_fit_old[idx_next] < min_f:
                    min_f = pbest_fit_old[idx_next]
                    best_idx = idx_next

                l_x = pbest_x_old[best_idx, 0]
                l_y = pbest_x_old[best_idx, 1]
                l_rx = pbest_x_old[best_idx, 2]
                l_ry = pbest_x_old[best_idx, 3]
                l_theta = pbest_x_old[best_idx, 4]
            else:
                # Collapse to Global Best (位於索引 0)
                l_x = pbest_x_old[0, 0]
                l_y = pbest_x_old[0, 1]
                l_rx = pbest_x_old[0, 2]
                l_ry = pbest_x_old[0, 3]
                l_theta = pbest_x_old[0, 4]

            # 產生 LCG 決定性隨機數
            seed = lcg_step(seed)
            r1 = ti.cast(seed, ti.f32) / 4294967296.0
            seed = lcg_step(seed)
            r2 = ti.cast(seed, ti.f32) / 4294967296.0
            if is_collapsing == 1:
                r2 = 1.0

            # 速度更新
            vx = w * vx + c1 * r1 * (pbest_x[i, 0] - x_c) + c2 * r2 * (l_x - x_c)
            vy = w * vy + c1 * r1 * (pbest_x[i, 1] - y_c) + c2 * r2 * (l_y - y_c)
            vrx = w * vrx + c1 * r1 * (pbest_x[i, 2] - r_x) + c2 * r2 * (l_rx - r_x)
            vry = w * vry + c1 * r1 * (pbest_x[i, 3] - r_y) + c2 * r2 * (l_ry - r_y)
            vtheta = (
                w * vtheta
                + c1 * r1 * (pbest_x[i, 4] - theta)
                + c2 * r2 * (l_theta - theta)
            )

            # 限制速度大小防止粒子飛太遠
            max_v_pos = 8.0 * scale
            max_v_size = 6.0 * scale
            max_v_ang = 0.25 * scale
            vx = ti.max(-max_v_pos, ti.min(max_v_pos, vx))
            vy = ti.max(-max_v_pos, ti.min(max_v_pos, vy))
            vrx = ti.max(-max_v_size, ti.min(max_v_size, vrx))
            vry = ti.max(-max_v_size, ti.min(max_v_size, vry))
            vtheta = ti.max(-max_v_ang, ti.min(max_v_ang, vtheta))

            # 位置更新
            x_c += vx
            y_c += vy
            r_x += vrx
            r_y += vry
            theta += vtheta

            # 邊界約束與反彈
            if x_c < 0.0:
                x_c = 0.0
                vx = -vx * 0.5
            elif x_c > ti.cast(width, ti.f32):
                x_c = ti.cast(width, ti.f32)
                vx = -vx * 0.5

            if y_c < 0.0:
                y_c = 0.0
                vy = -vy * 0.5
            elif y_c > ti.cast(height, ti.f32):
                y_c = ti.cast(height, ti.f32)
                vy = -vy * 0.5

            if r_x < 2.0:
                r_x = 2.0
                vrx = -vrx * 0.5
            elif r_x > max_r:
                r_x = max_r
                vrx = -vrx * 0.5

            if r_y < 2.0:
                r_y = 2.0
                vry = -vry * 0.5
            elif r_y > max_r:
                r_y = max_r
                vry = -vry * 0.5

            # 計算當前適應度
            _, _, _, delta = evaluate_candidate_ti(
                target_r,
                target_g,
                target_b,
                canvas_r,
                canvas_g,
                canvas_b,
                x_c,
                y_c,
                r_x,
                r_y,
                theta,
                alpha,
                alpha_mask,
                check_contour,
                use_freeze,
                freeze_mask,
                use_weight,
                weight_map,
                use_uncovered,
                uncovered_map,
                height,
                width,
            )

            # 更新個體歷史最佳
            if delta < pbest_fit[i]:
                pbest_fit[i] = delta
                pbest_x[i, 0] = x_c
                pbest_x[i, 1] = y_c
                pbest_x[i, 2] = r_x
                pbest_x[i, 3] = r_y
                pbest_x[i, 4] = theta
                pbest_x[i, 5] = alpha

        # 將狀態寫回
        particles_x[i, 0] = x_c
        particles_x[i, 1] = y_c
        particles_x[i, 2] = r_x
        particles_x[i, 3] = r_y
        particles_x[i, 4] = theta
        particles_x[i, 5] = alpha

        particles_v[i, 0] = vx
        particles_v[i, 1] = vy
        particles_v[i, 2] = vrx
        particles_v[i, 3] = vry
        particles_v[i, 4] = vtheta

        seeds[i] = seed


@ti.kernel
def finalize_pso_result_gpu(
    pbest_x: ti.types.ndarray(dtype=ti.f32, ndim=2),
    pbest_fit: ti.types.ndarray(dtype=ti.f32, ndim=1),
    best_candidate: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    target_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_r: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_g: ti.types.ndarray(dtype=ti.f32, ndim=2),
    canvas_b: ti.types.ndarray(dtype=ti.f32, ndim=2),
    alpha_mask: ti.types.ndarray(dtype=ti.f32, ndim=2),
    check_contour: ti.i32,
    use_freeze: ti.i32,
    freeze_mask: ti.types.ndarray(dtype=ti.uint8, ndim=2),
    use_weight: ti.i32,
    weight_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    use_uncovered: ti.i32,
    uncovered_map: ti.types.ndarray(dtype=ti.f32, ndim=2),
    height: ti.i32,
    width: ti.i32,
):
    for _ in range(1):
        x_c = pbest_x[0, 0]
        y_c = pbest_x[0, 1]
        r_x = pbest_x[0, 2]
        r_y = pbest_x[0, 3]
        theta = pbest_x[0, 4]
        alpha = pbest_x[0, 5]

        r, g, b, delta = evaluate_candidate_ti(
            target_r,
            target_g,
            target_b,
            canvas_r,
            canvas_g,
            canvas_b,
            x_c,
            y_c,
            r_x,
            r_y,
            theta,
            alpha,
            alpha_mask,
            check_contour,
            use_freeze,
            freeze_mask,
            use_weight,
            weight_map,
            use_uncovered,
            uncovered_map,
            height,
            width,
        )

        best_candidate[0, 0] = x_c
        best_candidate[0, 1] = y_c
        best_candidate[0, 2] = r_x
        best_candidate[0, 3] = r_y
        best_candidate[0, 4] = theta
        best_candidate[0, 5] = alpha
        best_candidate[0, 6] = r
        best_candidate[0, 7] = g
        best_candidate[0, 8] = b
        best_candidate[0, 9] = delta


class TaichiEvaluator(BaseEvaluator):
    _is_taichi_initialized = False
    _taichi_arch_name = "N/A"

    def __init__(
        self,
        target_image: np.ndarray,
        alpha_mask: np.ndarray = None,
        taichi_arch: str = None,
        taichi_device_id: int = None,
    ):
        super().__init__(target_image, alpha_mask)
        self.initialized = False
        self.arch_name = "N/A"

        if HAS_TAICHI:
            if TaichiEvaluator._is_taichi_initialized:
                self.initialized = True
                self.arch_name = TaichiEvaluator._taichi_arch_name
            else:
                # 阻斷隱式 Vulkan Layers（如 Game Capture, OBS, Discord overlay 等）注入，防止產生大量垃圾調試輸出並提升啟動穩定度
                import os

                os.environ["VK_LOADER_LAYERS_DISABLE"] = "~implicit~"
                os.environ["DISABLE_OBS_CAPTURE"] = "1"

                arch_map = {
                    "Vulkan": ti.vulkan,
                    "CUDA": ti.cuda,
                    "OpenGL": ti.opengl,
                    "CPU": ti.cpu,
                }

                if taichi_device_id is not None:
                    import os

                    os.environ["CUDA_VISIBLE_DEVICES"] = str(taichi_device_id)
                    os.environ["VULKAN_DEVICE_INDEX"] = str(taichi_device_id)
                    os.environ["VULKAN_PHYSICAL_DEVICE_INDEX"] = str(taichi_device_id)

                backends = []
                if taichi_arch and taichi_arch in arch_map:
                    backends.append(
                        (
                            arch_map[taichi_arch],
                            f"GPU - {taichi_arch}" if taichi_arch != "CPU" else "CPU",
                        )
                    )
                else:
                    backends = [
                        (ti.vulkan, "GPU - Vulkan"),
                        (ti.cuda, "GPU - CUDA"),
                        (ti.opengl, "GPU - OpenGL"),
                        (ti.cpu, "CPU"),
                    ]

                for arch, name in backends:
                    try:
                        ti.init(arch=arch, log_level=ti.WARN)
                        # Verify backend with a test allocation
                        test = ti.field(dtype=ti.f32, shape=1)
                        test[0] = 1.0

                        self.initialized = True
                        self.arch_name = name
                        TaichiEvaluator._is_taichi_initialized = True
                        TaichiEvaluator._taichi_arch_name = name
                        print(
                            f"[Taichi JIT Backend] Successfully initialized backend: {name} (Device ID: {taichi_device_id})"
                        )
                        break
                    except Exception as e:
                        print(
                            f"[Taichi Backend Warning] Attempt to initialize {arch} failed: {e}"
                        )
                        continue

            if self.initialized:
                try:
                    # Pre-upload target image to VRAM (HWC)
                    self.ti_target = ti.ndarray(dtype=ti.f32, shape=target_image.shape)
                    self.ti_target.from_numpy(target_image.astype(np.float32))

                    # Pre-upload planar target channels to VRAM (R, G, B channels)
                    self.ti_target_r = ti.ndarray(
                        dtype=ti.f32, shape=self.target_r.shape
                    )
                    self.ti_target_g = ti.ndarray(
                        dtype=ti.f32, shape=self.target_g.shape
                    )
                    self.ti_target_b = ti.ndarray(
                        dtype=ti.f32, shape=self.target_b.shape
                    )
                    self.ti_target_r.from_numpy(self.target_r)
                    self.ti_target_g.from_numpy(self.target_g)
                    self.ti_target_b.from_numpy(self.target_b)

                    self.ti_canvas = ti.ndarray(dtype=ti.f32, shape=target_image.shape)

                    # Pre-allocate planar canvas channels in VRAM (R, G, B channels)
                    self.ti_canvas_r = ti.ndarray(
                        dtype=ti.f32, shape=self.target_r.shape
                    )
                    self.ti_canvas_g = ti.ndarray(
                        dtype=ti.f32, shape=self.target_g.shape
                    )
                    self.ti_canvas_b = ti.ndarray(
                        dtype=ti.f32, shape=self.target_b.shape
                    )

                    if alpha_mask is not None:
                        self.ti_alpha = ti.ndarray(dtype=ti.f32, shape=alpha_mask.shape)
                        self.ti_alpha.from_numpy(alpha_mask.astype(np.float32))
                    else:
                        # 1x1 placeholder
                        self.ti_alpha = ti.ndarray(dtype=ti.f32, shape=(1, 1))
                        self.ti_alpha.from_numpy(np.zeros((1, 1), dtype=np.float32))

                    # Pre-allocate canvas-sized buffers
                    height, width, _ = target_image.shape
                    self.ti_freeze = ti.ndarray(dtype=ti.uint8, shape=(height, width))
                    self.ti_weight = ti.ndarray(dtype=ti.f32, shape=(height, width))
                    self.ti_uncovered = ti.ndarray(dtype=ti.f32, shape=(height, width))
                    self.ti_error_prob = ti.ndarray(dtype=ti.f32, shape=(height, width))

                    # 1x1 placeholders for unused optional maps
                    self.ti_empty_u8 = ti.ndarray(dtype=ti.uint8, shape=(1, 1))
                    self.ti_empty_u8.from_numpy(np.zeros((1, 1), dtype=np.uint8))
                    self.ti_empty_f32 = ti.ndarray(dtype=ti.f32, shape=(1, 1))
                    self.ti_empty_f32.from_numpy(np.zeros((1, 1), dtype=np.float32))

                    # GPU pipeline buffers for hill climbing
                    self.ti_best_candidate = ti.ndarray(dtype=ti.f32, shape=(1, 10))
                    self.ti_climb_candidates = ti.ndarray(dtype=ti.f32, shape=(128, 6))
                    self.ti_climb_results = ti.ndarray(dtype=ti.f32, shape=(128, 4))

                    # GPU PSO buffers
                    self.ti_particles_x = ti.ndarray(dtype=ti.f32, shape=(128, 6))
                    self.ti_particles_v = ti.ndarray(dtype=ti.f32, shape=(128, 5))
                    self.ti_pbest_x = ti.ndarray(dtype=ti.f32, shape=(128, 6))
                    self.ti_pbest_fit = ti.ndarray(dtype=ti.f32, shape=(128,))
                    self.ti_pbest_x_old = ti.ndarray(dtype=ti.f32, shape=(128, 6))
                    self.ti_pbest_fit_old = ti.ndarray(dtype=ti.f32, shape=(128,))
                    self.ti_seeds = ti.ndarray(dtype=ti.uint32, shape=(128,))

                    # 初始化 seeds
                    seeds_np = (
                        np.arange(128, dtype=np.uint32) * 1664525 + 1013904223
                    ).astype(np.uint32)
                    self.ti_seeds.from_numpy(seeds_np)
                except Exception as e:
                    print(f"[Taichi JIT VRAM Allocation Error] {e}")
                    self.initialized = False

    def get_name(self) -> str:
        return f"Taichi JIT ({self.arch_name})"

    def is_available(self) -> bool:
        return HAS_TAICHI and self.initialized

    def get_device_type(self) -> str:
        return "CPU" if self.arch_name == "CPU" else "GPU"

    def search_best_shape(
        self, current_canvas: np.ndarray, batch_size: int, params: dict
    ) -> tuple:
        if not self.is_available():
            raise RuntimeError(
                "Taichi JIT Evaluator is not available or failed to initialize backend."
            )

        height, width, _ = self.target_image.shape

        # 動態批次大小調整 (Dynamic Batch Size Adjustment)
        original_batch_size = batch_size
        current_max_r = params.get("current_max_r")
        base_max_r = max(10.0, min(width, height) / 3.0)

        if current_max_r is None:
            current_max_r = base_max_r

        r_ratio = current_max_r / base_max_r

        if self.get_device_type() == "GPU":
            # GPU 模式下，形狀小時放大批次以榨乾 GPU 算力；形狀大時縮小批次以防止 TDR。
            if r_ratio > 0.75:
                factor = 0.5
            elif r_ratio > 0.4:
                factor = 1.0
            elif r_ratio > 0.2:
                factor = 2.0
            else:
                factor = 4.0

            adjusted_batch_size = int(original_batch_size * factor)
            # 對齊 128 的倍數
            adjusted_batch_size = max(128, (adjusted_batch_size // 128) * 128)
            batch_size = min(131072, adjusted_batch_size)
        else:
            # CPU 模式下，防止 Cache Thrashing 與調度瓶頸
            factor = 0.5 if r_ratio > 0.5 else 1.0
            adjusted_batch_size = int(original_batch_size * factor)
            adjusted_batch_size = max(128, (adjusted_batch_size // 128) * 128)
            batch_size = min(2000, adjusted_batch_size)

        if not hasattr(self, "canvas_initialized") or not self.canvas_initialized:
            self.ti_canvas.from_numpy(current_canvas.astype(np.float32))
            self.canvas_initialized = True

        # GPU 端 VRAM 內部動態分拆 Canvas 通道 (HWC -> Planar)
        split_canvas_to_planar_gpu(
            self.ti_canvas,
            self.ti_canvas_r,
            self.ti_canvas_g,
            self.ti_canvas_b,
            height,
            width,
        )
        max_r = max(10.0, min(width, height) / 3.0)
        current_max_r = params.get("current_max_r")
        if current_max_r is not None:
            max_r = min(max_r, current_max_r)

        use_importance = params.get("use_importance", False)
        error_prob_np = params.get("error_prob")

        if use_importance and error_prob_np is not None and error_prob_np.shape[0] > 1:
            max_err_val = compute_raw_error_and_max(
                self.ti_target,
                self.ti_canvas,
                self.ti_error_prob,
                height,
                width,
            )
            normalize_error_prob(self.ti_error_prob, max_err_val, height, width)

        use_freeze = 1 if params.get("use_freeze", False) else 0
        freeze_mask_np = params.get("freeze_mask")
        ti_freeze_ref = self.ti_empty_u8
        if use_freeze == 1 and freeze_mask_np is not None:
            self.ti_freeze.from_numpy(freeze_mask_np)
            ti_freeze_ref = self.ti_freeze

        use_weight = 1 if params.get("use_weight", False) else 0
        weight_map_np = params.get("weight_map")
        ti_weight_ref = self.ti_empty_f32
        if use_weight == 1 and weight_map_np is not None:
            self.ti_weight.from_numpy(weight_map_np)
            ti_weight_ref = self.ti_weight

        use_uncovered = 1 if params.get("use_uncovered", False) else 0
        uncovered_map_np = params.get("uncovered_map")
        ti_uncovered_ref = self.ti_empty_f32
        if use_uncovered == 1 and uncovered_map_np is not None:
            self.ti_uncovered.from_numpy(uncovered_map_np)
            ti_uncovered_ref = self.ti_uncovered

        # VRAM Max-Capacity 顯存緩存分配快取機制
        current_capacity = (
            self.ti_candidates.shape[0] if hasattr(self, "ti_candidates") else 0
        )
        if batch_size > current_capacity:
            # 超出當前容量才重新配置擴大
            alloc_capacity = (
                batch_size * 4 if self.get_device_type() == "GPU" else batch_size
            )
            alloc_capacity = max(128, (alloc_capacity // 128) * 128)
            self.ti_candidates = ti.ndarray(dtype=ti.f32, shape=(alloc_capacity, 6))
            self.ti_results = ti.ndarray(dtype=ti.f32, shape=(alloc_capacity, 4))

        generate_candidates_gpu(
            self.ti_candidates,
            float(width),
            float(height),
            float(max_r),
            1 if (use_importance and error_prob_np is not None) else 0,
            self.ti_error_prob,
            batch_size,
        )

        # Disable contour check if alpha_mask is a placeholder
        check_contour = params.get("check_contour", False)
        if self.alpha_mask is None or self.alpha_mask.shape == (1, 1):
            check_contour = False
        check_contour_jit = 1 if check_contour else 0

        taichi_parallel_search(
            self.ti_target_r,
            self.ti_target_g,
            self.ti_target_b,
            self.ti_canvas_r,
            self.ti_canvas_g,
            self.ti_canvas_b,
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
            batch_size,
        )

        find_best_candidate_gpu(
            self.ti_candidates, self.ti_results, self.ti_best_candidate, batch_size
        )

        use_pure_gpu = params.get("use_pure_gpu", False)

        sa_enabled = 1 if params.get("sa_enabled", False) else 0
        sa_initial_temp = float(params.get("sa_initial_temp", 5000.0))
        sa_cooling_rate = float(params.get("sa_cooling_rate", 0.95))
        optimization_steps = params.get("optimization_steps", 50)

        if use_pure_gpu:
            # 準備 PSO 初始狀態
            best_candidate_np = self.ti_best_candidate.to_numpy()
            best_x = best_candidate_np[0, 0:6]
            best_delta = best_candidate_np[0, 9]

            # 決定性粒子位置初始化 ( NumPy 隨機生成器配合固定 seed )
            rng = np.random.default_rng(seed=42)
            particles_x_np = np.zeros((128, 6), dtype=np.float32)
            particles_x_np[0] = best_x

            for k in range(1, 128):
                particles_x_np[k, 0] = np.clip(
                    best_x[0] + rng.normal(0, 8.0), 0.0, width
                )
                particles_x_np[k, 1] = np.clip(
                    best_x[1] + rng.normal(0, 8.0), 0.0, height
                )
                particles_x_np[k, 2] = np.clip(
                    best_x[2] + rng.normal(0, 6.0), 2.0, max_r
                )
                particles_x_np[k, 3] = np.clip(
                    best_x[3] + rng.normal(0, 6.0), 2.0, max_r
                )
                particles_x_np[k, 4] = best_x[4] + rng.normal(0, 0.25)
                particles_x_np[k, 5] = 255.0

            # 寫入 VRAM
            self.ti_particles_x.from_numpy(particles_x_np)
            self.ti_pbest_x.from_numpy(particles_x_np)

            # 初始化速度與 fit
            particles_v_np = np.zeros((128, 5), dtype=np.float32)
            self.ti_particles_v.from_numpy(particles_v_np)

            pbest_fit_np = np.full((128,), 999999999.0, dtype=np.float32)
            pbest_fit_np[0] = best_delta
            self.ti_pbest_fit.from_numpy(pbest_fit_np)

            # 重設 seeds 確保多次執行的隨機序列 100% 相同
            seeds_np = (np.arange(128, dtype=np.uint32) * 1664525 + 1013904223).astype(
                np.uint32
            )
            self.ti_seeds.from_numpy(seeds_np)

            # 執行 PSO Epoch 同步調度
            total_steps = optimization_steps
            steps_per_epoch = 5
            num_epochs = max(1, total_steps // steps_per_epoch)

            for epoch in range(num_epochs):
                step_offset = epoch * steps_per_epoch
                # 拷貝當前 pbest 到 old buffers
                copy_pbest_gpu(
                    self.ti_pbest_x,
                    self.ti_pbest_x_old,
                    self.ti_pbest_fit,
                    self.ti_pbest_fit_old,
                )
                taichi_pso_epoch_gpu(
                    self.ti_particles_x,
                    self.ti_particles_v,
                    self.ti_pbest_x,
                    self.ti_pbest_fit,
                    self.ti_pbest_x_old,
                    self.ti_pbest_fit_old,
                    self.ti_seeds,
                    self.ti_target_r,
                    self.ti_target_g,
                    self.ti_target_b,
                    self.ti_canvas_r,
                    self.ti_canvas_g,
                    self.ti_canvas_b,
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
                    step_offset,
                    total_steps,
                )

                # 在 Python 端做排序，以確保當前全域最佳解位於索引 0
                pbest_fit_np = self.ti_pbest_fit.to_numpy()
                best_idx = np.argmin(pbest_fit_np)
                if best_idx != 0:
                    pbest_x_np = self.ti_pbest_x.to_numpy()

                    # 交換
                    pbest_x_np[[0, best_idx]] = pbest_x_np[[best_idx, 0]]
                    pbest_fit_np[[0, best_idx]] = pbest_fit_np[[best_idx, 0]]

                    self.ti_pbest_x.from_numpy(pbest_x_np)
                    self.ti_pbest_fit.from_numpy(pbest_fit_np)

            # 執行 finalize kernel 來重新獲得正確的 r, g, b 並寫入 ti_best_candidate
            finalize_pso_result_gpu(
                self.ti_pbest_x,
                self.ti_pbest_fit,
                self.ti_best_candidate,
                self.ti_target_r,
                self.ti_target_g,
                self.ti_target_b,
                self.ti_canvas_r,
                self.ti_canvas_g,
                self.ti_canvas_b,
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
            )

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
        else:
            # Hybrid mode: download best candidate, run Numba CPU hill climb, write back
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

            freeze_mask_np_dummy = (
                freeze_mask_np
                if (use_freeze == 1 and freeze_mask_np is not None)
                else np.zeros((1, 1), dtype=np.uint8)
            )
            weight_map_np_dummy = (
                weight_map_np
                if (use_weight == 1 and weight_map_np is not None)
                else np.ones((1, 1), dtype=np.float32)
            )
            uncovered_map_np_dummy = (
                uncovered_map_np
                if (use_uncovered == 1 and uncovered_map_np is not None)
                else np.ones((1, 1), dtype=np.float32)
            )

            try:
                from evaluators import numba_kernels

                canvas_r = np.ascontiguousarray(current_canvas[:, :, 0])
                canvas_g = np.ascontiguousarray(current_canvas[:, :, 1])
                canvas_b = np.ascontiguousarray(current_canvas[:, :, 2])

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
                        int(alpha),
                        r,
                        g,
                        b,
                        delta,
                        optimization_steps,
                        self.alpha_mask
                        if self.alpha_mask is not None
                        else np.zeros((1, 1), dtype=np.float32),
                        True if check_contour_jit == 1 else False,
                        sa_enabled=True if sa_enabled == 1 else False,
                        initial_temp=sa_initial_temp,
                        cooling_rate=sa_cooling_rate,
                        max_r=max_r,
                        use_freeze=True if use_freeze == 1 else False,
                        freeze_mask=freeze_mask_np_dummy,
                        use_weight=True if use_weight == 1 else False,
                        weight_map=weight_map_np_dummy,
                        use_uncovered=True if use_uncovered == 1 else False,
                        uncovered_map=uncovered_map_np_dummy,
                    )
                )
            except Exception as e:
                print(
                    f"[Taichi Evaluator JIT Warning] Numba CPU fallback failed during serial hill climb: {e}"
                )

            # Write optimized result back to GPU
            best_candidate_np[0, 0] = x_c
            best_candidate_np[0, 1] = y_c
            best_candidate_np[0, 2] = r_x
            best_candidate_np[0, 3] = r_y
            best_candidate_np[0, 4] = theta
            best_candidate_np[0, 5] = alpha
            best_candidate_np[0, 6] = r
            best_candidate_np[0, 7] = g
            best_candidate_np[0, 8] = b
            best_candidate_np[0, 9] = delta
            self.ti_best_candidate.from_numpy(best_candidate_np)

        # Draw the best shape directly on GPU canvas
        draw_ellipse_gpu(self.ti_canvas, self.ti_best_candidate, height, width)

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

        from evaluators import numba_kernels

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

        from evaluators.numba_evaluator import NumbaEvaluator

        numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
        numba_eval.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)

        # Sync GPU canvas buffer
        if self.initialized:
            self.ti_canvas.from_numpy(canvas.astype(np.float32))
            self.canvas_initialized = True

    def run_redundancy_check(
        self, shapes_list: list, width: int, height: int, final_check: bool = False
    ) -> list:
        from evaluators.numba_evaluator import NumbaEvaluator

        numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
        return numba_eval.run_redundancy_check(shapes_list, width, height, final_check)

    def init_uncovered_map(
        self, width: int, height: int, has_alpha: bool, bias: float
    ) -> np.ndarray:
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

    def update_uncovered_mask(
        self,
        uncovered_map: np.ndarray,
        x_c: float,
        y_c: float,
        r_x: float,
        r_y: float,
        theta_rad: float,
    ) -> None:
        from evaluators.numba_evaluator import NumbaEvaluator

        numba_eval = NumbaEvaluator(self.target_image, self.alpha_mask)
        numba_eval.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta_rad)

    def cleanup(self) -> None:
        pass
