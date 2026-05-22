"""Tests for session persistence during /chat/stream (issue #10)."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


async def _empty_stream(*args, **kwargs):
    return
    yield


def _make_response_stream(thread_id: str):
    from langchain_core.messages import AIMessage

    async def _stream(*args, **kwargs):
        for token in ("Hello", " world"):
            yield {
                "event": "on_chat_model_stream",
                "name": "ChatOpenAI",
                "data": {"chunk": AIMessage(content=token)},
            }

    return _stream


def _make_mock_conn():
    cursor = MagicMock()
    cursor.rowcount = 0
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── Cycle 13: stream creates a session record in MySQL ────────────────────────

def test_chat_stream_creates_session_record():
    conn, cursor = _make_mock_conn()

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_connection", return_value=conn):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _empty_stream
        from main import app
        client = TestClient(app)
        client.post("/chat/stream", json={"message": "hi", "customer_id": 1})

    # A session INSERT should have been executed
    all_calls = [str(c) for c in cursor.execute.call_args_list]
    assert any("sessions" in c.lower() for c in all_calls), \
        "Expected an INSERT into sessions table"


# ── Cycle 14: stream inserts human message into session_messages ──────────────

def test_chat_stream_inserts_human_message():
    conn, cursor = _make_mock_conn()

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_connection", return_value=conn):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _empty_stream
        from main import app
        client = TestClient(app)
        client.post("/chat/stream", json={"message": "Where is my order?", "customer_id": 1})

    all_calls = [str(c) for c in cursor.execute.call_args_list]
    assert any("session_messages" in c.lower() and "human" in c.lower() for c in all_calls), \
        "Expected INSERT of human message into session_messages"


# ── Cycle 15: stream inserts AI response into session_messages ────────────────

def test_chat_stream_inserts_ai_response():
    conn, cursor = _make_mock_conn()

    with patch("routes.chat._get_async_graph", new=AsyncMock()) as get_async_graph, \
         patch("routes.chat.get_connection", return_value=conn):
        mock_graph = get_async_graph.return_value
        mock_graph.astream_events = _make_response_stream("t1")
        from main import app
        client = TestClient(app)
        client.post("/chat/stream", json={"message": "hi", "customer_id": 1})

    all_calls = [str(c) for c in cursor.execute.call_args_list]
    assert any("session_messages" in c.lower() and "ai" in c.lower() for c in all_calls), \
        "Expected INSERT of AI response into session_messages"
