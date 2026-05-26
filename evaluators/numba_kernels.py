#!/usr/bin/env python3
import math

import numba
import numpy as np


@numba.jit(nopython=True, fastmath=True, cache=True)
def evaluate_candidate(
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
):
    """Evaluates a candidate rotated ellipse against the target image channels.
    Uses separate contiguous planar target/canvas channels (unit stride) and an
    analytical scanline solver to solve the boundary of the ellipse for each row y,
    eliminating the inner loop 'if' condition and early returns to unlock AVX2 vectorization.
    """
    height = target_r.shape[0]
    width = target_r.shape[1]

    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))

    # Bounding box of the rotated ellipse
    x_half = math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
    y_half = math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

    if (
        (x_c - x_half < 0.0)
        or (x_c + x_half > np.float32(width))
        or (y_c - y_half < 0.0)
        or (y_c + y_half > np.float32(height))
    ):
        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)

    min_x = max(0, int(x_c - x_half))
    max_x = min(width - 1, int(x_c + x_half))
    min_y = max(0, int(y_c - y_half))
    max_y = min(height - 1, int(y_c + y_half))

    inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
    inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)

    # Precomputed constant terms for quadratic boundary solving
    sin_cos = sin_t * cos_t
    a = inv_rx2 * cos_t * cos_t + inv_ry2 * sin_t * sin_t
    b_coeff = sin_cos * (inv_rx2 - inv_ry2)
    c_y_coeff = inv_rx2 * sin_t * sin_t + inv_ry2 * cos_t * cos_t

    # Validation Pass: Check contour and freeze mask first in a scalar loop with early return
    # This isolates early exits from the heavy accumulation loop so LLVM can vectorize
    if check_contour or use_freeze:
        for y in range(min_y, max_y + 1):
            dy = np.float32(y - y_c)
            b_val = dy * b_coeff
            c_val = dy * dy * c_y_coeff - 1.0
            discriminant = b_val * b_val - a * c_val
            if discriminant >= 0.0:
                sqrt_d = math.sqrt(discriminant)
                dx_min = (-b_val - sqrt_d) / a
                dx_max = (-b_val + sqrt_d) / a
                x_start = max(min_x, int(math.ceil(x_c + dx_min)))
                x_end = min(max_x, int(math.floor(x_c + dx_max)))

                for x in range(x_start, x_end + 1):
                    if check_contour and alpha_mask[y, x] <= 10.0:
                        return (
                            np.float32(0.0),
                            np.float32(0.0),
                            np.float32(0.0),
                            np.float32(99999999.0),
                        )
                    if use_freeze and freeze_mask[y, x] == 1:
                        return (
                            np.float32(0.0),
                            np.float32(0.0),
                            np.float32(0.0),
                            np.float32(99999999.0),
                        )

    # Accumulation Pass variables
    count = 0.0
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

    # Heavy Accumulation Loop: Contiguous memory access, zero branching, highly vectorizable (AVX2/FMA3)
    for y in range(min_y, max_y + 1):
        dy = np.float32(y - y_c)
        b_val = dy * b_coeff
        c_val = dy * dy * c_y_coeff - 1.0
        discriminant = b_val * b_val - a * c_val
        if discriminant >= 0.0:
            sqrt_d = math.sqrt(discriminant)
            dx_min = (-b_val - sqrt_d) / a
            dx_max = (-b_val + sqrt_d) / a
            x_start = max(min_x, int(math.ceil(x_c + dx_min)))
            x_end = min(max_x, int(math.floor(x_c + dx_max)))

            for x in range(x_start, x_end + 1):
                t_r = target_r[y, x]
                t_g = target_g[y, x]
                t_b = target_b[y, x]

                c_r = canvas_r[y, x]
                c_g = canvas_g[y, x]
                c_b = canvas_b[y, x]

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

    if count == 0:
        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)

    avg_r = sum_t_r / count
    avg_g = sum_t_g / count
    avg_b = sum_t_b / count

    a_f = np.float32(alpha / 255.0)
    a2_minus_2a = np.float32(a_f * a_f - 2.0 * a_f)
    two_a = np.float32(2.0 * a_f)
    two_a_one_minus_a = np.float32(2.0 * a_f * (1.0 - a_f))

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

    return avg_r, avg_g, avg_b, total_delta_mse


