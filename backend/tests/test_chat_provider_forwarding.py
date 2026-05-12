"""Tests that chat /stream forwards provider/model to graph configurable (issue #11)."""
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


# ── Cycle 1: provider and model are forwarded into configurable ───────────────

def test_provider_forwarded_to_graph_configurable():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    with patch("routes.chat.graph") as mock_graph:
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


def test_no_provider_leaves_configurable_none():
    captured_configs = []

    async def _capturing_stream(input_state, config, **kwargs):
        captured_configs.append(config)
        return
        yield

    with patch("routes.chat.graph") as mock_graph:
        mock_graph.astream_events = _capturing_stream
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        client.post(
            "/chat/stream",
            json={"message": "hi", "customer_id": 1},
        )

    cfg = captured_configs[0]
    assert cfg["configurable"].get("provider") is None
    assert cfg["configurable"].get("model") is None
