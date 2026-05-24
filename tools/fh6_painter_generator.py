#!/usr/bin/env python3
import sys
import os
import time
import math
import random
import json
import argparse
import gc


# --- Check dependencies ---
HAS_DEPENDENCIES = True
try:
    from PIL import Image
    import numpy as np
    import numba
except ImportError:
    HAS_DEPENDENCIES = False

if not HAS_DEPENDENCIES:
    print("ERROR: High-performance Python shape generator requires 'pillow', 'numpy', and 'numba'.", file=sys.stderr)
    print("Please install them by running: pip install pillow numpy numba", file=sys.stderr)
    sys.exit(1)

# --- Numba JIT Accelerated Core ---
@numba.jit(nopython=True, fastmath=True, cache=True)
def evaluate_candidate(target, canvas, x_c, y_c, r_x, r_y, theta, alpha, alpha_mask, check_contour, use_freeze=False, freeze_mask=None, use_weight=False, weight_map=None, use_uncovered=False, uncovered_map=None):
    """
    Evaluates a candidate rotated ellipse against the target image.
    Calculates the optimal average color and the Delta Mean Squared Error (MSE).
    Optimized via Loop Fusion (single-pass) and Strength Reduction.
    If check_contour is True, guarantees the ellipse is strictly inside the target contour.
    """
    height = target.shape[0]
    width = target.shape[1]
    
    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))
    
    # Calculate exact bounding box of the rotated ellipse to limit pixel search area
    x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    # Strictly enforce image boundary constraints (Hard Boundary Constraints)
    # If the ellipse goes beyond the outer canvas edges, reject it instantly
    if (x_c - x_half < 0.0) or (x_c + x_half > np.float32(width)) or (y_c - y_half < 0.0) or (y_c + y_half > np.float32(height)):
        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
        
    min_x = max(0, int(x_c - x_half))
    max_x = min(width - 1, int(x_c + x_half))
    min_y = max(0, int(y_c - y_half))
    max_y = min(height - 1, int(y_c + y_half))
    
    inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
    inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
    
    A = np.float32(cos_t*cos_t * inv_rx2 + sin_t*sin_t * inv_ry2)
    B_coef = np.float32(2.0 * cos_t * sin_t * (inv_rx2 - inv_ry2))
    C_coef = np.float32(sin_t*sin_t * inv_rx2 + cos_t*cos_t * inv_ry2)

    inv_2A = np.float32(1.0 / (2.0 * A)) if A > 0.0 else np.float32(0.0)

    # Initialize statistical accumulators for Loop Fusion
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
        B = B_coef * dy
        C = C_coef * dy * dy - np.float32(1.0)
        D = B * B - np.float32(4.0) * A * C
        
        if D >= 0.0:
            sqrt_D = np.float32(math.sqrt(D))
            dx1 = (-B - sqrt_D) * inv_2A
            dx2 = (-B + sqrt_D) * inv_2A

            x_start = int(math.ceil(x_c + dx1))
            x_end = int(math.floor(x_c + dx2))

            row_min_x = max(min_x, x_start)
            row_max_x = min(max_x, x_end)

            for x in range(row_min_x, row_max_x + 1):
                # Strictly enforce shape boundaries inside target contour
                if check_contour:
                    if alpha_mask[y, x] <= 10.0:
                        # Reject this candidate immediately with infinite penalty
                        return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
                
                # Dynamic Freeze Masking: reject shape if it touches any frozen pixel
                if use_freeze and freeze_mask[y, x] == 1:
                    return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(99999999.0)
                        
                t_r = target[y, x, 0]
                t_g = target[y, x, 1]
                t_b = target[y, x, 2]
                
                c_r = canvas[y, x, 0]
                c_g = canvas[y, x, 1]
                c_b = canvas[y, x, 2]
                
                # Regional Error Weighting & Uncovered Priority Weighting
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
    
    # Calculate Delta MSE using O(1) loop fusion formula
    delta_r = a2_minus_2a * sum_c2_r + two_a * sum_ct_r + two_a_one_minus_a * avg_r * sum_c_r + a2_minus_2a * avg_r * sum_t_r
    delta_g = a2_minus_2a * sum_c2_g + two_a * sum_ct_g + two_a_one_minus_a * avg_g * sum_c_g + a2_minus_2a * avg_g * sum_t_g
    delta_b = a2_minus_2a * sum_c2_b + two_a * sum_ct_b + two_a_one_minus_a * avg_b * sum_c_b + a2_minus_2a * avg_b * sum_t_b
    
    total_delta_mse = delta_r + delta_g + delta_b
    
    return avg_r, avg_g, avg_b, total_delta_mse

@numba.jit(nopython=True, fastmath=True, cache=True)
def draw_ellipse(canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha):
    """Draws the selected best ellipse onto the canvas with Strength Reduction."""
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
    
    A = np.float32(cos_t*cos_t * inv_rx2 + sin_t*sin_t * inv_ry2)
    B_coef = np.float32(2.0 * cos_t * sin_t * (inv_rx2 - inv_ry2))
    C_coef = np.float32(sin_t*sin_t * inv_rx2 + cos_t*cos_t * inv_ry2)

    inv_2A = np.float32(1.0 / (2.0 * A)) if A > 0.0 else np.float32(0.0)

    a_f = np.float32(alpha / 255.0)
    one_minus_a = np.float32(1.0 - a_f)
    
    r_val = np.float32(r)
    g_val = np.float32(g)
    b_val = np.float32(b)
    
    for y in range(min_y, max_y + 1):
        dy = np.float32(y - y_c)
        B = B_coef * dy
        C = C_coef * dy * dy - np.float32(1.0)
        D = B * B - np.float32(4.0) * A * C
        
        if D >= 0.0:
            sqrt_D = np.float32(math.sqrt(D))
            dx1 = (-B - sqrt_D) * inv_2A
            dx2 = (-B + sqrt_D) * inv_2A

            x_start = int(math.ceil(x_c + dx1))
            x_end = int(math.floor(x_c + dx2))

            row_min_x = max(min_x, x_start)
            row_max_x = min(max_x, x_end)

            for x in range(row_min_x, row_max_x + 1):
                canvas[y, x, 0] = canvas[y, x, 0] * one_minus_a + r_val * a_f
                canvas[y, x, 1] = canvas[y, x, 1] * one_minus_a + g_val * a_f
                canvas[y, x, 2] = canvas[y, x, 2] * one_minus_a + b_val * a_f
                if canvas.shape[2] == 4:
                    canvas[y, x, 3] = canvas[y, x, 3] * one_minus_a + np.float32(alpha)

