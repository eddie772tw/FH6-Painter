import json
import os
import tempfile

import pytest

from fh6_painter_launcher import (
    build_save_at,
    count_importable_shapes,
    is_forza_painter_canvas_header,
    is_json,
    pick_template_layer_count,
    replace_setting,
)


def test_is_json():
    assert is_json("test.json") is True
    assert is_json("TEST.JSON") is True
    assert is_json("test.png") is False


def test_is_forza_painter_canvas_header():
    valid = {"type": 1, "data": [0.0, 0.0, 100, 100], "color": [255, 255, 255, 0]}
    assert is_forza_painter_canvas_header(valid) is True

    invalid_type = {
        "type": 2,
        "data": [0.0, 0.0, 100, 100],
        "color": [255, 255, 255, 0],
    }
    assert is_forza_painter_canvas_header(invalid_type) is False

    invalid_data = {
        "type": 1,
        "data": [1.0, 0.0, 100, 100],
        "color": [255, 255, 255, 0],
    }
    assert is_forza_painter_canvas_header(invalid_data) is False


def test_count_importable_shapes():
    data = {
        "shapes": [
            {"type": 1, "data": [0.0, 0.0, 100, 100], "color": [255, 255, 255, 0]},
            {"type": 32, "data": [10, 10, 5, 5, 0], "color": [255, 0, 0, 255]},
            {"type": 32, "data": [20, 20, 5, 5, 0], "color": [0, 255, 0, 255]},
        ]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name

    try:
        assert count_importable_shapes(path) == 2
        assert pick_template_layer_count(path) == 1500
    finally:
        os.remove(path)


def test_build_save_at():
    assert build_save_at(1500) == "500,1000,1500"
    assert build_save_at(1200) == "500,1000,1200"


def test_replace_setting():
    text = "saveAt = 500\nstopAt = 1000"
    res = replace_setting(text, "saveAt", "500,1000,1500")
    assert "saveAt = 500,1000,1500" in res
    assert "stopAt = 1000" in res

    res = replace_setting(text, "newKey", "123")
    assert "newKey = 123" in res
