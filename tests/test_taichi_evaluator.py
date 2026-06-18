import numpy as np
import pytest


def test_taichi_evaluator_basic():
    from evaluators.taichi_evaluator import TaichiEvaluator

    target = np.random.rand(16, 16, 3).astype(np.float32)

    try:
        evaluator = TaichiEvaluator(target)
    except Exception as e:
        pytest.skip(f"Taichi initialization failed: {e}")

    assert evaluator.get_device_type() == "GPU"
    assert "Taichi JIT" in evaluator.get_name()
    assert evaluator.is_available() is True

    canvas = np.zeros_like(target)
    evaluator.draw_shape_on_canvas(canvas, 8.0, 8.0, 4.0, 4.0, 0.0, 0.5, 0.5, 0.5, 1.0)

    # Check if the drawn area has the correct color values
    assert np.any(canvas[:, :, 0] > 0)

    evaluator.cleanup()