@numba.jit(nopython=True, fastmath=True, cache=True)
def draw_ellipse(canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha):
    """Draws the selected best ellipse onto the canvas with Strength Reduction."""
    height = canvas.shape[0]
    width = canvas.shape[1]

    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))

    x_half = math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
    y_half = math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

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


@numba.jit(nopython=True, fastmath=True, cache=True)
def init_uncovered_map(width, height, has_alpha, alpha_mask, bias):
    """Initializes the uncovered weight map. Foreground pixels are prioritized with higher weight bias."""
    uncovered_map = np.ones((height, width), dtype=np.float32)
    if has_alpha:
        for y in range(height):
            for x in range(width):
                if alpha_mask[y, x] > 10.0:
                    uncovered_map[y, x] = np.float32(bias)
    else:
        uncovered_map[:] = np.float32(bias)
    return uncovered_map


@numba.jit(nopython=True, fastmath=True, cache=True)
def update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta):
    """Updates the uncovered map when a new shape is drawn, resetting covered pixels to 1.0 weight."""
    height = uncovered_map.shape[0]
    width = uncovered_map.shape[1]

    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))

    x_half = math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
    y_half = math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

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


@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def parallel_random_search(
    target_r,
    target_g,
    target_b,
    canvas_r,
    canvas_g,
    canvas_b,
    num_candidates,
    width,
    height,
    max_r,
    alpha_mask,
    check_contour,
    use_importance,
    error_prob,
    use_freeze=False,
    freeze_mask=None,
    use_weight=False,
    weight_map=None,
    use_uncovered=False,
    uncovered_map=None,
):

    if use_importance and error_prob.shape[0] > 1:
        x_c_arr = np.zeros(num_candidates, dtype=np.float32)
        y_c_arr = np.zeros(num_candidates, dtype=np.float32)
        for i in numba.prange(num_candidates):
            keep = False
            # limit to 100 attempts to avoid hanging
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
        x_c_arr = np.random.uniform(0.0, float(width), num_candidates).astype(
            np.float32
        )
        y_c_arr = np.random.uniform(0.0, float(height), num_candidates).astype(
            np.float32
        )

    r_x_arr = np.random.uniform(2.0, max_r, num_candidates).astype(np.float32)
    r_y_arr = np.random.uniform(2.0, max_r, num_candidates).astype(np.float32)
    theta_arr = np.random.uniform(0.0, 2.0 * math.pi, num_candidates).astype(np.float32)
    alpha_arr = np.full(num_candidates, 255.0, dtype=np.float32)

    deltas = np.zeros(num_candidates, dtype=np.float32)
    colors = np.zeros((num_candidates, 3), dtype=np.float32)

    for i in numba.prange(num_candidates):
        r, g, b, delta = evaluate_candidate(
            target_r,
            target_g,
            target_b,
            canvas_r,
            canvas_g,
            canvas_b,
            x_c_arr[i],
            y_c_arr[i],
            r_x_arr[i],
            r_y_arr[i],
            theta_arr[i],
            int(alpha_arr[i]),
            alpha_mask,
            check_contour,
            use_freeze,
            freeze_mask,
            use_weight,
            weight_map,
            use_uncovered,
            uncovered_map,
        )
        deltas[i] = np.float32(delta)
        colors[i, 0] = np.float32(r)
        colors[i, 1] = np.float32(g)
        colors[i, 2] = np.float32(b)

    best_idx = np.argmin(deltas)

    return (
        x_c_arr[best_idx],
        y_c_arr[best_idx],
        r_x_arr[best_idx],
        r_y_arr[best_idx],
        theta_arr[best_idx],
        int(alpha_arr[best_idx]),
        colors[best_idx, 0],
        colors[best_idx, 1],
        colors[best_idx, 2],
        deltas[best_idx],
    )


