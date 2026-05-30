"""Tests that chat /stream forwards provider/model from the request to the graph configurable."""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def stub_db(monkeypatch):
    """Prevent _persist_session_start from touching MySQL in unit tests."""
    mock_conn = MagicMock()
    monkeypatch.setattr("routes.chat.get_connection", lambda: mock_conn)


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


def _make_cfg():
    return type(
        "Cfg",
        (),
        {
            "DEFAULT_MODEL": "google/gemini-2.5-flash",
            "OLLAMA_DEFAULT_MODEL": "qwen3.5:9b",
        },
    )()


# ── Cycle 1: request model is forwarded to graph configurable ────────────────

def test_request_model_is_forwarded_to_graph_configurable():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_config", return_value=_make_cfg()):
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
    assert cfg["configurable"]["model"] == "llama3"


# ── Cycle 2: missing model falls back to env default for ollama ──────────────

def test_no_model_uses_ollama_env_default():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_config", return_value=_make_cfg()):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _capturing_stream
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"message": "hi", "customer_id": 1, "provider": "ollama"},
        )

    assert captured_configs, "graph was never called"
    cfg = captured_configs[0]
    assert cfg["configurable"]["provider"] == "ollama"
    assert cfg["configurable"]["model"] == "qwen3.5:9b"


# ── Cycle 3: missing provider + model uses openrouter env default ────────────

def test_no_provider_uses_openrouter_env_default_model():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_config", return_value=_make_cfg()):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _capturing_stream
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"message": "hi", "customer_id": 1},
        )

    assert captured_configs, "graph was never called"
    cfg = captured_configs[0]
    assert cfg["configurable"].get("provider") == "openrouter"
    assert cfg["configurable"].get("model") == "google/gemini-2.5-flash"


# ── Cycle 4: explicit openrouter model is forwarded ──────────────────────────

def test_explicit_openrouter_model_is_forwarded():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_config", return_value=_make_cfg()):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _capturing_stream
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"message": "hi", "customer_id": 1, "provider": "openrouter", "model": "anthropic/claude-3-5-sonnet"},
        )

    assert captured_configs, "graph was never called"
    cfg = captured_configs[0]
    assert cfg["configurable"]["provider"] == "openrouter"
    assert cfg["configurable"]["model"] == "anthropic/claude-3-5-sonnet"
