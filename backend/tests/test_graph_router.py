import pytest
import sys


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("graph"):
            sys.modules.pop(mod, None)


# ── Cycle 1: get_graph dispatches customer_service ───────────────────────────

def test_get_graph_customer_service_returns_compiled_graph():
    from graph.router import get_graph
    g = get_graph("customer_service")
    assert g is not None


# ── Cycle 2: unknown agent_type raises ValueError ─────────────────────────────

def test_get_graph_unknown_type_raises_value_error():
    from graph.router import get_graph
    with pytest.raises(ValueError, match="unknown_agent"):
        get_graph("unknown_agent")


# ── Cycle 3: chat route uses router, not hardcoded customer_service import ────

def test_chat_route_uses_graph_router(monkeypatch):
    import importlib
    from unittest.mock import AsyncMock, MagicMock, patch

    dispatched_types = []

    async def fake_router(agent_type: str):
        dispatched_types.append(agent_type)
        mock_graph = MagicMock()
        mock_graph.astream_events = MagicMock(return_value=_empty_async_gen())
        return mock_graph

    async def _empty_async_gen():
        return
        yield

    chat_module = importlib.import_module("routes.chat")
    monkeypatch.setattr(chat_module, "_get_async_graph", fake_router)

    from fastapi.testclient import TestClient
    from main import app

    with patch("routes.chat._persist_session_start"), patch("routes.chat._persist_ai_message"):
        client = TestClient(app, raise_server_exceptions=False)
        client.post("/chat/stream", json={
            "message": "hello",
            "customer_id": 1,
            "agent_type": "customer_service",
        })

    assert "customer_service" in dispatched_types
