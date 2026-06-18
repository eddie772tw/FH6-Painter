import json
import os
import tempfile

import numpy as np
import pytest
from PIL import Image


def test_generator_boundary_weight_map():
    from tools.fh6_painter_generator import get_boundary_weight_map

    alpha_mask = np.zeros((10, 10), dtype=np.float32)
    alpha_mask[2:8, 2:8] = 1.0

    weight_map = get_boundary_weight_map(alpha_mask, 5.0)
    assert weight_map.shape == (10, 10)
    # The sum of weight_map should be > 0 due to boundaries
    assert np.sum(weight_map) > 0.0


def test_scale_shapes_list():
    import copy

    from tools.fh6_painter_generator import scale_shapes_list

    shapes = [
        {"type": 1, "data": [0.0, 0.0, 100.0, 100.0], "color": [255, 255, 255, 0]},
        {"type": 32, "data": [10.0, 10.0, 5.0, 5.0, 0.0], "color": [255, 0, 0, 255]},
    ]

    # scale_shapes_list mutates in-place
    shapes_copy = copy.deepcopy(shapes)
    scale_shapes_list(shapes_copy, 2.0)

    assert shapes_copy[0]["data"][2] == 200.0
    assert shapes_copy[0]["data"][3] == 200.0

    assert shapes_copy[1]["data"][0] == 20.0
    assert shapes_copy[1]["data"][1] == 20.0
    assert shapes_copy[1]["data"][2] == 10.0
    assert shapes_copy[1]["data"][3] == 10.0


def test_load_profile():
    from tools.fh6_painter_generator import load_profile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        f.write("[Settings]\n")
        f.write("candidates = 500\n")
        f.write("shapes = 1\n")
        f.write("alpha = 128\n")
        f.write("mutations = 10\n")
        profile_path = f.name

    try:
        profile = load_profile(profile_path)
        assert int(profile["candidates"]) == 500
        assert int(profile["shapes"]) == 1
        assert int(profile["alpha"]) == 128
        assert int(profile["mutations"]) == 10
    finally:
        os.remove(profile_path)