# --- Numba JIT Uncovered Priority Weighting Helpers ---
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
    
    x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    min_x = max(0, int(x_c - x_half))
    max_x = min(width - 1, int(x_c + x_half))
    min_y = max(0, int(y_c - y_half))
    max_y = min(height - 1, int(y_c + y_half))
    
    inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
    inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
    
    A = np.float32(cos_t*cos_t * inv_rx2 + sin_t*sin_t * inv_ry2)
    B_coef = np.float32(2.0 * cos_t * sin_t * (inv_rx2 - inv_ry2))
    C_coef = np.float32(sin_t*sin_t * inv_rx2 + cos_t*cos_t * inv_ry2)

    inv_2A = np.float32(1.0 / (2.0 * A)) if A > 0.0 else np.float32(0.0)

    for y in range(min_y, max_y + 1):
        dy = np.float32(y - y_c)
        B = B_coef * dy
        C = C_coef * dy * dy - np.float32(1.0)
        D = B * B - np.float32(4.0) * A * C
        
        if D >= 0.0:
            sqrt_D = np.float32(math.sqrt(D))
            dx1 = (-B - sqrt_D) * inv_2A
            dx2 = (-B + sqrt_D) * inv_2A
            
            x_start = int(math.ceil(x_c + dx1))
            x_end = int(math.floor(x_c + dx2))

            row_min_x = max(min_x, x_start)
            row_max_x = min(max_x, x_end)

            for x in range(row_min_x, row_max_x + 1):
                uncovered_map[y, x] = np.float32(1.0)

def rebuild_uncovered_map_from_shapes(width, height, has_alpha, alpha_mask, bias, shapes_list):
    """Rebuilds the uncovered map by drawing all active shapes onto a fresh mask."""
    uncovered_map = init_uncovered_map(width, height, has_alpha, alpha_mask, bias)
    for s in shapes_list:
        if s["type"] == 32:
            data = s["data"]
            x_c, y_c, r_x, r_y, theta_deg = data
            theta = math.radians(theta_deg)
            update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta)
    return uncovered_map

def get_boundary_weight_map(alpha_mask, bias):
    """Computes a 2-pixel wide boundary weight map using pure standard NumPy."""
    if alpha_mask is None:
        return np.ones((1, 1), dtype=np.float32)
    height, width = alpha_mask.shape
    boundary_map = np.ones((height, width), dtype=np.float32)
    
    fg = (alpha_mask > 127.0)
    
    # 1-pixel shift
    sh_up = np.zeros_like(fg)
    sh_up[:-1, :] = fg[1:, :]
    sh_down = np.zeros_like(fg)
    sh_down[1:, :] = fg[:-1, :]
    sh_left = np.zeros_like(fg)
    sh_left[:, :-1] = fg[:, 1:]
    sh_right = np.zeros_like(fg)
    sh_right[:, 1:] = fg[:, :-1]
    
    # 2-pixel shift
    sh_up2 = np.zeros_like(fg)
    sh_up2[:-2, :] = fg[2:, :]
    sh_down2 = np.zeros_like(fg)
    sh_down2[2:, :] = fg[:-2, :]
    sh_left2 = np.zeros_like(fg)
    sh_left2[:, :-2] = fg[:, 2:]
    sh_right2 = np.zeros_like(fg)
    sh_right2[:, 2:] = fg[:, :-2]
    
    # Boundary is foreground pixels adjacent to background (within 2 pixels)
    boundary = fg & (~sh_up | ~sh_down | ~sh_left | ~sh_right | ~sh_up2 | ~sh_down2 | ~sh_left2 | ~sh_right2)
    
    boundary_map[boundary] = np.float32(bias)
    return boundary_map

# --- Numba Parallel Random Search ---
@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def parallel_random_search(target, canvas, num_candidates, width, height, max_r, alpha_mask, check_contour, use_importance, error_prob, use_freeze=False, freeze_mask=None, use_weight=False, weight_map=None, use_uncovered=False, uncovered_map=None):
    # Pre-generate random parameters using NumPy's fast JIT random generator as float32
    if use_importance and error_prob.shape[0] > 1:
        # Rejection sampling for x_c and y_c based on error probability map
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
        x_c_arr = np.random.uniform(0.0, float(width), num_candidates).astype(np.float32)
        y_c_arr = np.random.uniform(0.0, float(height), num_candidates).astype(np.float32)
        
    r_x_arr = np.random.uniform(2.0, max_r, num_candidates).astype(np.float32)
    r_y_arr = np.random.uniform(2.0, max_r, num_candidates).astype(np.float32)
    theta_arr = np.random.uniform(0.0, 2.0 * math.pi, num_candidates).astype(np.float32)
    alpha_arr = np.full(num_candidates, 255.0, dtype=np.float32)
    
    deltas = np.zeros(num_candidates, dtype=np.float32)
    colors = np.zeros((num_candidates, 3), dtype=np.float32)
    
    # Parallel loop across all CPU cores using numba.prange
    for i in numba.prange(num_candidates):
        r, g, b, delta = evaluate_candidate(
            target, canvas, 
            x_c_arr[i], y_c_arr[i], 
            r_x_arr[i], r_y_arr[i], 
            theta_arr[i], int(alpha_arr[i]),
            alpha_mask, check_contour,
            use_freeze, freeze_mask, use_weight, weight_map,
            use_uncovered, uncovered_map
        )
        deltas[i] = np.float32(delta)
        colors[i, 0] = np.float32(r)
        colors[i, 1] = np.float32(g)
        colors[i, 2] = np.float32(b)
        
    best_idx = np.argmin(deltas)
    
    return (
        x_c_arr[best_idx], y_c_arr[best_idx], 
        r_x_arr[best_idx], r_y_arr[best_idx], 
        theta_arr[best_idx], int(alpha_arr[best_idx]),
        colors[best_idx, 0], colors[best_idx, 1], colors[best_idx, 2],
        deltas[best_idx]
    )

