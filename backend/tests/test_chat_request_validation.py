"""Tests for ChatRequest agent_type field and Pydantic validator (issue #27)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


async def _empty_stream(*args, **kwargs):
    return
    yield


# ── Cycle 1: agent_type defaults to "customer_service" ───────────────────────

def test_chat_request_agent_type_defaults_to_customer_service():
    from routes.chat import ChatRequest

    req = ChatRequest(message="hello", customer_id=1)
    assert req.agent_type == "customer_service"


# ── Cycle 2: customer_service agent requires customer_id ──────────────────────

def test_customer_service_without_customer_id_returns_422():
    with patch("routes.chat._get_async_graph", new=AsyncMock()) as mock:
        mock.return_value.astream_events = _empty_stream
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "agent_type": "customer_service"},
        )

    assert resp.status_code == 422


def test_customer_service_with_customer_id_is_accepted():
    with patch("routes.chat._get_async_graph", new=AsyncMock()) as mock:
        mock.return_value.astream_events = _empty_stream
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "customer_id": 1, "agent_type": "customer_service"},
        )

    assert resp.status_code == 200


# ── Cycle 3: workspace agents reject customer_id ──────────────────────────────

def test_refund_email_agent_with_customer_id_returns_422():
    with patch("routes.chat._get_async_graph", new=AsyncMock()) as mock:
        mock.return_value.astream_events = _empty_stream
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "customer_id": 1, "agent_type": "refund_email"},
        )

    assert resp.status_code == 422


def test_calendar_agent_with_customer_id_returns_422():
    with patch("routes.chat._get_async_graph", new=AsyncMock()) as mock:
        mock.return_value.astream_events = _empty_stream
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "customer_id": 1, "agent_type": "calendar"},
        )

    assert resp.status_code == 422


def test_refund_email_agent_without_customer_id_is_accepted():
    with patch("routes.chat._get_async_graph", new=AsyncMock()) as mock:
        mock.return_value.astream_events = _empty_stream
        from main import app
        client = TestClient(app)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "agent_type": "refund_email"},
        )

    assert resp.status_code == 200


# ── Cycle 4: unknown agent_type is rejected ───────────────────────────────────

def test_unknown_agent_type_returns_422():
    with patch("routes.chat._get_async_graph", new=AsyncMock()) as mock:
        mock.return_value.astream_events = _empty_stream
        from main import app
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/chat/stream",
            json={"message": "hello", "agent_type": "totally_unknown_agent"},
        )

    assert resp.status_code == 422
