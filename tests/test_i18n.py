import json
import os
from unittest.mock import AsyncMock

import pytest

from backend.server import PainterServer


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_language_files_exist():
    lang_dir = os.path.join(get_project_root(), "lang")
    for lang in ["en-us", "zh-tw", "ja-jp"]:
        path = os.path.join(lang_dir, f"{lang}.json")
        assert os.path.exists(path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "header.disable_preview" in data


@pytest.mark.asyncio
async def test_get_lang_websocket():
    server = PainterServer()
    mock_ws = AsyncMock()

    await server.handle_message(
        mock_ws, json.dumps({"action": "get_lang", "lang": "zh-tw"})
    )

    mock_ws.send.assert_called_once()
    call_arg = mock_ws.send.call_args[0][0]
    response = json.loads(call_arg)

    assert response["action"] == "lang_data"
    assert response["data"]["header.disable_preview"] == "關閉預覽"