# --- Numba Serial Hill-Climbing ---
@numba.jit(nopython=True, fastmath=True, cache=True)
def serial_hill_climb(target, canvas, x_c, y_c, r_x, r_y, theta, alpha, r, g, b, best_delta, optimization_steps, alpha_mask, check_contour, sa_enabled=False, initial_temp=5000.0, cooling_rate=0.95, max_r=999.0, use_freeze=False, freeze_mask=None, use_weight=False, weight_map=None, use_uncovered=False, uncovered_map=None):
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
        
        # Mutation step sizes using numpy JIT normal distribution as float32
        nx_c = curr_x_c + np.float32(np.random.normal(0.0, 8.0 * scale))
        ny_c = curr_y_c + np.float32(np.random.normal(0.0, 8.0 * scale))
        nr_x = max(np.float32(2.0), min(max_r_f, curr_r_x + np.float32(np.random.normal(0.0, 6.0 * scale))))
        nr_y = max(np.float32(2.0), min(max_r_f, curr_r_y + np.float32(np.random.normal(0.0, 6.0 * scale))))
        ntheta = curr_theta + np.float32(np.random.normal(0.0, 0.25 * scale))
        nalpha = 255
        
        nr, ng, nb, delta = evaluate_candidate(target, canvas, nx_c, ny_c, nr_x, nr_y, ntheta, nalpha, alpha_mask, check_contour, use_freeze, freeze_mask, use_weight, weight_map, use_uncovered, uncovered_map)
        
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
            
    return (float(curr_x_c), float(curr_y_c), float(curr_r_x), float(curr_r_y), float(curr_theta), int(curr_r), int(curr_g), int(curr_b), curr_alpha, float(curr_delta))

# --- Hill-Climbing Search ---
def find_best_ellipse(target, canvas, num_candidates=200, optimization_steps=50, alpha_mask=None, check_contour=False, use_importance=False, error_prob=None, sa_enabled=False, initial_temp=5000.0, cooling_rate=0.95, current_max_r=None, use_freeze=False, freeze_mask=None, use_weight=False, weight_map=None, use_uncovered=False, uncovered_map=None):
    height, width, _ = target.shape
    max_r = max(10.0, min(width, height) / 3.0)
    if current_max_r is not None:
        max_r = min(max_r, current_max_r)
    
    if alpha_mask is None or alpha_mask.shape == (1, 1):
        if alpha_mask is None:
            alpha_mask = np.zeros((1, 1), dtype=np.float32)
        check_contour = False
        
    if error_prob is None:
        error_prob = np.zeros((1, 1), dtype=np.float32)
    
    # Prepare freeze_mask, weight_map, and uncovered_map defaults for JIT compatibility
    if freeze_mask is None:
        freeze_mask = np.zeros((1, 1), dtype=np.uint8)
    if weight_map is None:
        weight_map = np.ones((1, 1), dtype=np.float32)
    if uncovered_map is None:
        uncovered_map = np.ones((1, 1), dtype=np.float32)
        
    # 1. Parallel Random Search Phase
    x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = parallel_random_search(
        target, canvas, num_candidates, width, height, max_r, alpha_mask, check_contour, use_importance, error_prob,
        use_freeze, freeze_mask, use_weight, weight_map, use_uncovered, uncovered_map
    )
    
    # Graceful Fallback: If all candidates hit the freeze mask, disable freeze restrictions for this step to prevent solid black patches.
    fallback_active = False
    if use_freeze and delta >= 90000000.0:
        fallback_active = True
        x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = parallel_random_search(
            target, canvas, num_candidates, width, height, max_r, alpha_mask, check_contour, use_importance, error_prob,
            False, freeze_mask, use_weight, weight_map, use_uncovered, uncovered_map
        )
    
    # 2. Local JIT Hill-Climbing Optimization Phase
    hill_climb_freeze = use_freeze if not fallback_active else False
    x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta = serial_hill_climb(
        target, canvas, x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta, optimization_steps, alpha_mask, check_contour,
        sa_enabled, initial_temp, cooling_rate, max_r, hill_climb_freeze, freeze_mask, use_weight, weight_map, use_uncovered, uncovered_map
    )
    
    return (x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta)

# --- JIT-compiled Backward Alpha Occlusion Redundancy Check ---
@numba.jit(nopython=True, fastmath=True, cache=True)
def run_redundancy_check_jit(shapes_data, shapes_color, shapes_type, width, height):
    """
    JIT-accelerated backward occlusion tracing.
    shapes_data: 2D array (N, 5) -> [x_c, y_c, r_x, r_y, theta] (theta in radians)
    shapes_color: 2D array (N, 4) -> [r, g, b, alpha]
    shapes_type: 1D array (N) -> type (1 for background, 32 for ellipse)
    Returns a boolean mask of shape visibility (True if useful, False if redundant).
    """
    num_shapes = len(shapes_type)
    visible_mask = np.ones(num_shapes, dtype=np.bool_)
    
    # 2D occlusion canvas initialized to 0.0
    occlusion = np.zeros((height, width), dtype=np.float32)
    
    # Walk backward from top to bottom
    for i in range(num_shapes - 1, -1, -1):
        s_type = shapes_type[i]
        
        # Background canvas header (type 1)
        if s_type == 1:
            visible_mask[i] = True
            # Background is 100% opaque, fills the whole canvas
            for y in range(height):
                for x in range(width):
                    occlusion[y, x] = 1.0
            continue
            
        # Ellipse shape (type 32)
        x_c = np.float32(shapes_data[i, 0])
        y_c = np.float32(shapes_data[i, 1])
        r_x = np.float32(shapes_data[i, 2])
        r_y = np.float32(shapes_data[i, 3])
        theta = np.float32(shapes_data[i, 4])
        
        alpha = shapes_color[i, 3]
        a_f = np.float32(alpha / 255.0)
        
        cos_t = np.float32(math.cos(theta))
        sin_t = np.float32(math.sin(theta))
        
        # Calculate exact bounding box of the rotated ellipse
        x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
        y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
        
        min_x = max(0, int(x_c - x_half))
        max_x = min(width - 1, int(x_c + x_half))
        min_y = max(0, int(y_c - y_half))
        max_y = min(height - 1, int(y_c + y_half))
        
        inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
        inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
        
        A = np.float32(cos_t*cos_t * inv_rx2 + sin_t*sin_t * inv_ry2)
        B_coef = np.float32(2.0 * cos_t * sin_t * (inv_rx2 - inv_ry2))
        C_coef = np.float32(sin_t*sin_t * inv_rx2 + cos_t*cos_t * inv_ry2)

        inv_2A = np.float32(1.0 / (2.0 * A)) if A > 0.0 else np.float32(0.0)

        # Check if shape contributes any visible pixel
        has_contribution = False
        
        for y in range(min_y, max_y + 1):
            dy = np.float32(y - y_c)
            B = B_coef * dy
            C = C_coef * dy * dy - np.float32(1.0)
            D = B * B - np.float32(4.0) * A * C
            
            if D >= 0.0:
                sqrt_D = np.float32(math.sqrt(D))
                dx1 = (-B - sqrt_D) * inv_2A
                dx2 = (-B + sqrt_D) * inv_2A

                x_start = int(math.ceil(x_c + dx1))
                x_end = int(math.floor(x_c + dx2))

                row_min_x = max(min_x, x_start)
                row_max_x = min(max_x, x_end)

                for x in range(row_min_x, row_max_x + 1):
                    if occlusion[y, x] < 0.999:
                        has_contribution = True
                        occlusion[y, x] += (1.0 - occlusion[y, x]) * a_f
                
        if not has_contribution:
            visible_mask[i] = False
            
    return visible_mask

