import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from backend.server import PainterServer


class FakeWebSocket:
    def __init__(self):
        self.sent_messages = []

    async def send(self, message):
        self.sent_messages.append(message)


@pytest.fixture
def server():
    return PainterServer()


@pytest.fixture
def fake_ws():
    return FakeWebSocket()


@pytest.mark.asyncio
async def test_ping(server, fake_ws):
    await server.handle_message(fake_ws, json.dumps({"action": "ping"}))
    assert len(fake_ws.sent_messages) == 1
    resp = json.loads(fake_ws.sent_messages[0])
    assert resp["action"] == "pong"


@pytest.mark.asyncio
async def test_get_engines(server, fake_ws):
    await server.handle_message(fake_ws, json.dumps({"action": "get_engines"}))
    assert len(fake_ws.sent_messages) == 1
    resp = json.loads(fake_ws.sent_messages[0])
    assert resp["action"] == "engines_list"
    assert "data" in resp
    assert isinstance(resp["data"], list)


@pytest.mark.asyncio
async def test_stop_generation(server, fake_ws):
    assert server.cancel_flag is False
    await server.handle_message(fake_ws, json.dumps({"action": "stop_generation"}))
    assert server.cancel_flag is True


@pytest.mark.asyncio
async def test_inject_geometry_success(server, fake_ws):
    server.clients.add(fake_ws)

    # Patch the run_importer function that is dynamically imported
    with patch("tools.fh6_import_layer_table.run_importer", return_value=0) as mock_run:
        # Inject it into sys.modules so the dynamic import in server.py finds our mock
        import sys

        if "tools.fh6_import_layer_table" not in sys.modules:
            mock_module = MagicMock()
            mock_module.run_importer = mock_run
            sys.modules["tools.fh6_import_layer_table"] = mock_module
        else:
            sys.modules["tools.fh6_import_layer_table"].run_importer = mock_run

        await server.inject_geometry({"json_path": "test.png", "layers": 100})

        assert len(fake_ws.sent_messages) >= 2
        started = json.loads(fake_ws.sent_messages[0])
        assert started["action"] == "injection_status"
        assert started["status"] == "started"

        completed = json.loads(fake_ws.sent_messages[1])
        assert completed["action"] == "injection_status"
        assert completed["status"] == "completed"

        mock_run.assert_called_once()
        args = mock_run.call_args[0]
        # Check that the path reconstructed replaces .png with .json
        assert "test.json" in args[0]


@pytest.mark.asyncio
async def test_start_generation(server, fake_ws):
    server.clients.add(fake_ws)

    def fake_run(config, loop):
        # Fake blocking task
        pass

    with patch.object(server, "run_generator_blocking", side_effect=fake_run):
        await server.start_generation({"img_path": "test.png", "layers": 10})

        assert len(fake_ws.sent_messages) >= 2
        started = json.loads(fake_ws.sent_messages[0])
        assert started["action"] == "generation_status"
        assert started["status"] == "started"

        completed = json.loads(fake_ws.sent_messages[-1])
        assert completed["action"] == "generation_status"
        assert completed["status"] == "completed"


@pytest.mark.asyncio
async def test_get_profiles(server, fake_ws):
    with patch("backend.server.scan_profiles") as mock_scan:
        mock_scan.return_value = [
            {"filename": "test.ini", "name": "test", "desc": "desc", "path": "path"}
        ]
        await server.handle_message(fake_ws, json.dumps({"action": "get_profiles"}))
        assert len(fake_ws.sent_messages) == 1
        resp = json.loads(fake_ws.sent_messages[0])
        assert resp["action"] == "profiles_list"
        assert len(resp["data"]) == 1
        assert resp["data"][0]["name"] == "test"


@pytest.mark.asyncio
async def test_get_gpus(server, fake_ws):
    with patch("backend.server.scan_gpus") as mock_scan:
        mock_scan.return_value = ["NVIDIA RTX 4090"]
        await server.handle_message(fake_ws, json.dumps({"action": "get_gpus"}))
        assert len(fake_ws.sent_messages) == 1
        resp = json.loads(fake_ws.sent_messages[0])
        assert resp["action"] == "gpus_list"
        assert resp["data"] == ["NVIDIA RTX 4090"]


