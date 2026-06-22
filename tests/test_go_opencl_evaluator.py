import numpy as np
import pytest


def test_go_opencl_evaluator_methods():
    from evaluators.go_opencl_evaluator import GoOpenCLEvaluator

    target = np.random.rand(16, 16, 3).astype(np.float32)
    evaluator = GoOpenCLEvaluator(target)

    # Test initialization
    assert evaluator.get_name() == "Go OpenCL (GPU, Fastest)"
    assert evaluator.get_device_type() == "GPU"
    assert isinstance(evaluator.is_available(), bool)

    # Check that NotImplementError is correctly raised for JIT interface
    with pytest.raises(NotImplementedError):
        evaluator.search_best_shape(target, 4, {})

    with pytest.raises(NotImplementedError):
        evaluator.draw_shape_on_canvas(
            target, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        )

    # Check fallback implementations
    canvas = np.zeros_like(target)
    evaluator.rebuild_canvas(canvas, [], 0.0, 0.0, 0.0)

    uncovered_map = evaluator.init_uncovered_map(16, 16, has_alpha=False, bias=0.1)
    assert uncovered_map.shape == (16, 16)

    evaluator.cleanup()
