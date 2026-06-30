#!/usr/bin/env python3
import json
import os
import tempfile

import numpy as np
import pytest
from PIL import Image

from evaluators import EvaluatorFactory
from tools.fh6_painter_generator import run_generator

# 使用 PEP8 / Google Style / Black Style 規範


@pytest.fixture
def temp_image_path():
    """建立一個 16x16 的臨時 RGB 測試圖片。"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = f.name

    # 建立一個簡單的紅底藍色圓形圖片
    img = Image.new("RGB", (16, 16), color=(255, 0, 0))
    # 在圖片中央畫一個藍色點/矩形以製造擬合目標
    for x in range(6, 10):
        for y in range(6, 10):
            img.putpixel((x, y), (0, 0, 255))

    img.save(img_path)
    yield img_path

    # 測試結束後清理
    if os.path.exists(img_path):
        os.remove(img_path)


def test_generator_pure_python(temp_image_path):
    """整合測試：使用 Pure Python 引擎跑幾何生成器並驗證產出的 JSON。"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    # 先關閉與刪除，讓生成器可以重新建立與寫入
    os.remove(out_path)

    try:
        # 執行 3 層的生成，隨機採樣數設為 10，優化步數設為 5，極速運行
        res = run_generator(
            image_path=temp_image_path,
            output_path=out_path,
            layers_limit=3,
            candidates_limit=10,
            steps_limit=5,
            engine_name="NUMBA",
        )

        # 驗證回傳碼
        assert res == 0
        assert os.path.exists(out_path)

        # 讀取並驗證 JSON 資料
        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "shapes" in data
        shapes = data["shapes"]
        assert len(shapes) > 0

        # 第一個 shape 應為背景矩形 (type 1)
        assert shapes[0]["type"] == 1
        # 背景顏色應接近紅色的 (255, 0, 0)
        assert shapes[0]["color"][0] > 128
        assert shapes[0]["color"][2] < 128  # 藍色通道低

        # 其餘的 shape 應為橢圓 (type 32)
        if len(shapes) > 1:
            assert shapes[1]["type"] in (16, 32)
            # 應包含幾何特徵數據 [x_c, y_c, r_x, r_y, theta_deg]
            assert len(shapes[1]["data"]) == 5

    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_generator_numba(temp_image_path):
    """整合測試：使用 Numba JIT 引擎 (若可用) 跑幾何生成器並驗證產出。"""
    # 檢查 Numba 引擎是否可用
    evaluators = EvaluatorFactory.get_available_evaluators()
    numba_meta = next(e for e in evaluators if e["code"] == "NUMBA")
    if not numba_meta["available"]:
        pytest.skip("Numba JIT 評估器在當前系統中不可用，跳過測試")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    os.remove(out_path)

    try:
        res = run_generator(
            image_path=temp_image_path,
            output_path=out_path,
            layers_limit=3,
            candidates_limit=10,
            steps_limit=5,
            engine_name="NUMBA",
        )
        assert res == 0
        assert os.path.exists(out_path)

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "shapes" in data
        shapes = data["shapes"]
        assert len(shapes) > 0
        assert shapes[0]["type"] == 1

    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_early_convergence(temp_image_path):
    """驗證提早收斂優化：是否能在飽和時將圖層收斂至最接近的步進倍數並補足收斂。"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    os.remove(out_path)

    opt_settings = {
        "early_convergence": {
            "enabled": True,
            "check_interval": 2,
            "start_eval_ratio": 0.01,
            "redundancy_threshold": 0.0,  # 設為 0.0 強制觸發
            "convergence_step": 3,  # 自訂步進以利測試
        }
    }

    try:
        # 目標設為 6 層，在第 2 層觸發提早收斂，收斂目標應向上取整為 3 層 (步進為 3)
        res = run_generator(
            image_path=temp_image_path,
            output_path=out_path,
            layers_limit=6,
            candidates_limit=5,
            steps_limit=2,
            opt_settings=opt_settings,
            engine_name="NUMBA",
        )

        assert res == 0
        assert os.path.exists(out_path)

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        shapes = data["shapes"]
        # shapes 應該有 1 個背景 + 3 個收斂橢圓 = 4 個 shapes (而不是原定的 6 個)
        assert len(shapes) == 4
        assert shapes[0]["type"] == 1
        assert all(s["type"] in (16, 32) for s in shapes[1:])

    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_redundant_layer_consolidation():
    """驗證棄用圖層優化 (QoL 1)：被拋棄圖層是否被移至末端且位置設在畫布中心。"""
    from evaluators.numba_evaluator import NumbaEvaluator

    # 建立一個測試用的 shapes_list
    # 第一層是背景，第二層在 (8,8)，第三層在 (8,8) 完全遮擋第二層
    shapes_list = [
        {"type": 1, "data": [0.0, 0.0, 16.0, 16.0], "color": [255, 0, 0, 255]},
        {
            "type": 32,
            "data": [8.0, 8.0, 4.0, 4.0, 0.0],
            "color": [0, 0, 255, 255],
            "score": 10.0,
        },
        {
            "type": 32,
            "data": [8.0, 8.0, 4.0, 4.0, 0.0],
            "color": [0, 0, 255, 255],
            "score": 5.0,
        },
    ]

    evaluator = NumbaEvaluator(np.zeros((16, 16, 3), dtype=np.float32))
    res = evaluator.run_redundancy_check(shapes_list, 16, 16, final_check=True)

    # 驗證總長度依然為 3 (header + 1個有效 + 1個微型)
    assert len(res) == 3
    # 驗證有效圖層保持在上方
    assert res[1]["score"] == 5.0
    # 驗證被棄用的圖層被推到最末端 (index 2)
    assert res[2]["score"] == 0.0
    # 驗證棄用圖層的中心位置已改為畫布正中心 [16 / 2, 16 / 2] = [8.0, 8.0]
    assert res[2]["data"][0] == 8.0
    assert res[2]["data"][1] == 8.0
    assert res[2]["data"][2] == 0.01
    assert res[2]["data"][3] == 0.01


def test_generator_resume(temp_image_path):
    """測試續作功能：從現有 JSON 開始，成功繼續生成 shape 到設定的上限。"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f1:
        out_path1 = f1.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f2:
        out_path2 = f2.name

    os.remove(out_path1)
    os.remove(out_path2)

    try:
        # 1. 產生初始 3 個圖層 (1個背景矩形 + 2個橢圓)
        res1 = run_generator(
            image_path=temp_image_path,
            output_path=out_path1,
            layers_limit=2,
            candidates_limit=20,
            steps_limit=5,
            engine_name="NUMBA",
            opt_settings={"image_pyramid": {"enabled": False}},
        )
        assert res1 == 0
        assert os.path.exists(out_path1)

        with open(out_path1, "r", encoding="utf-8") as f:
            data1 = json.load(f)
        shapes1 = data1["shapes"]
        assert len(shapes1) == 3  # 1 background + 2 ellipses

        # 2. 從該 JSON 續作，設定目標為 4 個圖層 (1個背景矩形 + 3個橢圓)
        res2 = run_generator(
            image_path=temp_image_path,
            output_path=out_path2,
            layers_limit=3,
            candidates_limit=20,
            steps_limit=5,
            engine_name="NUMBA",
            resume_path=out_path1,
            opt_settings={"image_pyramid": {"enabled": False}},
        )
        assert res2 == 0
        assert os.path.exists(out_path2)

        with open(out_path2, "r", encoding="utf-8") as f:
            data2 = json.load(f)
        shapes2 = data2["shapes"]
        # 應該包含 1 背景 + 3 橢圓 = 4 個 shape
        assert len(shapes2) == 4

    finally:
        if os.path.exists(out_path1):
            os.remove(out_path1)
        if os.path.exists(out_path2):
            os.remove(out_path2)


