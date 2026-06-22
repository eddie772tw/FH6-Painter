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
    with (
        patch("os.path.exists", return_value=True),
        patch(
            "glob.glob", return_value=["D:\\FH6-Painter\\output\\test\\test_500.json"]
        ),
    ):
        await server.handle_message(
            fake_ws,
            json.dumps({"action": "get_checkpoints", "img_path": "D:\\test\\test.png"}),
        )
        assert len(fake_ws.sent_messages) == 1
        resp = json.loads(fake_ws.sent_messages[0])
        assert resp["action"] == "checkpoints_list"
        assert len(resp["checkpoints"]) == 1
        assert resp["checkpoints"][0]["layer"] == 500