def optimize_redundant_shapes(shapes_list, width, height):
    """Filters out fully occluded/redundant shapes from the shapes list."""
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
            
    visible_mask = run_redundancy_check_jit(shapes_data, shapes_color, shapes_type, width, height)
    optimized_shapes = [shapes_list[i] for i in range(num_shapes) if visible_mask[i]]
    
    removed_count = num_shapes - len(optimized_shapes)
    if removed_count > 0:
        print(f"\n[Optimization] Removed {removed_count} redundant/occluded shapes! Conserved layers count: {len(optimized_shapes)}")
        
    return optimized_shapes

def optimize_redundant_shapes_final(shapes_list, width, height):
    """
    末尾專用：不刪除冗餘形狀，而是將其重置為左上角 (0, 0) 的極小全透明形狀，
    以維持總層數剛好等於原始層數限制，便於遊戲內手動清理。
    """
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
            
    visible_mask = run_redundancy_check_jit(shapes_data, shapes_color, shapes_type, width, height)
    
    final_shapes = []
    reset_count = 0
    
    # shapes_list[0] 是 background header
    final_shapes.append(shapes_list[0])
    
    for i in range(1, num_shapes):
        s = shapes_list[i]
        if visible_mask[i]:
            final_shapes.append(s)
        else:
            # 冗餘形狀，將其重置為極小且置於畫布外的完全不透明形狀，確保在遊戲和預覽中均不顯示並保持不透明特質
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
            shapes_data[i, 0], shapes_data[i, 1], shapes_data[i, 2], shapes_data[i, 3], 
            shapes_data[i, 4], 
            shapes_color[i, 0], shapes_color[i, 1], shapes_color[i, 2], shapes_color[i, 3]
        )

def rebuild_canvas_from_shapes(canvas, shapes_list, avg_r, avg_g, avg_b):
    """Re-draws all valid shapes onto the canvas after redundancy check optimization using fast JIT compiler."""
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
            
    rebuild_canvas_jit(canvas, avg_r, avg_g, avg_b, avg_a, shapes_data, shapes_color)

# --- Helper Functions ---
def scale_shapes_list(shapes, factor):
    """等比例縮放形狀清單內所有圖案的座標與半徑"""
    for s in shapes:
        if s["type"] == 32:
            s["data"][0] = float(s["data"][0] * factor) # X
            s["data"][1] = float(s["data"][1] * factor) # Y
            s["data"][2] = float(s["data"][2] * factor) # rX
            s["data"][3] = float(s["data"][3] * factor) # rY
        elif s["type"] == 1:
            s["data"][2] = float(s["data"][2] * factor) # w
            s["data"][3] = float(s["data"][3] * factor) # h

