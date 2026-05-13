"""Tests that chat /stream resolves provider/model from server config (issue #11)."""
import json
import pytest
from unittest.mock import patch, AsyncMock


def parse_sse(text: str) -> list[dict]:
    events = []
    current: dict = {}
    for line in text.splitlines():
        if line.startswith("event:"):
            current["event"] = line[len("event:"):].strip()
        elif line.startswith("data:"):
            raw = line[len("data:"):].strip()
            try:
                current["data"] = json.loads(raw)
            except json.JSONDecodeError:
                current["data"] = raw
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


async def _empty_stream(*args, **kwargs):
    return
    yield


# ── Cycle 1: provider is forwarded and model is resolved from env ─────────────

def test_provider_uses_env_default_model_in_graph_configurable():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    cfg = type(
        "Cfg",
        (),
        {
            "DEFAULT_MODEL": "google/gemini-2.5-flash",
            "OLLAMA_DEFAULT_MODEL": "qwen3.5:9b",
        },
    )()

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_config", return_value=cfg):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _capturing_stream
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"message": "hi", "customer_id": 1, "provider": "ollama", "model": "llama3"},
        )

    assert captured_configs, "graph was never called"
    cfg = captured_configs[0]
    assert cfg["configurable"]["provider"] == "ollama"
    assert cfg["configurable"]["model"] == "qwen3.5:9b"


def test_no_provider_uses_openrouter_env_default_model():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    cfg = type(
        "Cfg",
        (),
        {
            "DEFAULT_MODEL": "google/gemini-2.5-flash",
            "OLLAMA_DEFAULT_MODEL": "qwen3.5:9b",
        },
    )()

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_config", return_value=cfg):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _capturing_stream
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"message": "hi", "customer_id": 1},
        )

    cfg = captured_configs[0]
    assert cfg["configurable"].get("provider") == "openrouter"
    assert cfg["configurable"].get("model") == "google/gemini-2.5-flash"
