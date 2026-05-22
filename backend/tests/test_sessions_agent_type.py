"""Tests for sessions API returning agent_type field (issue #27)."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _make_conn(fetchall_rows=None, fetchone_rows=None):
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall_rows or []
    if fetchone_rows is not None:
        cursor.fetchone.side_effect = fetchone_rows
    else:
        cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


# ── Cycle 1: Sessions SQL selects agent_type column ──────────────────────────

def test_sessions_list_sql_selects_agent_type():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = _make_conn(fetchall_rows=[])

    with patch("routes.sessions.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        client.get("/sessions")

    sql_called = conn.cursor.return_value.execute.call_args[0][0]
    assert "agent_type" in sql_called.lower()


# ── Cycle 2: Sessions persist stores agent_type ───────────────────────────────

def test_persist_session_start_stores_agent_type():
    from routes.chat import _persist_session_start

    cursor = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.chat.get_connection", return_value=conn):
        _persist_session_start("thread-1", 1, "hello", "customer_service")

    calls = [str(call) for call in cursor.execute.call_args_list]
    assert any("agent_type" in c for c in calls)


# ── Cycle 4: Sessions list includes agent_type field ─────────────────────────

def test_get_sessions_list_includes_agent_type():
    rows = [
        {
            "thread_id": "abc-123",
            "customer_id": 1,
            "agent_type": "customer_service",
            "created_at": "2026-05-01 10:00:00",
            "first_message": "Where is my order?",
        }
    ]
    conn = _make_conn(fetchall_rows=rows)

    with patch("routes.sessions.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/sessions")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["agent_type"] == "customer_service"


# ── Cycle 5: Sessions list nullable customer_id for workspace agents ───────────

def test_get_sessions_list_supports_null_customer_id():
    rows = [
        {
            "thread_id": "xyz-456",
            "customer_id": None,
            "agent_type": "refund_email",
            "created_at": "2026-05-01 11:00:00",
            "first_message": "Draft a refund email",
        }
    ]
    conn = _make_conn(fetchall_rows=rows)

    with patch("routes.sessions.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/sessions")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["customer_id"] is None
    assert data[0]["agent_type"] == "refund_email"
