#!/usr/bin/env python3
import argparse
import gc
import json
import math
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


HAS_DEPENDENCIES = True
try:
    import numpy as np
    from PIL import Image
except ImportError:
    HAS_DEPENDENCIES = False

if not HAS_DEPENDENCIES:
    print(
        "ERROR: High-performance Python shape generator requires 'pillow' and 'numpy'.",
        file=sys.stderr,
    )
    print("Please install them by running: pip install pillow numpy", file=sys.stderr)
    sys.exit(1)


def get_boundary_weight_map(alpha_mask, bias):
    """Computes a 2-pixel wide boundary weight map using pure standard NumPy."""
    if alpha_mask is None or alpha_mask.shape == (1, 1):
        return np.ones((1, 1), dtype=np.float32)
    height, width = alpha_mask.shape
    boundary_map = np.ones((height, width), dtype=np.float32)

    fg = alpha_mask > 127.0

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
    boundary = fg & (
        ~sh_up
        | ~sh_down
        | ~sh_left
        | ~sh_right
        | ~sh_up2
        | ~sh_down2
        | ~sh_left2
        | ~sh_right2
    )

    boundary_map[boundary] = np.float32(bias)
    return boundary_map


def scale_shapes_list(shapes, factor):
    """Scale all shape coordinates and radii by the given factor."""
    for s in shapes:
        if s["type"] in (16, 32):
            s["data"][0] = float(s["data"][0] * factor)  # X
            s["data"][1] = float(s["data"][1] * factor)  # Y
            s["data"][2] = float(s["data"][2] * factor)  # rX
            s["data"][3] = float(s["data"][3] * factor)  # rY
        elif s["type"] == 1:
            s["data"][2] = float(s["data"][2] * factor)  # w
            s["data"][3] = float(s["data"][3] * factor)  # h


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


def rebuild_uncovered_map_from_shapes(
    evaluator, width, height, has_alpha, alpha_mask, bias, shapes_list
):
    """Rebuilds the uncovered map by drawing all active shapes onto a fresh mask."""
    uncovered_map = evaluator.init_uncovered_map(width, height, has_alpha, bias)
    for s in shapes_list:
        if s["type"] in (16, 32):
            data = s["data"]
            x_c, y_c, r_x, r_y, theta_deg = data
            theta = math.radians(theta_deg)
            evaluator.update_uncovered_mask(uncovered_map, x_c, y_c, r_x, r_y, theta)
    return uncovered_map


