#!/usr/bin/env python3
import sys
import os
import time
import math
import random
import json
import argparse

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
def evaluate_candidate(target, canvas, x_c, y_c, r_x, r_y, theta, alpha):
    """
    Evaluates a candidate rotated ellipse against the target image.
    Calculates the optimal average color and the Delta Mean Squared Error (MSE).
    Optimized via Loop Fusion (single-pass) and Strength Reduction.
    """
    height = target.shape[0]
    width = target.shape[1]
    
    cos_t = np.float32(math.cos(theta))
    sin_t = np.float32(math.sin(theta))
    
    # Calculate exact bounding box of the rotated ellipse to limit pixel search area
    x_half = math.sqrt(r_x*r_x * cos_t*cos_t + r_y*r_y * sin_t*sin_t)
    y_half = math.sqrt(r_x*r_x * sin_t*sin_t + r_y*r_y * cos_t*cos_t)
    
    min_x = max(0, int(x_c - x_half))
    max_x = min(width - 1, int(x_c + x_half))
    min_y = max(0, int(y_c - y_half))
    max_y = min(height - 1, int(y_c + y_half))
    
    inv_rx2 = np.float32(1.0 / (r_x * r_x) if r_x > 0 else 0.0)
    inv_ry2 = np.float32(1.0 / (r_y * r_y) if r_y > 0 else 0.0)
    
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
        # Apply Strength Reduction: precalculate initial rx and ry for the row
        dx_start = np.float32(min_x - x_c)
        rx = dx_start * cos_t + dy * sin_t
        ry = -dx_start * sin_t + dy * cos_t
        
        for x in range(min_x, max_x + 1):
            if (rx * rx) * inv_rx2 + (ry * ry) * inv_ry2 <= 1.0:
                t_r = target[y, x, 0]
                t_g = target[y, x, 1]
                t_b = target[y, x, 2]
                
                c_r = canvas[y, x, 0]
                c_g = canvas[y, x, 1]
                c_b = canvas[y, x, 2]
                
                count += 1
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
                
            # Linear increment of rx and ry (Strength Reduction)
            rx += cos_t
            ry -= sin_t
            
    if count == 0:
        return 0.0, 0.0, 0.0, 99999999.0
        
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
    
    total_delta_mse = float(delta_r + delta_g + delta_b)
    
    return float(avg_r), float(avg_g), float(avg_b), total_delta_mse

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
            
            rx += cos_t
            ry -= sin_t

