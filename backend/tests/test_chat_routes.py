"""Tests for POST /chat/stream SSE endpoint (issue #9)."""

import asyncio
import importlib
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_sse(text: str) -> list[dict]:
    """Parse raw SSE text into list of {event, data} dicts."""
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
    """Async generator that yields nothing."""
    return
    yield  # noqa: unreachable — makes this an async generator


def _make_full_stream(thread_id: str):
    """Return an async generator simulating all 8 node events + token stream."""
    from langchain_core.messages import AIMessage

    async def _stream(*args, **kwargs):
        yield {
            "event": "on_chain_end",
            "name": "memory_loader",
            "data": {"output": {"memory_context": [{"type": "memory", "key": "pref", "value": "fast"}]}},
        }
        yield {"event": "on_chain_start", "name": "planner", "data": {}}
        # Simulate a tool-call planner round
        yield {
            "event": "on_chain_end",
            "name": "planner",
            "data": {
                "output": {
                    "messages": [
                        AIMessage(
                            content="Checking order",
                            tool_calls=[{"name": "order_lookup", "args": {"order_id": 1}, "id": "tc1"}],
                        )
                    ]
                }
            },
        }
        yield {"event": "on_chain_start", "name": "tools", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "tools",
            "data": {"output": {"messages": []}},
        }
        # Second planner round — final (no tool calls)
        yield {"event": "on_chain_start", "name": "planner", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "planner",
            "data": {
                "output": {
                    "messages": [AIMessage(content="Your order is on the way.")]
                }
            },
        }
        # Token stream
        for token in ("Your", " order", " is", " on", " the", " way."):
            yield {
                "event": "on_chat_model_stream",
                "name": "ChatOpenAI",
                "data": {"chunk": AIMessage(content=token)},
            }
        yield {
            "event": "on_chain_end",
            "name": "verifier",
            "data": {
                "output": {
                    "verification": {"valid": True, "checks": ["all checks passed"], "override_message": None}
                }
            },
        }
        yield {
            "event": "on_chain_end",
            "name": "memory_update",
            "data": {"output": {}},
        }

    return _stream


def _make_single_tool_result_stream():
    from langchain_core.messages import ToolMessage

    async def _stream(*args, **kwargs):
        yield {"event": "on_chain_start", "name": "tools", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "tools",
            "data": {
                "output": {
                    "messages": [
                        ToolMessage(
                            content='{"order_id": 12345, "status": "pending"}',
                            tool_call_id="call_1",
                            name="order_lookup",
                        )
                    ]
                }
            },
        }

    return _stream


def _make_multi_tool_result_stream():
    from langchain_core.messages import ToolMessage

    async def _stream(*args, **kwargs):
        yield {"event": "on_chain_start", "name": "tools", "data": {}}
        yield {
            "event": "on_chain_end",
            "name": "tools",
            "data": {
                "output": {
                    "messages": [
                        ToolMessage(
                            content='{"order_id": 12345, "status": "pending"}',
                            tool_call_id="call_1",
                            name="order_lookup",
                        ),
                        ToolMessage(
                            content='{"customer_id": 1, "vip": true}',
                            tool_call_id="call_2",
                            name="customer_profile",
                        ),
                    ]
                }
            },
        }

    return _stream


def _make_memory_updated_stream():
    async def _stream(*args, **kwargs):
        yield {
            "event": "on_chain_end",
            "name": "memory_update",
            "data": {
                "output": {
                    "key": "last_interaction_summary",
                    "value": "User asked for refund details.",
                }
            },
        }

    return _stream


# ── Cycle 1: Endpoint returns SSE content-type ───────────────────────────────

def test_chat_stream_returns_sse_content_type():
    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _empty_stream
        from main import app

        client = TestClient(app)
        resp = client.post("/chat/stream", json={"message": "hello", "customer_id": 1})

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")


# ── Cycle 2: CORS allows localhost:5173 ──────────────────────────────────────

def test_cors_allows_localhost_5173():
    from main import app

    client = TestClient(app)
    resp = client.options(
        "/chat/stream",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ── Cycle 3: New session generates UUID thread_id in first event ─────────────

def test_new_session_generates_uuid_thread_id_in_first_event():
    import re

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _empty_stream
        from main import app

        client = TestClient(app)
        resp = client.post("/chat/stream", json={"message": "hello", "customer_id": 1})

    events = parse_sse(resp.text)
    assert events, "expected at least one SSE event"

    first_data = events[0]["data"]
    thread_id = first_data.get("thread_id", "")
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    assert uuid_pattern.match(thread_id), f"thread_id '{thread_id}' is not a valid UUID"


# ── Cycle 4: Existing session echoes provided thread_id ──────────────────────

def test_existing_session_echoes_thread_id():
    provided_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _empty_stream
        from main import app

        client = TestClient(app)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "customer_id": 1, "thread_id": provided_id},
        )

    events = parse_sse(resp.text)
    assert events, "expected at least one SSE event"
    assert events[0]["data"]["thread_id"] == provided_id


# ── Cycle 5: All 8 SSE event types fire at correct graph node transitions ─────

def test_all_sse_event_types_emitted_on_full_graph_run():
    fixed_thread_id = "11111111-2222-3333-4444-555555555555"

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _make_full_stream(fixed_thread_id)
        from main import app

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/chat/stream",
            json={
                "message": "Where is my order?",
                "customer_id": 1,
                "thread_id": fixed_thread_id,
            },
        )

    assert resp.status_code == 200
    events = parse_sse(resp.text)
    event_types = {e["event"] for e in events}

    required = {
        "memory_loaded",
        "planner_start",
        "planner_result",
        "tool_start",
        "tool_result",
        "verifier_result",
        "memory_updated",
        "response_token",
        "response_end",
    }
    missing = required - event_types
    assert not missing, f"Missing SSE event types: {missing}"


