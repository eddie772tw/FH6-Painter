import numpy as np
import pytest


def test_taichi_evaluator_basic():
    from evaluators.taichi_evaluator import TaichiEvaluator

    target = np.random.rand(16, 16, 3).astype(np.float32)

    try:
        evaluator = TaichiEvaluator(target)
    except Exception as e:
        pytest.skip(f"Taichi instantiation threw exception: {e}")

    # If the evaluator is not initialized or not available, skip the test gracefully.
    if not evaluator.is_available() or not evaluator.initialized:
        pytest.skip(
            "Taichi JIT is not available or failed to initialize in this environment."
        )

    # Resilient device type check based on the actual backend name
    expected_device = "CPU" if "CPU" in evaluator.get_name() else "GPU"
    assert evaluator.get_device_type() == expected_device
    assert "Taichi JIT" in evaluator.get_name()
    assert evaluator.is_available() is True

    canvas = np.zeros_like(target)
    evaluator.draw_shape_on_canvas(canvas, 8.0, 8.0, 4.0, 4.0, 0.0, 0.5, 0.5, 0.5, 1.0)

    # Check if the drawn area has the correct color values (proves JIT draw kernel successfully executed)
    assert np.any(canvas[:, :, 0] > 0)

    evaluator.cleanup()


def test_taichi_evaluator_pure_gpu_search():
    from evaluators.taichi_evaluator import TaichiEvaluator

    target = np.random.rand(16, 16, 3).astype(np.float32)
    try:
        evaluator = TaichiEvaluator(target)
    except Exception as e:
        pytest.skip(f"Taichi instantiation threw exception: {e}")

    if not evaluator.is_available() or not evaluator.initialized:
        pytest.skip(
            "Taichi JIT is not available or failed to initialize in this environment."
        )

    canvas = np.zeros_like(target)
    params = {"optimization_steps": 5, "use_pure_gpu": True, "sa_enabled": False}

    # Verify execution of the JIT kernels on the active device (GPU or CPU fallback in headless CI)
    shape_params, delta = evaluator.search_best_shape(
        canvas, batch_size=128, params=params
    )
    assert len(shape_params) == 9
    assert delta < 99999999.0

    evaluator.cleanup()


def test_taichi_numba_consistency():
    from evaluators.numba_evaluator import NumbaEvaluator
    from evaluators.taichi_evaluator import TaichiEvaluator

    # Set up matching target image (32x32x3)
    np.random.seed(42)
    target = np.random.rand(32, 32, 3).astype(np.float32)

    try:
        taichi_eval = TaichiEvaluator(target)
    except Exception as e:
        pytest.skip(f"Taichi initialization threw exception: {e}")

    if not taichi_eval.is_available() or not taichi_eval.initialized:
        pytest.skip(
            "Taichi JIT is not available or failed to initialize in this environment."
        )

    numba_eval = NumbaEvaluator(target)

    # 1. Verify rendering equivalence (particularly boundary tolerance and clipping)
    canvas_ti = np.zeros_like(target)
    canvas_nb = np.zeros_like(target)

    # Draw an ellipse exceeding boundaries (centered at (2,2) with radius 15) to check clipping parity
    shape_args = (2.0, 2.0, 15.0, 10.0, 0.5, 0.8, 0.4, 0.6, 128.0)
    taichi_eval.draw_shape_on_canvas(canvas_ti, *shape_args)
    numba_eval.draw_shape_on_canvas(canvas_nb, *shape_args)

    # Calculate MAE and mismatch rate to accommodate float32/JIT boundary coordinate differences
    mae = np.mean(np.abs(canvas_ti - canvas_nb))
    diff_pixels = np.any(np.abs(canvas_ti - canvas_nb) > 1e-3, axis=-1)
    mismatch_rate = np.mean(diff_pixels)

    assert mae < 0.01, f"Mean absolute error too high: {mae}"
    assert mismatch_rate < 0.05, (
        f"Too many mismatched edge pixels: {mismatch_rate * 100:.2f}%"
    )

    # 2. Verify search output positioning and scaling bounds sanity
    canvas_search = np.zeros_like(target)
    params = {
        "optimization_steps": 10,
        "analytical_color_enabled": True,
        "use_pure_gpu": False,
    }

    # Execute Hybrid search (which utilizes Taichi random candidates selection + Numba CPU climbing)
    shape_params, delta = taichi_eval.search_best_shape(
        canvas_search, batch_size=256, params=params
    )

    # Assert shape scale parameters are well within maximum boundaries (not giant misplaced blobs)
    max_r = max(10.0, 32.0 / 3.0)
    assert shape_params[2] <= max_r * 1.1, (
        f"Candidate radius r_x is too large: {shape_params[2]}"
    )
    assert shape_params[3] <= max_r * 1.1, (
        f"Candidate radius r_y is too large: {shape_params[3]}"
    )
    assert delta < 9999999.0

    taichi_eval.cleanup()


