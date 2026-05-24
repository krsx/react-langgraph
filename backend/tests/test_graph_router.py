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


# ── Cycle 4: sync router composes refund_email graph with MCP tools ──────────

def test_get_graph_refund_email_includes_filtered_mcp_tools(monkeypatch):
    import importlib
    from langchain_core.tools import tool
    import graph.refund_email.graph as refund_graph

    @tool
    def search_gmail(query: str) -> str:
        """Search Gmail messages."""
        return "[]"

    from graph.mcp_client import mcp_manager

    monkeypatch.setattr(mcp_manager, "_tools", [search_gmail], raising=False)

    captured: dict = {}
    original_compile = refund_graph.compile_graph

    def capturing_compile(tools, checkpointer):
        captured["tools"] = list(tools)
        return original_compile(tools, checkpointer)

    monkeypatch.setattr(refund_graph, "compile_graph", capturing_compile)

    router = importlib.import_module("graph.router")
    router.get_graph("refund_email")

    tool_names = [tool.name for tool in captured["tools"]]
    assert "search_gmail" in tool_names


# ── Cycle 5: sync router composes calendar graph with CLI + MCP tools ───────

def test_get_graph_calendar_includes_cli_and_filtered_mcp_tools(monkeypatch):
    import importlib
    from langchain_core.tools import tool
    import graph.calendar.graph as calendar_graph

    @tool
    def create_event(summary: str) -> str:
        """Create a calendar event."""
        return "ok"

    from graph.mcp_client import mcp_manager

    monkeypatch.setattr(mcp_manager, "_tools", [create_event], raising=False)

    captured: dict = {}
    original_compile = calendar_graph.compile_graph

    def capturing_compile(tools, checkpointer):
        captured["tools"] = list(tools)
        return original_compile(tools, checkpointer)

    monkeypatch.setattr(calendar_graph, "compile_graph", capturing_compile)

    router = importlib.import_module("graph.router")
    router.get_graph("calendar")

    tool_names = [tool.name for tool in captured["tools"]]
    assert "today_events" in tool_names
    assert "create_event" in tool_names
