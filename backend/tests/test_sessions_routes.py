"""Tests for session history endpoints (issue #10): GET /sessions, GET /sessions/{id}."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_conn_multi(fetchall_rows=None, fetchone_rows=None):
    """Build a mock where fetchone returns values from a list on successive calls."""
    cursor = MagicMock()
    cursor.fetchall.return_value = fetchall_rows or []
    if fetchone_rows is not None:
        cursor.fetchone.side_effect = fetchone_rows
    else:
        cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── Cycle 10: GET /sessions returns list with metadata ────────────────────────

def test_get_sessions_returns_list():
    rows = [
        {
            "thread_id": "abc-123",
            "customer_id": 1,
            "created_at": "2026-05-01 10:00:00",
            "first_message": "Where is my order?",
        }
    ]
    conn, _ = _make_conn_multi(fetchall_rows=rows)

    with patch("routes.sessions.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/sessions")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["thread_id"] == "abc-123"
    assert "first_message" in data[0]


# ── Cycle 11: GET /sessions/{id} returns ordered messages ─────────────────────

def test_get_session_messages_returns_ordered_list():
    session_row = {"thread_id": "abc-123"}
    messages = [
        {"message_id": 1, "role": "human", "content": "Hello", "created_at": "2026-05-01 10:00:00"},
        {"message_id": 2, "role": "ai", "content": "Hi there!", "created_at": "2026-05-01 10:00:01"},
    ]
    conn, cursor = _make_conn_multi(
        fetchall_rows=messages,
        fetchone_rows=[session_row],
    )

    with patch("routes.sessions.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/sessions/abc-123")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["role"] == "human"
    assert data[1]["role"] == "ai"


# ── Cycle 12: GET /sessions/{id} returns 404 for unknown session ──────────────

def test_get_session_not_found_returns_404():
    conn, cursor = _make_conn_multi(fetchone_rows=[None])

    with patch("routes.sessions.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/sessions/nonexistent-id")

    assert resp.status_code == 404