# --- Numba Parallel Random Search ---
@numba.jit(nopython=True, parallel=True, fastmath=True, cache=True)
def parallel_random_search(target, canvas, num_candidates, width, height, max_r):
    # Pre-generate random parameters using NumPy's fast JIT random generator as float32
    x_c_arr = np.random.uniform(0.0, float(width), num_candidates).astype(np.float32)
    y_c_arr = np.random.uniform(0.0, float(height), num_candidates).astype(np.float32)
    r_x_arr = np.random.uniform(2.0, max_r, num_candidates).astype(np.float32)
    r_y_arr = np.random.uniform(2.0, max_r, num_candidates).astype(np.float32)
    theta_arr = np.random.uniform(0.0, 2.0 * math.pi, num_candidates).astype(np.float32)
    alpha_arr = np.random.uniform(15.0, 180.0, num_candidates).astype(np.float32)
    
    deltas = np.zeros(num_candidates, dtype=np.float32)
    colors = np.zeros((num_candidates, 3), dtype=np.float32)
    
    # Parallel loop across all CPU cores using numba.prange
    for i in numba.prange(num_candidates):
        r, g, b, delta = evaluate_candidate(
            target, canvas, 
            x_c_arr[i], y_c_arr[i], 
            r_x_arr[i], r_y_arr[i], 
            theta_arr[i], int(alpha_arr[i])
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
def serial_hill_climb(target, canvas, x_c, y_c, r_x, r_y, theta, alpha, r, g, b, best_delta, optimization_steps):
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
    
    for step in range(optimization_steps):
        scale = np.float32(1.0 - (step / optimization_steps))
        
        # Mutation step sizes using numpy JIT normal distribution as float32
        nx_c = curr_x_c + np.float32(np.random.normal(0.0, 8.0 * scale))
        ny_c = curr_y_c + np.float32(np.random.normal(0.0, 8.0 * scale))
        nr_x = max(np.float32(2.0), curr_r_x + np.float32(np.random.normal(0.0, 6.0 * scale)))
        nr_y = max(np.float32(2.0), curr_r_y + np.float32(np.random.normal(0.0, 6.0 * scale)))
        ntheta = curr_theta + np.float32(np.random.normal(0.0, 0.25 * scale))
        nalpha = max(10, min(255, int(curr_alpha + np.random.normal(0.0, 8.0 * scale))))
        
        nr, ng, nb, delta = evaluate_candidate(target, canvas, nx_c, ny_c, nr_x, nr_y, ntheta, nalpha)
        if delta < curr_delta:
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
            
    return (float(curr_x_c), float(curr_y_c), float(curr_r_x), float(curr_r_y), float(curr_theta), int(curr_r), int(curr_g), int(curr_b), curr_alpha, float(curr_delta))

# --- Hill-Climbing Search ---
def find_best_ellipse(target, canvas, num_candidates=200, optimization_steps=50):
    height, width, _ = target.shape
    max_r = max(10.0, min(width, height) / 3.0)
    
    # 1. Parallel Random Search Phase
    x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta = parallel_random_search(
        target, canvas, num_candidates, width, height, max_r
    )
    
    # 2. Local JIT Hill-Climbing Optimization Phase
    x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta = serial_hill_climb(
        target, canvas, x_c, y_c, r_x, r_y, theta, alpha, r, g, b, delta, optimization_steps
    )
    
    return (x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta)

# --- Helper Functions ---
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
def run_generator(image_path, output_path=None, profile_path=None, layers_limit=None, candidates_limit=None, steps_limit=None, progress_callback=None):
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}", file=sys.stderr)
        return 1
        
    if not output_path:
        base_name, _ = os.path.splitext(image_path)
        output_path = f"{base_name}.json"
        
    # --- Load Settings from Profile ---
    profile = load_profile(profile_path)
    
    max_res = int(profile.get("maxResolution", 2000))
    profile_layers = int(profile.get("stopAt", 2000))
    profile_candidates = int(profile.get("randomSamples", 20000))
    profile_steps = int(profile.get("mutatedSamples", 200))
    save_every = int(profile.get("saveEvery", 10))
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
    
    print(f"Optimized Python Generator Core: Numba JIT Compiler Enabled")
    if profile_path:
        print(f"Profile: {os.path.basename(profile_path)}")
    print(f"Target: {image_path} -> Output: {output_path}")
    print(f"Layers limit: {layers} | Candidates: {candidates} | Optim steps: {steps}")
    
    # Load and preprocess image
    img = Image.open(image_path).convert("RGB")
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
        target = np.round(target / factor) * factor
    
    # Calculate target image average color
    avg_r = np.mean(target[:, :, 0])
    avg_g = np.mean(target[:, :, 1])
    avg_b = np.mean(target[:, :, 2])
    
    # Initialize canvas with target image average color
    canvas = np.zeros_like(target)
    canvas[:, :, 0] = avg_r
    canvas[:, :, 1] = avg_g
    canvas[:, :, 2] = avg_b
    
    # Construct shape array with canvas header shape
    shapes_list = []
    
    # Header format: type=1, data=[0, 0, w, h], color=[avg_r, avg_g, avg_b, 0]
    header = {
        "type": 1,
        "data": [0.0, 0.0, float(width), float(height)],
        "color": [int(avg_r), int(avg_g), int(avg_b), 0],
        "score": 0.0
    }
    shapes_list.append(header)
    
    start_time = time.time()
    last_print = time.time()
    
    for i in range(layers):
        result = find_best_ellipse(target, canvas, candidates, steps)
        if not result:
            continue
            
        x_c, y_c, r_x, r_y, theta, r, g, b, alpha, delta = result
        
        # Draw on canvas
        draw_ellipse(canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha)
        
        # Save shape
        shapes_list.append({
            "type": 32,
            "data": [x_c, y_c, r_x, r_y, float(math.degrees(theta))],
            "color": [r, g, b, alpha],
            "score": float(delta)
        })
        
        current_layer = i + 1
        
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
            progress_callback(current_layer, layers, speed, eta, canvas)
            
        if now - last_print >= 1.0 or i == layers - 1:
            pct = current_layer * 100.0 / layers
            sys.stdout.write(f"\rGenerating Shapes: {pct:5.1f}% | Layer {current_layer:4d}/{layers} | Speed: {speed:5.1f} layers/s | ETA: {eta:4.0f}s")
            sys.stdout.flush()
            last_print = now
            
    print()
    total_time = time.time() - start_time
    print(f"Shape generation completed in {total_time:.2f} seconds!")
    
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