@pytest.mark.asyncio
async def test_get_profile_settings(server, fake_ws):
    with (
        patch("os.path.exists", return_value=True),
        patch(
            "tools.fh6_painter_generator.load_profile",
            return_value={
                "stopAt": "1000",
                "randomSamples": "5000",
                "mutatedSamples": "100",
            },
        ),
        patch("builtins.open", return_value=MagicMock()) as mock_open,
    ):
        # Mock description reading
        mock_file = MagicMock()
        mock_file.__enter__.return_value = ["description = custom desc"]
        mock_open.return_value = mock_file

        await server.handle_message(
            fake_ws,
            json.dumps({"action": "get_profile_settings", "profile_name": "custom"}),
        )
        assert len(fake_ws.sent_messages) == 1
        resp = json.loads(fake_ws.sent_messages[0])
        assert resp["action"] == "profile_settings"
        assert resp["settings"]["stopAt"] == "1000"
        assert resp["settings"]["description"] == "custom desc"


@pytest.mark.asyncio
async def test_get_checkpoints(server, fake_ws):
    import os
    expected_path = os.path.join("output", "test", "test_500.json")
    input_path = os.path.join("test", "test.png")
    with (
        patch("os.path.exists", return_value=True),
        patch(
            "glob.glob", return_value=[expected_path]
        ),
    ):
        await server.handle_message(
            fake_ws,
            json.dumps({"action": "get_checkpoints", "img_path": input_path}),
        )
        assert len(fake_ws.sent_messages) == 1
        resp = json.loads(fake_ws.sent_messages[0])
        assert resp["action"] == "checkpoints_list"
        assert len(resp["checkpoints"]) == 1
        assert resp["checkpoints"][0]["layer"] == 500


def test_get_project_base():
    from backend.server import get_project_base
    import os

    # 1. Standard path in output folder
    p1 = os.path.join("output", "image", "image.100.json")
    assert get_project_base(p1) == "image"
    p2 = os.path.join("output", "image", "image_masked.100.json")
    assert get_project_base(p2) == "image"
    p3 = os.path.join("output", "image", "_temp_resume.json")
    assert get_project_base(p3) == "image"

    # 2. Custom input directory path
    p4 = os.path.join("test_img", "image.json")
    assert get_project_base(p4) == "image"
    p5 = os.path.join("test_img", "image.200.json")
    assert get_project_base(p5) == "image"
    p6 = os.path.join("test_img", "image_masked.json")
    assert get_project_base(p6) == "image"

    # 3. Temp resume outside output
    p7 = os.path.join("test_img", "_temp_resume.json")
    assert get_project_base(p7) == "test_img"


@pytest.mark.asyncio
async def test_get_checkpoints_excludes_temp_resume(server, fake_ws):
    import os
    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", return_value=MagicMock()) as mock_open,
        patch("glob.glob", return_value=[]),
    ):
        # Mock json load
        mock_file = MagicMock()
        mock_file.__enter__.return_value = MagicMock()
        mock_open.return_value = mock_file

        with patch(
            "json.load", return_value={"shapes": [{}, {}]}
        ):  # 2 shapes -> 1 layer
            # Request checkpoints with _temp_resume.json path
            # It should not add _temp_resume.json to checkpoints
            input_path = os.path.join("output", "test", "_temp_resume.json")
            await server.handle_message(
                fake_ws,
                json.dumps(
                    {
                        "action": "get_checkpoints",
                        "img_path": input_path,
                    }
                ),
            )

            assert len(fake_ws.sent_messages) == 1
            resp = json.loads(fake_ws.sent_messages[0])
            assert resp["action"] == "checkpoints_list"
            # It should NOT contain _temp_resume.json path
            assert (
                any("_temp_resume.json" in cp["path"] for cp in resp["checkpoints"])
                is False
            )
