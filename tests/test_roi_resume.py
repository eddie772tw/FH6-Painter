import os
from unittest.mock import MagicMock, patch

import pytest

from backend.server import PainterServer


def test_resume_roi_ignores_masked_images():
    """Verifies that when resuming generation, the server correctly ignores
    previously generated `_masked.png` files to prevent ROI bounds from lingering.
    """
    server = PainterServer()
    loop = MagicMock()

    config = {
        "img_path": "output/test/test.json",
        "roi": {
            "enabled": False
        },  # Disable ROI to see if it mistakenly picks up masked.png
    }

    def mock_exists(path):
        if path.endswith(".json"):
            return True
        if "test_masked.png" in path:
            return True
        if "test.png" in path:
            return True
        return False

    def mock_glob(pattern):
        if "test*" in pattern and pattern.endswith(".png"):
            # Return masked image first to simulate the bug scenario where it is picked
            # instead of the original image.
            return ["output/test/test_masked.png", "output/test/test.png"]
        return []

    with (
        patch("backend.server.os.path.exists", side_effect=mock_exists),
        patch("glob.glob", side_effect=mock_glob),
        patch("shutil.copy2"),
        patch("backend.server.os.makedirs"),
        patch.object(PainterServer, "_sync_broadcast"),
        patch("tools.fh6_painter_generator.run_generator") as mock_run_gen,
    ):
        mock_run_gen.return_value = 0
        server.run_generator_blocking(config, loop)

        # Verify run_generator was called with the correct target image
        mock_run_gen.assert_called_once()
        args, kwargs = mock_run_gen.call_args

        print("KWARGS:", kwargs)
        target_image = kwargs.get("image_path", "")
        # The target_image_path should be "test.png" NOT "test_masked.png"
        assert target_image.endswith("test.png")
        assert not target_image.endswith("test_masked.png")
