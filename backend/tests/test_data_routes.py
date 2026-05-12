"""Tests for data exploration endpoints (issue #10): /customers, /orders, /complaints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_conn(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# ── Cycle 1: GET /customers returns list ─────────────────────────────────────

def test_get_customers_returns_list():
    rows = [{"customer_id": 1, "name": "Ahmad Rifqi", "email": "c1@example.com", "created_at": "2026-01-01"}]
    conn, _ = _make_conn(rows)

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/customers")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert data[0]["customer_id"] == 1
    assert data[0]["name"] == "Ahmad Rifqi"


# ── Cycle 2: GET /orders returns all orders ───────────────────────────────────

def test_get_orders_returns_all():
    rows = [
        {"order_id": 101, "customer_id": 1, "product_name": "Widget", "status": "pending"},
        {"order_id": 102, "customer_id": 2, "product_name": "Gadget", "status": "delivered"},
    ]
    conn, _ = _make_conn(rows)

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/orders")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


# ── Cycle 3: GET /orders?customer_id=1 filters ───────────────────────────────

def test_get_orders_filtered_by_customer():
    rows = [{"order_id": 101, "customer_id": 1, "product_name": "Widget", "status": "pending"}]
    conn, cursor = _make_conn(rows)

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/orders?customer_id=1")

    assert resp.status_code == 200
    # verify the query used the customer_id param
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    assert "customer_id" in sql.lower()
    assert 1 in call_args[0][1]


# ── Cycle 4: GET /complaints returns all complaints ───────────────────────────

def test_get_complaints_returns_all():
    rows = [{"complaint_id": 1, "customer_id": 1, "issue": "Late delivery", "status": "resolved"}]
    conn, _ = _make_conn(rows)

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/complaints")

    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["complaint_id"] == 1


# ── Cycle 5: GET /complaints?customer_id=1 filters ────────────────────────────

def test_get_complaints_filtered_by_customer():
    rows = [{"complaint_id": 1, "customer_id": 1, "issue": "Late delivery", "status": "resolved"}]
    conn, cursor = _make_conn(rows)

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.get("/complaints?customer_id=1")

    assert resp.status_code == 200
    call_args = cursor.execute.call_args
    sql = call_args[0][0]
    assert "customer_id" in sql.lower()
    assert 1 in call_args[0][1]
