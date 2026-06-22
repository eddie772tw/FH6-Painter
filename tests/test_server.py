import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock
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
    with patch('tools.fh6_import_layer_table.run_importer', return_value=0) as mock_run:
        # Inject it into sys.modules so the dynamic import in server.py finds our mock
        import sys
        if 'tools.fh6_import_layer_table' not in sys.modules:
            mock_module = MagicMock()
            mock_module.run_importer = mock_run
            sys.modules['tools.fh6_import_layer_table'] = mock_module
        else:
            sys.modules['tools.fh6_import_layer_table'].run_importer = mock_run

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
        
    with patch.object(server, 'run_generator_blocking', side_effect=fake_run):
        await server.start_generation({"img_path": "test.png", "layers": 10})
        
        assert len(fake_ws.sent_messages) >= 2
        started = json.loads(fake_ws.sent_messages[0])
        assert started["action"] == "generation_status"
        assert started["status"] == "started"
        
        completed = json.loads(fake_ws.sent_messages[-1])
        assert completed["action"] == "generation_status"
        assert completed["status"] == "completed"