def run_generator(
    image_path,
    output_path=None,
    profile_path=None,
    layers_limit=None,
    candidates_limit=None,
    steps_limit=None,
    progress_callback=None,
    opt_settings=None,
    engine_name=None,
    taichi_arch=None,
    taichi_device_id=None,
    use_pure_gpu=False,
    resume_path=None,
):
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}", file=sys.stderr)
        return 1

    if not profile_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # parent of 'tools'
        default_profile = os.path.join(
            project_root, "settings", "c. balanced - good quality and speed.ini"
        )
        if os.path.exists(default_profile):
            profile_path = default_profile
            print(
                f"No profile specified. Using default: {os.path.basename(profile_path)}"
            )

    if not output_path:
        img_base = os.path.splitext(os.path.basename(image_path))[0]
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)  # parent of 'tools'
        output_dir = os.path.join(project_root, "output", img_base)
        output_path = os.path.join(output_dir, f"{img_base}.json")

    # Load settings from profile
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

    layers = layers_limit if layers_limit is not None else profile_layers
    candidates = (
        candidates_limit if candidates_limit is not None else profile_candidates
    )
    steps = steps_limit if steps_limit is not None else profile_steps

    # Load optimization settings
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
                print(
                    f"Warning: Failed to load optimization settings: {e}",
                    file=sys.stderr,
                )

    opt_pyramid = opt_settings.get("image_pyramid", {})
    pyramid_enabled = opt_pyramid.get("enabled", False)
    pyramid_layers_threshold = opt_pyramid.get("pyramid_layers_threshold", 500)
    pyramid_stagnation = opt_pyramid.get("stagnation_threshold", 0.005)

    opt_importance = opt_settings.get("importance_sampling", {})
    importance_enabled = opt_importance.get("enabled", False)
    importance_interval = opt_importance.get("update_interval", 10)

    opt_sa = opt_settings.get("simulated_annealing", {})
    sa_enabled = opt_sa.get("enabled", False)
    sa_initial_temp = opt_sa.get("initial_temperature", 5000.0)
    sa_cooling_rate = opt_sa.get("cooling_rate", 0.95)

    opt_freeze = opt_settings.get("dynamic_freeze", {})
    freeze_enabled = opt_freeze.get("enabled", False)
    freeze_update_interval = opt_freeze.get("update_interval", 100)
    freeze_error_threshold = opt_freeze.get("error_threshold", 3)

    opt_weight = opt_settings.get("error_weighting", {})
    weight_enabled = opt_weight.get("enabled", False)
    weight_update_interval = opt_weight.get("update_interval", 100)

    opt_decay = opt_settings.get("decaying_shape", {})
    decay_enabled = opt_decay.get("enabled", False)
    decay_min_max_r = opt_decay.get("min_max_r", 5.0)

    opt_early = opt_settings.get("early_convergence", {})
    early_enabled = opt_early.get("enabled", False)
    early_interval = opt_early.get("check_interval", 100)
    early_ratio = opt_early.get("start_eval_ratio", 0.5)
    early_threshold = opt_early.get("redundancy_threshold", 0.75)
    early_step = opt_early.get("convergence_step", 50)

    resume_shapes = []
    if resume_path and os.path.exists(resume_path):
        try:
            with open(resume_path, "r", encoding="utf-8") as f:
                res_data = json.load(f)
                resume_shapes = res_data.get("shapes", [])
                print(
                    f"[Engine] Loaded {len(resume_shapes)} shapes from resume JSON: {resume_path}"
                )
        except Exception as e:
            print(
                f"Warning: Failed to load resume JSON {resume_path}: {e}",
                file=sys.stderr,
            )

    if resume_shapes:
        pyramid_enabled = False
        print("[Engine] Resume mode active. Image pyramid disabled.")

    if profile_path:
        print(f"Profile: {os.path.basename(profile_path)}")
    print(f"Target: {image_path} -> Output: {output_path}")
    print(f"Layers limit: {layers} | Candidates: {candidates} | Optim steps: {steps}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    img_raw = Image.open(image_path)
    has_alpha = img_raw.mode in ("RGBA", "LA") or (
        img_raw.mode == "P" and "transparency" in img_raw.info
    )
    if resume_shapes:
        header = resume_shapes[0]
        if header.get("type") == 1 and len(header.get("color", [])) >= 4:
            has_alpha = header["color"][3] <= 0
    if has_alpha:
        img = img_raw.convert("RGBA")
        print("Detected transparent background. Enabling Alpha-guided Ambient Padding.")
    else:
        img = img_raw.convert("RGB")

    width, height = img.size

    if max_res > 0 and (width > max_res or height > max_res):
        scale = max_res / max(width, height)
        new_w = int(width * scale)
        new_h = int(height * scale)
        print(
            f"Resizing target image from {width}x{height} to {new_w}x{new_h} to match maxResolution={max_res}"
        )
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        width, height = img.size

    target = np.array(img, dtype=np.float32)

    if 0 < posterize_levels < 256:
        print(f"Applying color posterization with {posterize_levels} levels...")
        factor = 255.0 / (posterize_levels - 1)
        if has_alpha:
            target[:, :, :3] = np.round(target[:, :, :3] / factor) * factor
        else:
            target = np.round(target / factor) * factor

    alpha_mask = np.zeros((1, 1), dtype=np.float32)
    if has_alpha:
        target_rgb = target[:, :, :3]
        alpha_mask = (target[:, :, 3] > 127.0).astype(np.float32) * 255.0
        fg_mask = alpha_mask > 127.0

        if np.any(fg_mask):
            avg_r = np.mean(target_rgb[fg_mask, 0])
            avg_g = np.mean(target_rgb[fg_mask, 1])
            avg_b = np.mean(target_rgb[fg_mask, 2])
        else:
            avg_r, avg_g, avg_b = 128.0, 128.0, 128.0

        bg_mask = ~fg_mask
        target_rgb[bg_mask, 0] = avg_r
        target_rgb[bg_mask, 1] = avg_g
        target_rgb[bg_mask, 2] = avg_b
        target = target_rgb
    else:
        avg_r = np.mean(target[:, :, 0])
        avg_g = np.mean(target[:, :, 1])
        avg_b = np.mean(target[:, :, 2])

    if resume_shapes:
        header = resume_shapes[0]
        if header.get("type") == 1 and len(header.get("color", [])) >= 4:
            avg_r_res, avg_g_res, avg_b_res, avg_a_res = header["color"]
            avg_r = float(avg_r_res)
            avg_g = float(avg_g_res)
            avg_b = float(avg_b_res)

    # Image pyramid multi-resolution preparation
    target_1_1 = target.copy()
    alpha_mask_1_1 = alpha_mask.copy()
    w_1_1, h_1_1 = width, height
    current_pyramid_stage = "1/1"

    if pyramid_enabled:
        w_1_2 = max(8, w_1_1 // 2)
        h_1_2 = max(8, h_1_1 // 2)
        img_1_2 = img.resize((w_1_2, h_1_2), Image.Resampling.LANCZOS)
        target_1_2 = np.array(img_1_2, dtype=np.float32)

        w_1_4 = max(4, w_1_1 // 4)
        h_1_4 = max(4, h_1_1 // 4)
        img_1_4 = img.resize((w_1_4, h_1_4), Image.Resampling.LANCZOS)
        target_1_4 = np.array(img_1_4, dtype=np.float32)

        if has_alpha:
            target_1_2_rgb = target_1_2[:, :, :3]
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

            target_1_4_rgb = target_1_4[:, :, :3]
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

        print(
            f"[Image Pyramid] 影像金字塔解析度已生成: 1/4 ({w_1_4}x{h_1_4}), 1/2 ({w_1_2}x{h_1_2}), 1/1 ({w_1_1}x{h_1_1})"
        )

        current_pyramid_stage = "1/4"
        target = target_1_4
        alpha_mask = alpha_mask_1_4
        width, height = w_1_4, h_1_4

    canvas = np.zeros_like(target)
    canvas[:, :, 0] = avg_r
    canvas[:, :, 1] = avg_g
    canvas[:, :, 2] = avg_b

    # Load computational engine
    from evaluators import EvaluatorFactory

    evaluator = EvaluatorFactory.create_evaluator(
        engine_name,
        target,
        alpha_mask,
        taichi_arch=taichi_arch,
        taichi_device_id=taichi_device_id,
    )

    shapes_list = []
    header = {
        "type": 1,
        "data": [0.0, 0.0, float(width), float(height)],
        "color": [int(avg_r), int(avg_g), int(avg_b), 0 if has_alpha else 255],
        "score": 0.0,
    }
    shapes_list.append(header)

    error_prob = None
    if importance_enabled:
        diff_mat = np.abs(target - canvas)
        err_heatmap = np.mean(diff_mat, axis=2)
        max_err = err_heatmap.max()
        error_prob = (
            (err_heatmap / max_err).astype(np.float32)
            if max_err > 0
            else np.zeros(err_heatmap.shape, dtype=np.float32)
        )

    freeze_mask = np.zeros((height, width), dtype=np.uint8) if freeze_enabled else None

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

    opt_uncovered = opt_settings.get("uncovered_bias", {})
    uncovered_enabled = opt_uncovered.get("enabled", True)
    uncovered_bias = opt_uncovered.get("bias", 5.0)

    uncovered_map = None
    if uncovered_enabled:
        uncovered_map = evaluator.init_uncovered_map(
            width, height, has_alpha, uncovered_bias
        )

    if resume_shapes:
        for s in resume_shapes[1:]:
            if s.get("type") in (16, 32):
                shapes_list.append(s)
                x_c, y_c, r_x, r_y, theta_deg = s["data"]
                r, g, b, alpha = s["color"]
                theta = math.radians(theta_deg)
                evaluator.draw_shape_on_canvas(
                    canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha
                )
                if uncovered_enabled and uncovered_map is not None:
                    evaluator.update_uncovered_mask(
                        uncovered_map, x_c, y_c, r_x, r_y, theta
                    )
        print(
            f"[Engine] Successfully resumed canvas state with {len(shapes_list) - 1} shapes."
        )

    base_max_r = max(10.0, min(width, height) / 3.0)

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

    # 提早收斂優化追蹤變數
    original_layers = layers
    prev_valid_layers = 0
    early_triggered = False

    starting_layer_count = len(shapes_list) - 1

    try:
        while (len(shapes_list) - 1 < layers) and (attempts < max_attempts):
            attempts += 1

            current_max_r = None
            if decay_enabled:
                progress_ratio = (len(shapes_list) - 1) / layers
                current_max_r = max(
                    decay_min_max_r, base_max_r * (1.0 - progress_ratio**2)
                )

            eval_params = {
                "optimization_steps": steps,
                "check_contour": has_alpha,
                "use_importance": importance_enabled,
                "error_prob": error_prob,
                "sa_enabled": sa_enabled,
                "sa_initial_temp": sa_initial_temp,
                "sa_cooling_rate": sa_cooling_rate,
                "current_max_r": current_max_r,
                "use_freeze": freeze_enabled,
                "freeze_mask": freeze_mask,
                "use_weight": use_weight_jit,
                "weight_map": weight_map,
                "use_uncovered": uncovered_enabled,
                "uncovered_map": uncovered_map,
                "use_pure_gpu": use_pure_gpu,
            }

            best_shape_params, delta = evaluator.search_best_shape(
                canvas, candidates, eval_params
            )

            if delta >= 90000000.0:
                print(
                    f"\n[Warning] Layer {len(shapes_list)}: Candidate shape rejected due to hard boundary/freeze conflict (delta={delta:.1f}). Skipping..."
                )
                continue

            x_c, y_c, r_x, r_y, theta, r, g, b, alpha = best_shape_params

            evaluator.draw_shape_on_canvas(
                canvas, x_c, y_c, r_x, r_y, theta, r, g, b, alpha
            )

            if uncovered_enabled and uncovered_map is not None:
                evaluator.update_uncovered_mask(
                    uncovered_map, x_c, y_c, r_x, r_y, theta
                )

            shapes_list.append(
                {
                    "type": 32,
                    "data": [x_c, y_c, r_x, r_y, float(math.degrees(theta))],
                    "color": [int(r), int(g), int(b), int(alpha)],
                    "score": float(delta),
                }
            )

            total_generated_so_far += 1
            current_layer = len(shapes_list) - 1

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

            if pyramid_enabled:
                if current_pyramid_stage == "1/4":
                    if current_layer >= stage_1_4_limit or stagnated:
                        print(
                            f"\n[Image Pyramid] 1/4 解析度階段完成於層數 {current_layer} (停滯={stagnated})。正在切換至 1/2 解析度..."
                        )
                        scale_shapes_list(shapes_list, 2.0)

                        evaluator.cleanup()
                        target = target_1_2
                        alpha_mask = alpha_mask_1_2
                        width, height = w_1_2, h_1_2
                        evaluator = EvaluatorFactory.create_evaluator(
                            engine_name,
                            target,
                            alpha_mask,
                            taichi_arch=taichi_arch,
                            taichi_device_id=taichi_device_id,
                        )

                        canvas = np.zeros_like(target)
                        evaluator.rebuild_canvas(
                            canvas, shapes_list, avg_r, avg_g, avg_b
                        )
                        if uncovered_enabled:
                            uncovered_map = rebuild_uncovered_map_from_shapes(
                                evaluator,
                                width,
                                height,
                                has_alpha,
                                alpha_mask,
                                uncovered_bias,
                                shapes_list,
                            )
                        current_pyramid_stage = "1/2"
                        recent_deltas = []
                        if importance_enabled:
                            diff_mat = np.abs(target - canvas)
                            err_heatmap = np.mean(diff_mat, axis=2)
                            max_err = err_heatmap.max()
                            error_prob = (
                                (err_heatmap / max_err).astype(np.float32)
                                if max_err > 0
                                else np.zeros(err_heatmap.shape, dtype=np.float32)
                            )
                        if freeze_enabled:
                            freeze_mask = np.zeros((h_1_2, w_1_2), dtype=np.uint8)
                        if boundary_enabled and has_alpha:
                            boundary_weight_map = get_boundary_weight_map(
                                alpha_mask, boundary_bias
                            )
                        if use_weight_jit:
                            weight_map = boundary_weight_map.copy()
                        base_max_r = max(10.0, min(w_1_2, h_1_2) / 3.0)
                elif current_pyramid_stage == "1/2":
                    if current_layer >= stage_1_2_limit or stagnated:
                        print(
                            f"\n[Image Pyramid] 1/2 解析度階段完成於層數 {current_layer} (停滯={stagnated})。正在切換至 1/1 解析度 (Fine Phase)..."
                        )
                        scale_shapes_list(shapes_list, 2.0)

                        evaluator.cleanup()
                        target = target_1_1
                        alpha_mask = alpha_mask_1_1
                        width, height = w_1_1, h_1_1
                        evaluator = EvaluatorFactory.create_evaluator(
                            engine_name,
                            target,
                            alpha_mask,
                            taichi_arch=taichi_arch,
                            taichi_device_id=taichi_device_id,
                        )

                        canvas = np.zeros_like(target)
                        evaluator.rebuild_canvas(
                            canvas, shapes_list, avg_r, avg_g, avg_b
                        )
                        if uncovered_enabled:
                            uncovered_map = rebuild_uncovered_map_from_shapes(
                                evaluator,
                                width,
                                height,
                                has_alpha,
                                alpha_mask,
                                uncovered_bias,
                                shapes_list,
                            )
                        current_pyramid_stage = "1/1"
                        recent_deltas = []
                        if importance_enabled:
                            diff_mat = np.abs(target - canvas)
                            err_heatmap = np.mean(diff_mat, axis=2)
                            max_err = err_heatmap.max()
                            error_prob = (
                                (err_heatmap / max_err).astype(np.float32)
                                if max_err > 0
                                else np.zeros(err_heatmap.shape, dtype=np.float32)
                            )
                        if freeze_enabled:
                            freeze_mask = np.zeros((h_1_1, w_1_1), dtype=np.uint8)
                        if boundary_enabled and has_alpha:
                            boundary_weight_map = get_boundary_weight_map(
                                alpha_mask, boundary_bias
                            )
                        if use_weight_jit:
                            weight_map = boundary_weight_map.copy()
                        base_max_r = max(10.0, min(w_1_1, h_1_1) / 3.0)

            if importance_enabled and total_generated_so_far % importance_interval == 0:
                diff_mat = np.abs(target - canvas)
                err_heatmap = np.mean(diff_mat, axis=2)
                max_err = err_heatmap.max()
                error_prob = (
                    (err_heatmap / max_err).astype(np.float32)
                    if max_err > 0
                    else np.zeros(err_heatmap.shape, dtype=np.float32)
                )

            freeze_update_needed = (
                freeze_enabled
                and total_generated_so_far > 0
                and total_generated_so_far % freeze_update_interval == 0
            )
            weight_update_needed = (
                weight_enabled
                and total_generated_so_far > 0
                and total_generated_so_far % weight_update_interval == 0
            )
            if freeze_update_needed or weight_update_needed:
                diff_mat = np.abs(target - canvas)
                per_pixel_err = np.mean(diff_mat[:, :, :3], axis=2)

                if freeze_update_needed:
                    freeze_mask = np.where(
                        per_pixel_err < freeze_error_threshold, np.uint8(1), np.uint8(0)
                    ).astype(np.uint8)
                    frozen_pct = (
                        np.sum(freeze_mask)
                        * 100.0
                        / (freeze_mask.shape[0] * freeze_mask.shape[1])
                    )
                    print(
                        f"\n[Freeze Mask] 層數 {current_layer}: 凍結了 {frozen_pct:.1f}% 的像素 (閾值={freeze_error_threshold})"
                    )

                if weight_update_needed:
                    max_err = per_pixel_err.max()
                    if max_err > 0:
                        normalized_err = per_pixel_err / max_err
                        dynamic_weights = (1.0 + normalized_err * 9.0).astype(
                            np.float32
                        )
                        if boundary_enabled and has_alpha:
                            weight_map = (dynamic_weights * boundary_weight_map).astype(
                                np.float32
                            )
                        else:
                            weight_map = dynamic_weights
                    else:
                        weight_map = (
                            boundary_weight_map.copy()
                            if (boundary_enabled and has_alpha)
                            else np.ones((height, width), dtype=np.float32)
                        )

            # Midway redundancy check & canvas rebuilding
            is_normal_trigger = (
                total_generated_so_far > 0 and total_generated_so_far % 500 == 0
            )
            is_test_trigger = (
                layers < 500
                and total_generated_so_far >= 10
                and (total_generated_so_far - 10) % 10 == 0
            )
            is_early_trigger = (
                early_enabled
                and not early_triggered
                and total_generated_so_far >= int(early_ratio * layers)
                and (total_generated_so_far % early_interval == 0)
            )

            if is_normal_trigger or is_test_trigger or is_early_trigger:
                print(
                    f"\n[Engine] Reached {total_generated_so_far} generated layers. Running mid-way redundancy check..."
                )
                shapes_list = evaluator.run_redundancy_check(
                    shapes_list, width, height, final_check=False
                )
                evaluator.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)
                if uncovered_enabled:
                    uncovered_map = rebuild_uncovered_map_from_shapes(
                        evaluator,
                        width,
                        height,
                        has_alpha,
                        alpha_mask,
                        uncovered_bias,
                        shapes_list,
                    )
                current_layer = len(shapes_list) - 1

                # 提早收斂飽和度評估與執行
                if is_early_trigger:
                    G = total_generated_so_far - prev_valid_layers
                    retained = current_layer - prev_valid_layers
                    if G > 0:
                        redundancy_ratio = 1.0 - (retained / G)
                        print(
                            f"\n[Early Convergence] 飽和度評估 - 目前生成: {total_generated_so_far} 層 | 有效圖層: {current_layer} 層"
                        )
                        print(
                            f"[Early Convergence] 過去 {G} 層中，有效保留: {retained} 層 | 淘汰率: {redundancy_ratio * 100:.1f}% (閾值: {early_threshold * 100:.1f}%)"
                        )

                        if redundancy_ratio >= early_threshold:
                            print(
                                f"\n[Early Convergence] 偵測到細節已飽和 (淘汰率 {redundancy_ratio * 100:.1f}% >= 閾值 {early_threshold * 100:.1f}%)！開始執行提早收斂..."
                            )

                            # 收斂層數則以 early_step 為步進向上取整，且不得超過原定最大層數 original_layers
                            best_t = min(
                                int(math.ceil(current_layer / float(early_step)))
                                * early_step,
                                original_layers,
                            )

                            print(
                                f"[Early Convergence] 執行補足策略：將目標層數 layers 調整為 {best_t} 層 (當前有效: {current_layer} 層)"
                            )
                            layers = best_t
                            early_triggered = True

                            if current_layer >= layers:
                                print(
                                    "[Early Convergence] 當前層數已達到或超過收斂目標，停止生成。"
                                )
                                break

                # 更新 prev_valid_layers 供下一次區間評估使用
                prev_valid_layers = current_layer

            if current_layer in save_at or (
                save_every > 0
                and current_layer % save_every == 0
                and current_layer < layers
            ):
                base_dir = os.path.dirname(output_path) or "."
                file_base, file_ext = os.path.splitext(os.path.basename(output_path))
                inter_path = os.path.join(
                    base_dir, f"{file_base}_{current_layer}{file_ext}"
                )
                try:
                    with open(inter_path, "w", encoding="utf-8") as f:
                        json.dump({"shapes": shapes_list}, f, indent=2)
                except Exception as e:
                    print(
                        f"\nWarning: Failed to save intermediate JSON to {inter_path}: {e}",
                        file=sys.stderr,
                    )

            now = time.time()
            elapsed = now - start_time
            generated_in_session = current_layer - starting_layer_count
            speed = generated_in_session / elapsed if elapsed > 0 else 0.0
            eta = (layers - current_layer) / speed if speed > 0 else 0.0

            if progress_callback:
                if has_alpha:
                    canvas_rgba = np.zeros((height, width, 4), dtype=np.float32)
                    canvas_rgba[:, :, :3] = canvas
                    canvas_rgba[:, :, 3] = alpha_mask
                    cb_res = progress_callback(
                        current_layer, layers, speed, eta, canvas_rgba
                    )
                else:
                    cb_res = progress_callback(
                        current_layer, layers, speed, eta, canvas
                    )

                if cb_res is False or cb_res == "ABORT":
                    print(
                        "\n[Engine] Shape generation aborted by progress callback cancellation request."
                    )
                    break

            if now - last_print >= 1.0 or current_layer == layers:
                pct = current_layer * 100.0 / layers
                if not progress_callback:
                    sys.stdout.write(
                        f"\rGenerating Shapes: {pct:5.1f}% | Layer {current_layer:4d}/{layers} | Speed: {speed:5.1f} layers/s | ETA: {eta:4.0f}s"
                    )
                    sys.stdout.flush()
                else:
                    if current_layer % 500 == 0 or current_layer == layers:
                        print(
                            f"[Engine] Shape generation progress: {pct:.1f}% ({current_layer}/{layers})"
                        )
                last_print = now

        print()
        gc.enable()
        total_time = time.time() - start_time

        print(f"Shape generation completed in {total_time:.2f} seconds!")

        if pyramid_enabled and current_pyramid_stage != "1/1":
            if current_pyramid_stage == "1/4":
                print("\n[Image Pyramid] 正在從 1/4 直接升級至 1/1 解析度...")
                scale_shapes_list(shapes_list, 4.0)
            elif current_pyramid_stage == "1/2":
                print("\n[Image Pyramid] 正在從 1/2 升級至 1/1 解析度...")
                scale_shapes_list(shapes_list, 2.0)

            evaluator.cleanup()
            target = target_1_1
            alpha_mask = alpha_mask_1_1
            width, height = w_1_1, h_1_1
            evaluator = EvaluatorFactory.create_evaluator(
                engine_name,
                target,
                alpha_mask,
                taichi_arch=taichi_arch,
                taichi_device_id=taichi_device_id,
            )

            canvas = np.zeros_like(target)
            evaluator.rebuild_canvas(canvas, shapes_list, avg_r, avg_g, avg_b)
            current_pyramid_stage = "1/1"

        # Final redundancy check
        print(
            "\n[Engine] Running final redundancy check to reserve layer count and reset occluded shapes..."
        )
        shapes_list = evaluator.run_redundancy_check(
            shapes_list, width, height, final_check=True
        )

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"shapes": shapes_list}, f, indent=2)

        print(f"JSON geometry successfully written to: {output_path}")
        return 0

    finally:
        evaluator.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="High-performance Python Image-to-JSON Shape Generator"
    )
    parser.add_argument("image_path", help="Path to input image file")
    parser.add_argument("--output", "-o", help="Path to save output JSON geometry")
    parser.add_argument("--profile", "-p", help="Path to settings INI profile")
    parser.add_argument(
        "--layers",
        "-l",
        type=int,
        default=None,
        help="Number of layers/shapes to generate (overrides profile)",
    )
    parser.add_argument(
        "--candidates",
        "-c",
        type=int,
        default=None,
        help="Number of random candidates per shape (overrides profile)",
    )
    parser.add_argument(
        "--steps",
        "-s",
        type=int,
        default=None,
        help="Number of local hill-climbing steps (overrides profile)",
    )
    parser.add_argument(
        "--engine",
        "-e",
        default="NUMBA",
        choices=["NUMBA", "TAICHI", "PURE_PYTHON"],
        help="Computational engine plugin to use (NUMBA, TAICHI, PURE_PYTHON)",
    )
    parser.add_argument(
        "--resume",
        "-resume",
        help="Path to resume JSON checkpoint file",
    )

    args = parser.parse_args()
    return run_generator(
        image_path=args.image_path,
        output_path=args.output,
        profile_path=args.profile,
        layers_limit=args.layers,
        candidates_limit=args.candidates,
        steps_limit=args.steps,
        engine_name=args.engine,
        resume_path=args.resume,
    )


if __name__ == "__main__":
    sys.exit(main())