def test_taichi_numba_contour_check_consistency():
    import taichi as ti

    from evaluators import numba_kernels
    from evaluators.numba_evaluator import NumbaEvaluator
    from evaluators.taichi_evaluator import (
        TaichiEvaluator,
        split_canvas_to_planar_gpu,
        taichi_parallel_search,
    )

    np.random.seed(42)
    target = np.random.rand(32, 32, 3).astype(np.float32) * 255.0
    alpha_mask = np.zeros((32, 32), dtype=np.float32)
    y, x = np.ogrid[:32, :32]
    # circular mask
    mask = (x - 16) ** 2 + (y - 16) ** 2 <= 10**2
    alpha_mask[mask] = 255.0

    try:
        taichi_eval = TaichiEvaluator(target, alpha_mask)
    except Exception as e:
        pytest.skip(f"Taichi initialization threw exception: {e}")

    if not taichi_eval.is_available() or not taichi_eval.initialized:
        pytest.skip("Taichi JIT is not available.")

    numba_eval = NumbaEvaluator(target, alpha_mask)

    canvas = np.zeros_like(target)
    canvas[5:27, 5:27, :] = 128.0

    # 1. Candidate inside contour
    # 2. Candidate crossing contour boundary (partially transparent)
    # 3. Candidate outside contour (fully transparent)
    candidates = np.array(
        [
            [16.0, 16.0, 5.0, 5.0, 0.0, 255.0],
            [16.0, 16.0, 11.0, 11.0, 0.5, 255.0],
            [3.0, 3.0, 4.0, 4.0, 0.0, 255.0],
        ],
        dtype=np.float32,
    )

    # Prepare GPU canvas
    taichi_eval.ti_canvas.from_numpy(canvas.astype(np.float32))
    split_canvas_to_planar_gpu(
        taichi_eval.ti_canvas,
        taichi_eval.ti_canvas_r,
        taichi_eval.ti_canvas_g,
        taichi_eval.ti_canvas_b,
        32,
        32,
    )

    canvas_r = np.ascontiguousarray(canvas[:, :, 0])
    canvas_g = np.ascontiguousarray(canvas[:, :, 1])
    canvas_b = np.ascontiguousarray(canvas[:, :, 2])

    for cand in candidates:
        x_c, y_c, r_x, r_y, theta, alpha = cand

        # Numba
        nb_res = numba_kernels.evaluate_candidate(
            numba_eval.target_r,
            numba_eval.target_g,
            numba_eval.target_b,
            canvas_r,
            canvas_g,
            canvas_b,
            x_c,
            y_c,
            r_x,
            r_y,
            theta,
            int(alpha),
            alpha_mask,
            True,  # check_contour=True
            False,
            np.zeros((1, 1), dtype=np.uint8),
            False,
            np.zeros((1, 1), dtype=np.float32),
            False,
            np.zeros((1, 1), dtype=np.float32),
            1,
            True,
            True,
        )

        # Taichi
        ti_cand = ti.ndarray(dtype=ti.f32, shape=(1, 6))
        ti_cand.from_numpy(cand.reshape(1, 6))
        ti_res = ti.ndarray(dtype=ti.f32, shape=(1, 4))

        taichi_parallel_search(
            taichi_eval.ti_target_r,
            taichi_eval.ti_target_g,
            taichi_eval.ti_target_b,
            taichi_eval.ti_canvas_r,
            taichi_eval.ti_canvas_g,
            taichi_eval.ti_canvas_b,
            ti_cand,
            ti_res,
            taichi_eval.ti_alpha,
            1,  # check_contour=True
            0,
            taichi_eval.ti_empty_u8,
            0,
            taichi_eval.ti_empty_f32,
            0,
            taichi_eval.ti_empty_f32,
            32,
            32,
            1,
            1,
        )
        ti_res_np = ti_res.to_numpy()[0]

        delta_nb = nb_res[3]
        delta_ti = ti_res_np[3]

        if delta_nb > 90000000.0:
            assert delta_ti > 90000000.0, (
                f"Candidate {cand} was rejected in Numba but not in Taichi"
            )
        else:
            assert abs(delta_nb - delta_ti) < 100.0, (
                f"Delta mismatch for candidate {cand}: Numba={delta_nb}, Taichi={delta_ti}"
            )

    taichi_eval.cleanup()