def load_profile(profile_path):
    """Parses custom .ini profile files from the settings directory."""
    params = {}
    if not profile_path or not os.path.exists(profile_path):
        return params
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith(";"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    params[key.strip()] = val.strip()
    except Exception as e:
        print(f"Warning: Failed to load profile {profile_path}: {e}", file=sys.stderr)
    return params

# --- Main Logic ---
def run_generator(image_path, output_path=None, profile_path=None, layers_limit=None, candidates_limit=None, steps_limit=None, progress_callback=None, opt_settings=None):
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}", file=sys.stderr)
        return 1
        
    # --- Resolve default profile to c. balanced if not provided ---
    if not profile_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # parent of 'tools'
        default_profile = os.path.join(project_root, "settings", "c. balanced - good quality and speed.ini")
        if os.path.exists(default_profile):
            profile_path = default_profile
            print(f"No profile specified. Using default: {os.path.basename(profile_path)}")

        
    if not output_path:
        img_base = os.path.splitext(os.path.basename(image_path))[0]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # parent of 'tools'
        output_dir = os.path.join(project_root, "output", img_base)
        output_path = os.path.join(output_dir, f"{img_base}.json")
        
    # --- Load Settings from Profile ---
    profile = load_profile(profile_path)
    
    max_res = int(profile.get("maxResolution", 2000))
    profile_layers = int(profile.get("stopAt", 2000))
    profile_candidates = int(profile.get("randomSamples", 20000))
    profile_steps = int(profile.get("mutatedSamples", 200))
    save_every = int(profile.get("saveEvery", 500))
    if save_every < 500:
        save_every = 500
    posterize_levels = int(profile.get("posterizeLevels", 256))
    
    save_at_str = profile.get("saveAt", "")
    save_at = set()
    if save_at_str:
        try:
            save_at = {int(x.strip()) for x in save_at_str.split(",") if x.strip()}
        except Exception:
            pass

    # Override defaults if explicitly provided
    layers = layers_limit if layers_limit is not None else profile_layers
    candidates = candidates_limit if candidates_limit is not None else profile_candidates
    steps = steps_limit if steps_limit is not None else profile_steps
    
    # --- Load Optimization Settings ---
    if opt_settings is None:
        opt_settings = {}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        opt_path = os.path.join(project_root, "optimization_settings.json")
        if os.path.exists(opt_path):
            try:
                with open(opt_path, "r", encoding="utf-8") as f:
                    opt_settings = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load optimization settings: {e}", file=sys.stderr)

    # 影像金字塔設定
    opt_pyramid = opt_settings.get("image_pyramid", {})
    pyramid_enabled = opt_pyramid.get("enabled", False)
    pyramid_layers_threshold = opt_pyramid.get("pyramid_layers_threshold", 500)
    pyramid_stagnation = opt_pyramid.get("stagnation_threshold", 0.005)

    # 重點採樣設定
    opt_importance = opt_settings.get("importance_sampling", {})
    importance_enabled = opt_importance.get("enabled", False)
    importance_interval = opt_importance.get("update_interval", 10)

    # 模擬退火設定
    opt_sa = opt_settings.get("simulated_annealing", {})
    sa_enabled = opt_sa.get("enabled", False)
    sa_initial_temp = opt_sa.get("initial_temperature", 5000.0)
    sa_cooling_rate = opt_sa.get("cooling_rate", 0.95)

    # 動態凍結遮罩設定
    opt_freeze = opt_settings.get("dynamic_freeze", {})
    freeze_enabled = opt_freeze.get("enabled", False)
    freeze_update_interval = opt_freeze.get("update_interval", 100)
    freeze_error_threshold = opt_freeze.get("error_threshold", 3)

    # 區域誤差加權設定
    opt_weight = opt_settings.get("error_weighting", {})
    weight_enabled = opt_weight.get("enabled", False)
    weight_update_interval = opt_weight.get("update_interval", 100)

    # 衰減式形狀限縮設定
    opt_decay = opt_settings.get("decaying_shape", {})
    decay_enabled = opt_decay.get("enabled", False)
    decay_min_max_r = opt_decay.get("min_max_r", 5.0)

    print(f"Optimized Python Generator Core: Numba JIT Compiler Enabled")
    if profile_path:
        print(f"Profile: {os.path.basename(profile_path)}")
    print(f"Target: {image_path} -> Output: {output_path}")
    print(f"Layers limit: {layers} | Candidates: {candidates} | Optim steps: {steps}")
    # Ensure the output directory exists before starting generation to support intermediate saves safely
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # Load and preprocess image (preserving RGBA if present to support transparent backgrounds)
    img_raw = Image.open(image_path)
    has_alpha = (img_raw.mode in ("RGBA", "LA") or (img_raw.mode == "P" and "transparency" in img_raw.info))
    if has_alpha:
        img = img_raw.convert("RGBA")
        print("Detected transparent background (RGBA/LA/Palette with alpha). Enabling Alpha-guided Ambient Padding.")
    else:
        img = img_raw.convert("RGB")
        
    width, height = img.size
    
    # Auto-resize to match maxResolution if specified
    if max_res > 0 and (width > max_res or height > max_res):
        scale = max_res / max(width, height)
        new_w = int(width * scale)
        new_h = int(height * scale)
        print(f"Resizing target image from {width}x{height} to {new_w}x{new_h} to match maxResolution={max_res}")
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        width, height = img.size
        
    target = np.array(img, dtype=np.float32)
    
    # Apply posterization if specified
    if 0 < posterize_levels < 256:
        print(f"Applying color posterization with {posterize_levels} levels...")
        factor = 255.0 / (posterize_levels - 1)
        if has_alpha:
            target[:, :, :3] = np.round(target[:, :, :3] / factor) * factor
        else:
            target = np.round(target / factor) * factor
    
    alpha_mask = np.zeros((1, 1), dtype=np.float32)
    if has_alpha:
        # Extract RGB channels and Alpha channel
        target_rgb = target[:, :, :3]
        # Binarize original alpha mask to make edges extremely sharp (Scheme 1)
        alpha_mask = (target[:, :, 3] > 127.0).astype(np.float32) * 255.0
        
        # Create foreground mask (opacity > 127)
        fg_mask = alpha_mask > 127.0
        
        # Calculate foreground average color to avoid background contamination
        if np.any(fg_mask):
            avg_r = np.mean(target_rgb[fg_mask, 0])
            avg_g = np.mean(target_rgb[fg_mask, 1])
            avg_b = np.mean(target_rgb[fg_mask, 2])
        else:
            avg_r, avg_g, avg_b = 128.0, 128.0, 128.0
            
        # Target transparent/background area is padded with the foreground average color
        bg_mask = ~fg_mask
        target_rgb[bg_mask, 0] = avg_r
        target_rgb[bg_mask, 1] = avg_g
        target_rgb[bg_mask, 2] = avg_b
        
        # Strip alpha channel from target for painter loop integration
        target = target_rgb
    else:
        # Calculate target image average color
        avg_r = np.mean(target[:, :, 0])
        avg_g = np.mean(target[:, :, 1])
        avg_b = np.mean(target[:, :, 2])
    
    # --- Image Pyramid Multi-Resolution Preparation ---
    target_1_1 = target.copy()
    alpha_mask_1_1 = alpha_mask.copy()
    w_1_1, h_1_1 = width, height
    
    current_pyramid_stage = "1/1"
    
    if pyramid_enabled:
        # 1/2 resolution
        w_1_2 = max(8, w_1_1 // 2)
        h_1_2 = max(8, h_1_1 // 2)
        img_1_2 = img.resize((w_1_2, h_1_2), Image.Resampling.LANCZOS)
        target_1_2 = np.array(img_1_2, dtype=np.float32)
        
        # 1/4 resolution
        w_1_4 = max(4, w_1_1 // 4)
        h_1_4 = max(4, h_1_1 // 4)
        img_1_4 = img.resize((w_1_4, h_1_4), Image.Resampling.LANCZOS)
        target_1_4 = np.array(img_1_4, dtype=np.float32)
        
        if has_alpha:
            # 1/2
            target_1_2_rgb = target_1_2[:, :, :3]
            # Binarize 1/2 scale alpha mask (Scheme 1)
            alpha_mask_1_2 = (target_1_2[:, :, 3] > 127.0).astype(np.float32) * 255.0
            fg_mask_1_2 = alpha_mask_1_2 > 127.0
            if np.any(fg_mask_1_2):
                avg_r_1_2 = np.mean(target_1_2_rgb[fg_mask_1_2, 0])
                avg_g_1_2 = np.mean(target_1_2_rgb[fg_mask_1_2, 1])
                avg_b_1_2 = np.mean(target_1_2_rgb[fg_mask_1_2, 2])
            else:
                avg_r_1_2, avg_g_1_2, avg_b_1_2 = avg_r, avg_g, avg_b
            bg_mask_1_2 = ~fg_mask_1_2
            target_1_2_rgb[bg_mask_1_2, 0] = avg_r_1_2
            target_1_2_rgb[bg_mask_1_2, 1] = avg_g_1_2
            target_1_2_rgb[bg_mask_1_2, 2] = avg_b_1_2
            target_1_2 = target_1_2_rgb
            
            # 1/4
            target_1_4_rgb = target_1_4[:, :, :3]
            # Binarize 1/4 scale alpha mask (Scheme 1)
            alpha_mask_1_4 = (target_1_4[:, :, 3] > 127.0).astype(np.float32) * 255.0
            fg_mask_1_4 = alpha_mask_1_4 > 127.0
            if np.any(fg_mask_1_4):
                avg_r_1_4 = np.mean(target_1_4_rgb[fg_mask_1_4, 0])
                avg_g_1_4 = np.mean(target_1_4_rgb[fg_mask_1_4, 1])
                avg_b_1_4 = np.mean(target_1_4_rgb[fg_mask_1_4, 2])
            else:
                avg_r_1_4, avg_g_1_4, avg_b_1_4 = avg_r, avg_g, avg_b
            bg_mask_1_4 = ~fg_mask_1_4
            target_1_4_rgb[bg_mask_1_4, 0] = avg_r_1_4
            target_1_4_rgb[bg_mask_1_4, 1] = avg_g_1_4
            target_1_4_rgb[bg_mask_1_4, 2] = avg_b_1_4
            target_1_4 = target_1_4_rgb
        else:
            alpha_mask_1_2 = np.zeros((1, 1), dtype=np.float32)
            alpha_mask_1_4 = np.zeros((1, 1), dtype=np.float32)
            
        print(f"[Image Pyramid] 影像金字塔解析度已生成: 1/4 ({w_1_4}x{h_1_4}), 1/2 ({w_1_2}x{h_1_2}), 1/1 ({w_1_1}x{h_1_1})")
        
        # Start at Stage 1/4
        current_pyramid_stage = "1/4"
        target = target_1_4
        alpha_mask = alpha_mask_1_4
        width, height = w_1_4, h_1_4

    # Initialize canvas with target image average color
    canvas = np.zeros_like(target)
    canvas[:, :, 0] = avg_r
    canvas[:, :, 1] = avg_g
    canvas[:, :, 2] = avg_b
    
    # Construct shape array with canvas header shape
    shapes_list = []
    
    # Header format: type=1, data=[0, 0, w, h], color=[avg_r, avg_g, avg_b, 0 if has_alpha else 255]
    # If the target image has transparent background, background is transparent (0); otherwise it is fully opaque (255)
    header = {
        "type": 1,
        "data": [0.0, 0.0, float(width), float(height)],
        "color": [int(avg_r), int(avg_g), int(avg_b), 0 if has_alpha else 255],
        "score": 0.0
    }
    shapes_list.append(header)
    
    # Initialize error probability map for Importance Sampling
    error_prob = None
    if importance_enabled:
        diff_mat = np.abs(target - canvas)
        err_heatmap = np.mean(diff_mat, axis=2)
        max_err = err_heatmap.max()
        error_prob = (err_heatmap / max_err).astype(np.float32) if max_err > 0 else np.zeros(err_heatmap.shape, dtype=np.float32)

    # Initialize freeze_mask and weight_map for Dynamic Freeze Masking & Error Weighting & Boundary Weighting
    freeze_mask = np.zeros((height, width), dtype=np.uint8) if freeze_enabled else None
    
    # 邊界超加權設定 (Boundary Weighting) (Scheme 2)
    opt_boundary = opt_settings.get("boundary_weighting", {})
    boundary_enabled = opt_boundary.get("enabled", True)
    boundary_bias = opt_boundary.get("bias", 3.0)
    
    boundary_weight_map = np.ones((height, width), dtype=np.float32)
    if boundary_enabled and has_alpha and alpha_mask is not None:
        boundary_weight_map = get_boundary_weight_map(alpha_mask, boundary_bias)
        
    use_weight_jit = weight_enabled or (boundary_enabled and has_alpha)
    if use_weight_jit:
        weight_map = boundary_weight_map.copy()
    else:
        weight_map = None
    
    # Initialize uncovered priority weighting settings (permanently integrated in core)
    opt_uncovered = opt_settings.get("uncovered_bias", {})
    uncovered_enabled = opt_uncovered.get("enabled", True)
    uncovered_bias = opt_uncovered.get("bias", 5.0)
    
    uncovered_map = None
    if uncovered_enabled:
        uncovered_map = init_uncovered_map(width, height, has_alpha, alpha_mask, uncovered_bias)
    
    # Base max_r for Decaying Shape Constraints
    base_max_r = max(10.0, min(width, height) / 3.0)

    # Disable automatic garbage collection to eliminate overhead from many dict allocations in loop
    gc.disable()
    
    start_time = time.time()
    last_print = time.time()
    
    attempts = 0
    max_attempts = layers * 3
    total_generated_so_far = 0
    
    recent_deltas = []
    stage_1_4_limit = pyramid_layers_threshold
    stage_1_2_limit = pyramid_layers_threshold * 2
    if layers <= pyramid_layers_threshold * 2:
        stage_1_4_limit = max(10, int(layers * 0.25))
        stage_1_2_limit = max(20, int(layers * 0.50))
        
    while (len(shapes_list) - 1 < layers) and (attempts < max_attempts):

        attempts += 1
        
        # Decaying Shape Constraints: dynamically shrink max radius as layers progress
        current_max_r = None
        if decay_enabled:
            progress_ratio = (len(shapes_list) - 1) / layers
            current_max_r = max(decay_min_max_r, base_max_r * (1.0 - progress_ratio ** 2))
        
        result = find_best_ellipse(
            target, canvas, candidates, steps, 
            alpha_mask=alpha_mask, check_contour=has_alpha,
            use_importance=importance_enabled, error_prob=error_prob,
            sa_enabled=sa_enabled, initial_temp=sa_initial_temp, cooling_rate=sa_cooling_rate,
            current_max_r=current_max_r,
            use_freeze=freeze_enabled, freeze_mask=freeze_mask,
            use_weight=use_weight_jit, weight_map=weight_map,
            use_uncovered=uncovered_enabled, uncovered_map=uncovered_map
        )
        x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta = result
        
        if delta >= 90000000.0:
            # Reject invalid shapes to avoid rendering solid black patches on the canvas
            print(f"\n[Warning] Layer {len(shapes_list)}: Candidate shape rejected due to hard boundary/freeze conflict (delta={delta:.1f}). Skipping...")
            continue
        
        # Draw on canvas
        draw_ellipse(canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha)
        
        # Update uncovered mask with the newly drawn shape
        if uncovered_enabled and uncovered_map is not None:
            update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta)
        
        # Save shape
        shapes_list.append({
            "type": 32,
            "data": [x_c, y_c, r_x, r_y, float(math.degrees(theta))],
            "color": [r, g, b, alpha],
            "score": float(delta)
        })
        
        total_generated_so_far += 1
        current_layer = len(shapes_list) - 1
        
        # Stagnation tracking
        mse_change = -delta / (canvas.shape[0] * canvas.shape[1])
        recent_deltas.append(mse_change)
        if len(recent_deltas) > 30:
            recent_deltas.pop(0)
            
        stagnated = False
        if len(recent_deltas) >= 20:
            avg_recent = sum(recent_deltas[-10:]) / 10.0
            avg_older = sum(recent_deltas[:-10]) / (len(recent_deltas) - 10)
            if avg_older > 0 and (avg_recent / avg_older) < pyramid_stagnation:
                stagnated = True
                
        # Image Pyramid stage transition
        if pyramid_enabled:
            if current_pyramid_stage == "1/4":
                if current_layer >= stage_1_4_limit or stagnated:
                    print(f"\n[Image Pyramid] 1/4 解析度階段完成於層數 {current_layer} (停滯={stagnated})。正在切換至 1/2 解析度...")
                    scale_shapes_list(shapes_list, 2.0)
                    target = target_1_2
                    alpha_mask = alpha_mask_1_2
                    width, height = w_1_2, h_1_2
                    canvas = np.zeros_like(target)
                    rebuild_canvas_from_shapes(canvas, shapes_list, avg_r, avg_g, avg_b)
                    if uncovered_enabled:
                        uncovered_map = rebuild_uncovered_map_from_shapes(width, height, has_alpha, alpha_mask, uncovered_bias, shapes_list)
                    current_pyramid_stage = "1/2"
                    recent_deltas = []
                    # Recalculate error map for new resolution
                    if importance_enabled:
                        diff_mat = np.abs(target - canvas)
                        err_heatmap = np.mean(diff_mat, axis=2)
                        max_err = err_heatmap.max()
                        error_prob = (err_heatmap / max_err).astype(np.float32) if max_err > 0 else np.zeros(err_heatmap.shape, dtype=np.float32)
                    # Reinitialize freeze_mask and weight_map for new resolution
                    if freeze_enabled:
                        freeze_mask = np.zeros((h_1_2, w_1_2), dtype=np.uint8)
                    if boundary_enabled and has_alpha:
                        boundary_weight_map = get_boundary_weight_map(alpha_mask, boundary_bias)
                    if use_weight_jit:
                        weight_map = boundary_weight_map.copy()
                    base_max_r = max(10.0, min(w_1_2, h_1_2) / 3.0)
            elif current_pyramid_stage == "1/2":
                if current_layer >= stage_1_2_limit or stagnated:
                    print(f"\n[Image Pyramid] 1/2 解析度階段完成於層數 {current_layer} (停滯={stagnated})。正在切換至 1/1 解析度 (Fine Phase)...")
                    scale_shapes_list(shapes_list, 2.0)
                    target = target_1_1
                    alpha_mask = alpha_mask_1_1
                    width, height = w_1_1, h_1_1
                    canvas = np.zeros_like(target)
                    rebuild_canvas_from_shapes(canvas, shapes_list, avg_r, avg_g, avg_b)
                    if uncovered_enabled:
                        uncovered_map = rebuild_uncovered_map_from_shapes(width, height, has_alpha, alpha_mask, uncovered_bias, shapes_list)
                    current_pyramid_stage = "1/1"
                    recent_deltas = []
                    # Recalculate error map for new resolution
                    if importance_enabled:
                        diff_mat = np.abs(target - canvas)
                        err_heatmap = np.mean(diff_mat, axis=2)
                        max_err = err_heatmap.max()
                        error_prob = (err_heatmap / max_err).astype(np.float32) if max_err > 0 else np.zeros(err_heatmap.shape, dtype=np.float32)
                    # Reinitialize freeze_mask and weight_map for new resolution
                    if freeze_enabled:
                        freeze_mask = np.zeros((h_1_1, w_1_1), dtype=np.uint8)
                    if boundary_enabled and has_alpha:
                        boundary_weight_map = get_boundary_weight_map(alpha_mask, boundary_bias)
                    if use_weight_jit:
                        weight_map = boundary_weight_map.copy()
                    base_max_r = max(10.0, min(w_1_1, h_1_1) / 3.0)

        # Update importance sampling error probability map every N layers
        if importance_enabled and total_generated_so_far % importance_interval == 0:
            diff_mat = np.abs(target - canvas)
            err_heatmap = np.mean(diff_mat, axis=2)
            max_err = err_heatmap.max()
            error_prob = (err_heatmap / max_err).astype(np.float32) if max_err > 0 else np.zeros(err_heatmap.shape, dtype=np.float32)

        # Periodically update Dynamic Freeze Mask & Error Weight Map
        freeze_update_needed = freeze_enabled and total_generated_so_far > 0 and total_generated_so_far % freeze_update_interval == 0
        weight_update_needed = weight_enabled and total_generated_so_far > 0 and total_generated_so_far % weight_update_interval == 0
        if freeze_update_needed or weight_update_needed:
            diff_mat = np.abs(target - canvas)
            per_pixel_err = np.mean(diff_mat[:, :, :3], axis=2)  # Average RGB error per pixel
            
            if freeze_update_needed:
                # Freeze pixels where all RGB channels are within threshold
                freeze_mask = np.where(per_pixel_err < freeze_error_threshold, np.uint8(1), np.uint8(0)).astype(np.uint8)
                frozen_pct = np.sum(freeze_mask) * 100.0 / (freeze_mask.shape[0] * freeze_mask.shape[1])
                print(f"\n[Freeze Mask] 層數 {current_layer}: 凍結了 {frozen_pct:.1f}% 的像素 (閾值={freeze_error_threshold})")
            
            if weight_update_needed:
                # Exponential weighting: high error pixels get much higher weight
                max_err = per_pixel_err.max()
                if max_err > 0:
                    normalized_err = per_pixel_err / max_err  # [0, 1]
                    dynamic_weights = (1.0 + normalized_err * 9.0).astype(np.float32)  # [1, 10]
                    if boundary_enabled and has_alpha:
                        weight_map = (dynamic_weights * boundary_weight_map).astype(np.float32)
                    else:
                        weight_map = dynamic_weights
                else:
                    weight_map = boundary_weight_map.copy() if (boundary_enabled and has_alpha) else np.ones((height, width), dtype=np.float32)

        # --- Midway Redundancy Check & Canvas Rebuilding ---
        # Test mode fallback: If layers < 500, trigger every 10 layers starting at 10.
        is_normal_trigger = (total_generated_so_far > 0 and total_generated_so_far % 500 == 0)
        is_test_trigger = (layers < 500 and total_generated_so_far >= 10 and (total_generated_so_far - 10) % 10 == 0)
        
        if is_normal_trigger or is_test_trigger:
            print(f"\n[Engine] Reached {total_generated_so_far} generated layers. Running mid-way redundancy check...")
            shapes_list = optimize_redundant_shapes(shapes_list, width, height)
            # Rebuild canvas from stable ordered remaining shapes
            rebuild_canvas_from_shapes(canvas, shapes_list, avg_r, avg_g, avg_b)
            if uncovered_enabled:
                uncovered_map = rebuild_uncovered_map_from_shapes(width, height, has_alpha, alpha_mask, uncovered_bias, shapes_list)
            current_layer = len(shapes_list) - 1
        
        # Check if we should save intermediate JSON
        if current_layer in save_at or (save_every > 0 and current_layer % save_every == 0 and current_layer < layers):
            base_dir = os.path.dirname(output_path) or "."
            file_base, file_ext = os.path.splitext(os.path.basename(output_path))
            inter_path = os.path.join(base_dir, f"{file_base}_{current_layer}{file_ext}")
            try:
                with open(inter_path, "w", encoding="utf-8") as f:
                    json.dump({"shapes": shapes_list}, f, indent=2)
            except Exception as e:
                print(f"\nWarning: Failed to save intermediate JSON to {inter_path}: {e}", file=sys.stderr)
        
        # Progress Bar, Callback & Timing
        now = time.time()
        elapsed = now - start_time
        speed = current_layer / elapsed if elapsed > 0 else 0.0
        eta = (layers - current_layer) / speed if speed > 0 else 0.0
        
        if progress_callback:
            if has_alpha:
                # Pack canvas with alpha channel as (H, W, 4) to let GUI render transparent background with checkerboard
                canvas_rgba = np.zeros((height, width, 4), dtype=np.float32)
                canvas_rgba[:, :, :3] = canvas
                canvas_rgba[:, :, 3] = alpha_mask
                cb_res = progress_callback(current_layer, layers, speed, eta, canvas_rgba)
            else:
                cb_res = progress_callback(current_layer, layers, speed, eta, canvas)
                
            if cb_res is False or cb_res == "ABORT":
                print("\n[Engine] Shape generation aborted by progress callback cancellation request.")
                break
            
        if now - last_print >= 1.0 or current_layer == layers:
            pct = current_layer * 100.0 / layers
            if not progress_callback:
                sys.stdout.write(f"\rGenerating Shapes: {pct:5.1f}% | Layer {current_layer:4d}/{layers} | Speed: {speed:5.1f} layers/s | ETA: {eta:4.0f}s")
                sys.stdout.flush()
            else:
                if current_layer % 500 == 0 or current_layer == layers:
                    print(f"[Engine] Shape generation progress: {pct:.1f}% ({current_layer}/{layers})")
            last_print = now
            
    print()
    gc.enable()
    total_time = time.time() - start_time

    print(f"Shape generation completed in {total_time:.2f} seconds!")
    
    # If we finished but are still in a low resolution stage, upscale to 1/1
    if pyramid_enabled and current_pyramid_stage != "1/1":
        if current_pyramid_stage == "1/4":
            print("\n[Image Pyramid] 正在從 1/4 直接升級至 1/1 解析度...")
            scale_shapes_list(shapes_list, 4.0)
        elif current_pyramid_stage == "1/2":
            print("\n[Image Pyramid] 正在從 1/2 升級至 1/1 解析度...")
            scale_shapes_list(shapes_list, 2.0)
        target = target_1_1
        alpha_mask = alpha_mask_1_1
        width, height = w_1_1, h_1_1
        canvas = np.zeros_like(target)
        rebuild_canvas_from_shapes(canvas, shapes_list, avg_r, avg_g, avg_b)
        current_pyramid_stage = "1/1"
        
    # --- Final Redundancy Check: Reset redundant layers to top-left transparent shapes ---
    print("\n[Engine] Running final redundancy check to reserve layer count and reset occluded shapes...")
    shapes_list = optimize_redundant_shapes_final(shapes_list, width, height)
    
    # Save to final JSON file
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"shapes": shapes_list}, f, indent=2)
        
    print(f"JSON geometry successfully written to: {output_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="High-performance Python Image-to-JSON Shape Generator")
    parser.add_argument("image_path", help="Path to input image file")
    parser.add_argument("--output", "-o", help="Path to save output JSON geometry")
    parser.add_argument("--profile", "-p", help="Path to settings INI profile")
    parser.add_argument("--layers", "-l", type=int, default=None, help="Number of layers/shapes to generate (overrides profile)")
    parser.add_argument("--candidates", "-c", type=int, default=None, help="Number of random candidates per shape (overrides profile)")
    parser.add_argument("--steps", "-s", type=int, default=None, help="Number of local hill-climbing steps (overrides profile)")
    
    args = parser.parse_args()
    return run_generator(
        image_path=args.image_path,
        output_path=args.output,
        profile_path=args.profile,
        layers_limit=args.layers,
        candidates_limit=args.candidates,
        steps_limit=args.steps
    )

if __name__ == "__main__":
    sys.exit(main())
