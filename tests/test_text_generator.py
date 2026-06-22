import os

import pytest

from tools.text_generator import generate_text_shapes


def test_generate_text_shapes_basic():
    # Test with a simple text, fallback font should be used
    result = generate_text_shapes(
        "A", "nonexistent.ttf", 50, canvas_w=100, canvas_h=100
    )

    assert "shapes" in result
    assert isinstance(result["shapes"], list)
    assert len(result["shapes"]) > 0

    # First shape is always the bounding box / header
    header = result["shapes"][0]
    assert header["type"] == 1
    assert header["data"][2] == 100.0  # canvas_w
    assert header["data"][3] == 100.0  # canvas_h

    # Check if subsequent shapes are generated
    if len(result["shapes"]) > 1:
        data_shape = result["shapes"][1]
        assert data_shape["type"] == 1
        assert len(data_shape["data"]) == 5  # cx, cy, w, h, angle
        assert len(data_shape["color"]) == 4  # r, g, b, a