@numba.jit(nopython=True, fastmath=True, cache=True)
def serial_hill_climb(
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
    r,
    g,
    b,
    best_delta,
    optimization_steps,
    alpha_mask,
    check_contour,
    sa_enabled=False,
    initial_temp=5000.0,
    cooling_rate=0.95,
    max_r=999.0,
    use_freeze=False,
    freeze_mask=None,
    use_weight=False,
    weight_map=None,
    use_uncovered=False,
    uncovered_map=None,
):
    curr_x_c = np.float32(x_c)
    curr_y_c = np.float32(y_c)
    curr_r_x = np.float32(r_x)
    curr_r_y = np.float32(r_y)
    curr_theta = np.float32(theta)
    curr_alpha = int(alpha)
    curr_r = np.float32(r)
    curr_g = np.float32(g)
    curr_b = np.float32(b)
    curr_delta = np.float32(best_delta)

    T = np.float32(initial_temp)
    c_rate = np.float32(cooling_rate)
    max_r_f = np.float32(max_r)

    for step in range(optimization_steps):
        scale = np.float32(1.0 - (step / optimization_steps))

        nx_c = curr_x_c + np.float32(np.random.normal(0.0, 8.0 * scale))
        ny_c = curr_y_c + np.float32(np.random.normal(0.0, 8.0 * scale))
        nr_x = max(
            np.float32(2.0),
            min(max_r_f, curr_r_x + np.float32(np.random.normal(0.0, 6.0 * scale))),
        )
        nr_y = max(
            np.float32(2.0),
            min(max_r_f, curr_r_y + np.float32(np.random.normal(0.0, 6.0 * scale))),
        )
        ntheta = curr_theta + np.float32(np.random.normal(0.0, 0.25 * scale))
        nalpha = 255

        nr, ng, nb, delta = evaluate_candidate(
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

    return (
        float(curr_x_c),
        float(curr_y_c),
        float(curr_r_x),
        float(curr_r_y),
        float(curr_theta),
        int(curr_r),
        int(curr_g),
        int(curr_b),
        curr_alpha,
        float(curr_delta),
    )


@numba.jit(nopython=True, fastmath=True, cache=True)
def run_redundancy_check_jit(shapes_data, shapes_color, shapes_type, width, height):
    """JIT-accelerated backward occlusion tracing."""
    num_shapes = len(shapes_type)
    visible_mask = np.ones(num_shapes, dtype=np.bool_)

    occlusion = np.zeros((height, width), dtype=np.float32)

    for i in range(num_shapes - 1, -1, -1):
        s_type = shapes_type[i]

        if s_type == 1:
            visible_mask[i] = True

            for y in range(height):
                for x in range(width):
                    occlusion[y, x] = 1.0
            continue

        x_c = np.float32(shapes_data[i, 0])
        y_c = np.float32(shapes_data[i, 1])
        r_x = np.float32(shapes_data[i, 2])
        r_y = np.float32(shapes_data[i, 3])
        theta = np.float32(shapes_data[i, 4])

        alpha = shapes_color[i, 3]
        a_f = np.float32(alpha / 255.0)

        cos_t = np.float32(math.cos(theta))
        sin_t = np.float32(math.sin(theta))

        x_half = math.sqrt(r_x * r_x * cos_t * cos_t + r_y * r_y * sin_t * sin_t)
        y_half = math.sqrt(r_x * r_x * sin_t * sin_t + r_y * r_y * cos_t * cos_t)

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

    return visible_mask


@numba.jit(nopython=True, fastmath=True, cache=True)
def rebuild_canvas_jit(canvas, avg_r, avg_g, avg_b, avg_a, shapes_data, shapes_color):
    """JIT accelerated fast canvas background reset and shape drawing loop."""
    canvas[:, :, 0] = np.float32(avg_r)
    canvas[:, :, 1] = np.float32(avg_g)
    canvas[:, :, 2] = np.float32(avg_b)
    if canvas.shape[2] == 4:
        canvas[:, :, 3] = np.float32(avg_a)

    num_shapes = len(shapes_data)
    for i in range(num_shapes):
        draw_ellipse(
            canvas,
            shapes_data[i, 0],
            shapes_data[i, 1],
            shapes_data[i, 2],
            shapes_data[i, 3],
            shapes_data[i, 4],
            shapes_color[i, 0],
            shapes_color[i, 1],
            shapes_color[i, 2],
            shapes_color[i, 3],
        )
