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


# ── Cycle 10: POST /customers creates a customer ──────────────────────────────

def test_post_customers_creates_customer():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [{"next_id": 3}, {"customer_id": 3, "name": "Alice", "email": "alice@example.com"}]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.post("/customers", json={"name": "Alice", "email": "alice@example.com"})

    assert resp.status_code == 201
    assert resp.json() == {"customer_id": 3, "name": "Alice", "email": "alice@example.com"}
    conn.commit.assert_called_once()


def test_post_customers_invalid_payload_returns_422():
    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/customers", json={"name": "Alice"})

    assert resp.status_code == 422


# ── Cycle 11: PUT /customers/{id} updates a customer ──────────────────────────

def test_put_customers_updates_customer():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = {"customer_id": 1, "name": "Updated", "email": "updated@example.com"}
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put("/customers/1", json={"name": "Updated", "email": "updated@example.com"})

    assert resp.status_code == 200
    assert resp.json() == {"customer_id": 1, "name": "Updated", "email": "updated@example.com"}
    conn.commit.assert_called_once()


def test_put_customers_not_found_returns_404():
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.put("/customers/999", json={"name": "Updated"})

    assert resp.status_code == 404


def test_put_customers_same_values_still_returns_200():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"customer_id": 1},
        {"customer_id": 1, "name": "Alice", "email": "alice@example.com"},
    ]
    cursor.rowcount = 0
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put("/customers/1", json={"name": "Alice"})

    assert resp.status_code == 200
    assert resp.json()["customer_id"] == 1


# ── Cycle 12: DELETE /customers/{id} removes dependent rows and customer ──────

def test_delete_customers_deletes_dependents_then_customer():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = {"customer_id": 1, "name": "Ahmad", "email": "a@example.com"}
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.delete("/customers/1")

    assert resp.status_code == 200
    assert resp.json() == {"deleted": True, "customer_id": 1}
    executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
    assert any("delete from complaints where customer_id = %s" in sql.lower() for sql in executed_sql)
    assert any("delete from orders where customer_id = %s" in sql.lower() for sql in executed_sql)
    assert any("delete from customer_memory where customer_id = %s" in sql.lower() for sql in executed_sql)
    assert any("delete from sessions where customer_id = %s" in sql.lower() for sql in executed_sql)
    assert any("delete from customers where customer_id = %s" in sql.lower() for sql in executed_sql)
    conn.commit.assert_called_once()


def test_delete_customers_not_found_returns_404():
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.delete("/customers/999")

    assert resp.status_code == 404


# ── Cycle 13: POST /orders creates an order ───────────────────────────────────

def test_post_orders_creates_order():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"next_id": 103},
        {
            "order_id": 103,
            "customer_id": 1,
            "product_name": "Desk Lamp",
            "status": "pending",
        },
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/orders",
            json={"customer_id": 1, "product_name": "Desk Lamp", "status": "pending"},
        )

    assert resp.status_code == 201
    assert resp.json() == {
        "order_id": 103,
        "customer_id": 1,
        "product_name": "Desk Lamp",
        "status": "pending",
    }
    conn.commit.assert_called_once()


def test_post_orders_invalid_payload_returns_422():
    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/orders", json={"customer_id": 1, "status": "pending"})

    assert resp.status_code == 422


# ── Cycle 14: PUT /orders/{id} updates order fields ───────────────────────────

def test_put_orders_updates_order():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = {
        "order_id": 101,
        "customer_id": 1,
        "product_name": "Desk Lamp Pro",
        "status": "processing",
    }
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put("/orders/101", json={"product_name": "Desk Lamp Pro", "status": "processing"})

    assert resp.status_code == 200
    assert resp.json()["order_id"] == 101
    assert resp.json()["product_name"] == "Desk Lamp Pro"
    conn.commit.assert_called_once()


def test_put_orders_not_found_returns_404():
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.put("/orders/999", json={"status": "delivered"})

    assert resp.status_code == 404


def test_put_orders_same_values_still_returns_200():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"order_id": 101},
        {"order_id": 101, "customer_id": 1, "product_name": "Desk Lamp", "status": "pending"},
    ]
    cursor.rowcount = 0
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put("/orders/101", json={"status": "pending"})

    assert resp.status_code == 200
    assert resp.json()["order_id"] == 101


# ── Cycle 15: DELETE /orders/{id} removes dependent complaints first ──────────

def test_delete_orders_deletes_complaints_then_order():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = {"order_id": 101}
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.delete("/orders/101")

    assert resp.status_code == 200
    assert resp.json() == {"deleted": True, "order_id": 101}
    executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
    assert any("delete from complaints where order_id = %s" in sql.lower() for sql in executed_sql)
    assert any("delete from orders where order_id = %s" in sql.lower() for sql in executed_sql)
    conn.commit.assert_called_once()


def test_delete_orders_not_found_returns_404():
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.delete("/orders/999")

    assert resp.status_code == 404


# ── Cycle 16: POST /complaints creates a complaint ────────────────────────────

def test_post_complaints_creates_complaint():
    cursor = MagicMock()
    cursor.lastrowid = 12
    cursor.fetchone.return_value = {
        "complaint_id": 12,
        "customer_id": 1,
        "order_id": 101,
        "issue": "Damaged box",
        "status": "open",
    }
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/complaints",
            json={
                "customer_id": 1,
                "order_id": 101,
                "issue": "Damaged box",
                "status": "open",
            },
        )

    assert resp.status_code == 201
    assert resp.json()["complaint_id"] == 12
    assert resp.json()["issue"] == "Damaged box"
    conn.commit.assert_called_once()


def test_post_complaints_invalid_payload_returns_422():
    from main import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/complaints", json={"customer_id": 1, "order_id": 101, "status": "open"})

    assert resp.status_code == 422


# ── Cycle 17: PUT /complaints/{id} updates complaint fields ───────────────────

def test_put_complaints_updates_complaint():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = {
        "complaint_id": 1,
        "customer_id": 1,
        "order_id": 101,
        "issue": "Updated issue",
        "status": "resolved",
    }
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put("/complaints/1", json={"issue": "Updated issue", "status": "resolved"})

    assert resp.status_code == 200
    assert resp.json()["complaint_id"] == 1
    assert resp.json()["status"] == "resolved"
    conn.commit.assert_called_once()


def test_put_complaints_not_found_returns_404():
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.put("/complaints/999", json={"status": "closed"})

    assert resp.status_code == 404


def test_put_complaints_same_values_still_returns_200():
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        {"complaint_id": 1},
        {"complaint_id": 1, "customer_id": 1, "order_id": 101, "issue": "Damaged box", "status": "open"},
    ]
    cursor.rowcount = 0
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.put("/complaints/1", json={"status": "open"})

    assert resp.status_code == 200
    assert resp.json()["complaint_id"] == 1


# ── Cycle 18: DELETE /complaints/{id} deletes complaint ───────────────────────

def test_delete_complaints_deletes_complaint():
    cursor = MagicMock()
    cursor.rowcount = 1
    cursor.fetchone.return_value = {"complaint_id": 1}
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app)
        resp = client.delete("/complaints/1")

    assert resp.status_code == 200
    assert resp.json() == {"deleted": True, "complaint_id": 1}
    conn.commit.assert_called_once()


def test_delete_complaints_not_found_returns_404():
    cursor = MagicMock()
    cursor.rowcount = 0
    cursor.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cursor

    with patch("routes.data.get_connection", return_value=conn):
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.delete("/complaints/999")

    assert resp.status_code == 404
