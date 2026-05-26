#!/usr/bin/env python3
import numpy as np
import pytest
from evaluators import EvaluatorFactory
from evaluators.pure_python_evaluator import PurePythonEvaluator
from evaluators.numba_evaluator import NumbaEvaluator

# 使用 PEP8 / Google Style / Black Style 規範

def test_evaluator_factory_scan():
    """測試 EvaluatorFactory 是否能順利掃描並回傳可用評估器列表。"""
    evaluators = EvaluatorFactory.get_available_evaluators()
    assert len(evaluators) > 0
    codes = [e["code"] for e in evaluators]
    assert "PURE_PYTHON" in codes
    assert "NUMBA" in codes
    assert "TAICHI" in codes


def test_pure_python_evaluator():
    """測試 PurePythonEvaluator 的基礎渲染與運算功能。"""
    # 建立 16x16 的隨機圖像作為測試目標
    np.random.seed(42)
    target = np.random.rand(16, 16, 3).astype(np.float32)

    evaluator = PurePythonEvaluator(target)
    assert evaluator.get_name() == "Pure Python (Baseline)"
    assert evaluator.get_device_type() == "CPU"
    assert evaluator.is_available() is True

    # 測試畫布初始化與形狀繪製
    canvas = np.zeros_like(target)
    evaluator.draw_shape_on_canvas(
        canvas=canvas,
        x_c=8.0,
        y_c=8.0,
        r_x=4.0,
        r_y=4.0,
        theta_rad=0.0,
        r=1.0,
        g=0.0,
        b=0.0,
        alpha=0.8
    )
    # 確認畫布有被更新 (有紅色像素被著色)
    assert np.sum(canvas[:, :, 0]) > 0
    assert np.sum(canvas[:, :, 1]) == 0
    assert np.sum(canvas[:, :, 2]) == 0

    # 測試未覆蓋優先度地圖
    uncovered_map = evaluator.init_uncovered_map(16, 16, has_alpha=False, bias=0.1)
    assert uncovered_map.shape == (16, 16)
    assert np.all(uncovered_map >= 0.1)

    evaluator.update_uncovered_mask(
        uncovered_map=uncovered_map,
        x_c=8.0,
        y_c=8.0,
        r_x=4.0,
        r_y=4.0,
        theta_rad=0.0
    )
    # 更新後中心部分區域權重應被重置為 1.0 (代表該像素已被覆蓋，優先度權重降為基數 1.0)
    assert uncovered_map[8, 8] == 1.0


def test_numba_evaluator():
    """測試 NumbaEvaluator 的基礎渲染與運算功能。"""
    np.random.seed(42)
    target = np.random.rand(16, 16, 3).astype(np.float32)

    evaluators = EvaluatorFactory.get_available_evaluators()
    numba_meta = next(e for e in evaluators if e["code"] == "NUMBA")

    if not numba_meta["available"]:
        pytest.skip("Numba JIT 評估器在當前系統中不可用，跳過測試")

    evaluator = NumbaEvaluator(target)
    assert "Numba JIT" in evaluator.get_name()
    assert evaluator.get_device_type() == "CPU"
    assert evaluator.is_available() is True

    # 測試畫布繪製
    canvas = np.zeros_like(target)
    evaluator.draw_shape_on_canvas(
        canvas=canvas,
        x_c=8.0,
        y_c=8.0,
        r_x=4.0,
        r_y=4.0,
        theta_rad=0.0,
        r=1.0,
        g=0.0,
        b=0.0,
        alpha=0.8
    )
    assert np.sum(canvas[:, :, 0]) > 0

    # 測試未覆蓋優先度地圖
    uncovered_map = evaluator.init_uncovered_map(16, 16, has_alpha=False, bias=0.1)
    evaluator.update_uncovered_mask(
        uncovered_map=uncovered_map,
        x_c=8.0,
        y_c=8.0,
        r_x=4.0,
        r_y=4.0,
        theta_rad=0.0
    )
    assert uncovered_map[8, 8] == 1.0


def test_evaluator_factory_fallback():
    """測試 EvaluatorFactory 在請求不可用引擎時的降級安全機制。"""
    target = np.zeros((16, 16, 3), dtype=np.float32)

    # 故意要求載入不可用的 TAICHI 引擎 (即便在 CI 無 GPU 環境下，或者是將其 mock 掉)
    # 我們可以利用一個非常規或不支援的 engine_name 來強迫觸發 fallback 機制
    evaluator = EvaluatorFactory.create_evaluator("INVALID_ENGINE_NAME", target)

    # 它應該能安全地降級並返回一個有效的 Evaluator (Numba 或 PurePython)
    assert evaluator is not None
    assert evaluator.get_device_type() == "CPU"

    # 清理資源
    evaluator.cleanup()