# ── Cycle 6: SSE event data shapes are correct ───────────────────────────────

def test_sse_event_data_shapes():
    fixed_thread_id = "11111111-2222-3333-4444-555555555555"

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _make_full_stream(fixed_thread_id)
        from main import app

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/chat/stream",
            json={
                "message": "Where is my order?",
                "customer_id": 1,
                "thread_id": fixed_thread_id,
            },
        )

    events = parse_sse(resp.text)
    by_type = {}
    for e in events:
        by_type.setdefault(e["event"], []).append(e["data"])

    # memory_loaded contains memory_context list
    assert "memory_context" in by_type["memory_loaded"][0]

    # planner_result contains content + tool_calls
    pr = by_type["planner_result"][0]
    assert "content" in pr
    assert "tool_calls" in pr

    # verifier_result contains valid + checks
    vr = by_type["verifier_result"][0]
    assert "valid" in vr
    assert "checks" in vr

    # response_token has token key
    rt = by_type["response_token"][0]
    assert "token" in rt

    # response_end has full response text
    re_ev = by_type["response_end"][0]
    assert "response" in re_ev
    assert re_ev["response"] == "Your order is on the way."


def test_tool_result_event_includes_tool_name_and_structured_json_results():
    fixed_thread_id = "11111111-2222-3333-4444-555555555555"

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _make_single_tool_result_stream()
        from main import app

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/chat/stream",
            json={
                "message": "Where is my order?",
                "customer_id": 1,
                "thread_id": fixed_thread_id,
            },
        )

    events = parse_sse(resp.text)
    tool_result = next(e["data"] for e in events if e["event"] == "tool_result")

    assert tool_result["thread_id"] == fixed_thread_id
    assert tool_result["tool_name"] == "order_lookup"
    assert tool_result["results"] == {"order_id": 12345, "status": "pending"}
    assert not isinstance(tool_result["results"], str)


def test_multi_tool_turn_emits_one_tool_result_event_per_tool_message():
    fixed_thread_id = "11111111-2222-3333-4444-555555555555"

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _make_multi_tool_result_stream()
        from main import app

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/chat/stream",
            json={
                "message": "Check order and profile",
                "customer_id": 1,
                "thread_id": fixed_thread_id,
            },
        )

    events = parse_sse(resp.text)
    tool_results = [e["data"] for e in events if e["event"] == "tool_result"]

    assert len(tool_results) == 2
    assert tool_results == [
        {
            "thread_id": fixed_thread_id,
            "tool_name": "order_lookup",
            "results": {"order_id": 12345, "status": "pending"},
        },
        {
            "thread_id": fixed_thread_id,
            "tool_name": "customer_profile",
            "results": {"customer_id": 1, "vip": True},
        },
    ]


def test_memory_updated_event_includes_written_key_and_value():
    fixed_thread_id = "11111111-2222-3333-4444-555555555555"

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _make_memory_updated_stream()
        from main import app

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.post(
            "/chat/stream",
            json={
                "message": "Summarize this turn",
                "customer_id": 1,
                "thread_id": fixed_thread_id,
            },
        )

    events = parse_sse(resp.text)
    memory_updated = next(e["data"] for e in events if e["event"] == "memory_updated")

    assert memory_updated == {
        "thread_id": fixed_thread_id,
        "key": "last_interaction_summary",
        "value": "User asked for refund details.",
    }


# ── Cycle 7: Graph error yields error SSE event ───────────────────────────────

def test_graph_error_yields_error_sse_event():
    async def _exploding_stream(*args, **kwargs):
        raise RuntimeError("graph exploded")
        yield  # noqa: unreachable

    with patch("routes.chat.get_async_graph", new=AsyncMock()) as get_async_graph:
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _exploding_stream
        from main import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/chat/stream", json={"message": "hello", "customer_id": 1})

    events = parse_sse(resp.text)
    event_types = {e["event"] for e in events}
    assert "error" in event_types

    error_data = next(e["data"] for e in events if e["event"] == "error")
    assert "error" in error_data
    assert "graph exploded" in error_data["error"]


def test_chat_stream_real_async_graph_path_avoids_sync_sqlite_error(monkeypatch):
    graph_module = importlib.import_module("graph.customer_service.graph")

    class _Conn:
        def cursor(self, *args, **kwargs):
            cursor = MagicMock()
            cursor.rowcount = 0
            return cursor

        def commit(self):
            pass

        def close(self):
            pass

    from langchain_core.messages import AIMessage

    asyncio.run(graph_module.close_async_graph())
    monkeypatch.setattr(graph_module, "memory_loader", lambda state: {"memory_context": []})
    monkeypatch.setattr(
        graph_module,
        "planner",
        lambda state, config: {"messages": [AIMessage(content="stub route response")]},
    )
    monkeypatch.setattr(
        graph_module,
        "verifier",
        lambda state: {
            "verification": {"valid": True, "checks": [], "override_message": None},
            "tool_results": [],
        },
    )
    monkeypatch.setattr(graph_module, "memory_update", lambda state: {})

    try:
        with patch("routes.chat.get_connection", return_value=_Conn()):
            from main import app

            client = TestClient(app)
            resp = client.post("/chat/stream", json={"message": "hello", "customer_id": 1})

        assert resp.status_code == 200
        assert "The SqliteSaver does not support async methods" not in resp.text

        async_graph = asyncio.run(graph_module.get_async_graph())
        assert type(async_graph.checkpointer).__name__ == "AsyncSqliteSaver"
    finally:
        asyncio.run(graph_module.close_async_graph())
