"""Tests for memory management endpoints (issue #10): GET/PUT/DELETE /memory/{customer_id}."""

from unittest.mock import MagicMock, call, patch

import pytest
from fastapi.testclient import TestClient


def _make_conn(rows=None):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows or []
    cursor.fetchone.return_value = rows[0] if rows else None
    cursor.rowcount = 1
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── Cycle 6: GET /memory/{customer_id} returns KV list ────────────────────────

def test_get_memory_returns_kv_list():
    rows = [
        {"key": "late_delivery_pattern", "value": "repeated late", "created_at": "2026-01-01"},
        {"key": "complaint_count", "value": "2", "created_at": "2026-01-01"},
    ]
    conn, _ = _make_conn(rows)

    with patch("routes.memory.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/memory/1")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["key"] == "late_delivery_pattern"


# ── Cycle 7: PUT /memory/{customer_id} upserts entries ────────────────────────

def test_put_memory_upserts_entries():
    conn, cursor = _make_conn()

    with patch("routes.memory.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put(
            "/memory/1",
            json=[
                {"key": "preferred_channel", "value": "email"},
                {"key": "vip_status", "value": "true"},
            ],
        )

    assert resp.status_code == 200
    assert resp.json()["updated"] == 2
    assert cursor.execute.call_count == 2
    conn.commit.assert_called_once()


# ── Cycle 8: DELETE /memory/{customer_id}/{key} deletes entry ─────────────────

def test_delete_memory_entry_success():
    conn, cursor = _make_conn()
    cursor.rowcount = 1

    with patch("routes.memory.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.delete("/memory/1/complaint_count")

    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    conn.commit.assert_called_once()


# ── Cycle 9: DELETE /memory/{customer_id}/{key} returns 404 when not found ────

def test_delete_memory_entry_not_found():
    conn, cursor = _make_conn()
    cursor.rowcount = 0

    with patch("routes.memory.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.delete("/memory/1/nonexistent_key")

    assert resp.status_code == 404