def test_early_convergence_with_progressive_sampling(temp_image_path):
    """驗證漸進式像素採樣下提早收斂優化：是否會先提升像素採樣精度，然後才收斂使用的圖層數量。"""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        out_path = f.name
    os.remove(out_path)

    opt_settings = {
        "early_convergence": {
            "enabled": True,
            "check_interval": 2,
            "start_eval_ratio": 0.01,
            "redundancy_threshold": 0.0,  # 強制觸發
            "convergence_step": 3,  # 自訂步進以利測試
        },
        "image_pyramid": {
            "enabled": True,
        },
    }

    try:
        # 目標設為 20 層，自訂步進為 3，檢查間隔為 2
        # 在第 2 層觸發時：sample_step > 1 -> 降為 2，不收斂，繼續生成
        # 在第 4 層觸發時：sample_step > 1 -> 降為 1，不收斂，繼續生成
        # 在第 6 層觸發時：sample_step 已經為 1 -> 執行收斂 -> 目標調整為 ceil(6/3)*3 = 6 層
        # 故最後應生成 1 背景 + 6 個橢圓 = 7 個 shapes
        res = run_generator(
            image_path=temp_image_path,
            output_path=out_path,
            layers_limit=20,
            candidates_limit=5,
            steps_limit=2,
            opt_settings=opt_settings,
            engine_name="PURE_PYTHON",
        )

        assert res == 0
        assert os.path.exists(out_path)

        with open(out_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        shapes = data["shapes"]
        assert len(shapes) == 7
        assert shapes[0]["type"] == 1
        assert all(s["type"] in (16, 32) for s in shapes[1:])

    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
