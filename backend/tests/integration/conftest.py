import json
import sqlite3
import uuid
import pathlib

import openai as _openai
import pytest
from dotenv import load_dotenv
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite import SqliteSaver

from db.connection import get_connection
from graph.customer_service.graph import builder, RECURSION_LIMIT

load_dotenv(pathlib.Path(__file__).parent.parent.parent.parent / ".env")


# ── Rate-limit guard ─────────────────────────────────────────────────────────
# OpenRouter free-tier has a 50-req/day cap.  When that cap is hit, skip the
# remaining tests with a clear message rather than failing the suite.


def handle_rate_limit(exc: _openai.RateLimitError) -> None:
    """Skip test cleanly if the daily free-model quota is exhausted."""
    msg = str(exc)
    if "per-day" in msg or "per_day" in msg or "per day" in msg.lower():
        pytest.skip(f"OpenRouter daily quota exhausted — rerun tomorrow: {exc}")
    raise exc


@pytest.fixture
def agent_graph():
    """Fresh in-memory checkpointer graph per test — isolated state, supports STM."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    return builder.compile(checkpointer=checkpointer).with_config({"recursion_limit": RECURSION_LIMIT})


@pytest.fixture
def thread():
    return f"integ-{uuid.uuid4()}"


@pytest.fixture
def reset_order_5678():
    yield
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'delivered' WHERE order_id = 5678")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def reset_order_7890():
    yield
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE orders SET status = 'delivered' WHERE order_id = 7890")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def complaint_cleanup():
    """Yields max complaint_id before test; deletes any complaint inserted after."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(complaint_id), 0) FROM complaints")
        max_id = cursor.fetchone()[0]
    finally:
        conn.close()

    yield max_id

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM complaints WHERE complaint_id > %s", (max_id,))
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def memory_snapshot():
    """Snapshot customer_memory for customer 1; restores exact state after test."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT `key`, value FROM customer_memory WHERE customer_id = 1")
        snapshot = {row["key"]: row["value"] for row in cursor.fetchall()}
    finally:
        conn.close()

    yield snapshot

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT `key` FROM customer_memory WHERE customer_id = 1")
        current_keys = {row["key"] for row in cursor.fetchall()}

        new_keys = current_keys - set(snapshot.keys())
        plain = conn.cursor()
        for key in new_keys:
            plain.execute(
                "DELETE FROM customer_memory WHERE customer_id = 1 AND `key` = %s", (key,)
            )
        for key, value in snapshot.items():
            plain.execute(
                "UPDATE customer_memory SET value = %s WHERE customer_id = 1 AND `key` = %s",
                (value, key),
            )
        conn.commit()
    finally:
        conn.close()


# ── Workspace agent mock tools ────────────────────────────────────────────────
# These are realistic tool doubles injected via compile_graph(tools, checkpointer).
# They return JSON shaped like real Gmail / Google Calendar API responses so the
# LLM reasons against plausible data without requiring live service credentials.

@tool
def search_gmail(query: str) -> str:
    """Search Gmail for emails matching a query."""
    return json.dumps([
        {"id": "msg1", "subject": "Refund for order #1234", "snippet": "I want a full refund for my broken item"},
        {"id": "msg2", "subject": "Return request for order #5678", "snippet": "I need to return this — it does not fit"},
    ])


@tool
def get_message(message_id: str) -> str:
    """Get the full content of a Gmail message by ID."""
    bodies = {
        "msg1": "Hi, I received order #1234 and the item arrived broken. Please refund me immediately.",
        "msg2": "Hello, I would like to return the item from order #5678. It does not fit as described.",
    }
    return json.dumps({
        "id": message_id,
        "subject": "Customer request",
        "from": "customer@example.com",
        "body": bodies.get(message_id, "Customer email body."),
    })


@tool
def send_reply(message_id: str, body: str) -> str:
    """Send a reply to a Gmail message."""
    return json.dumps({"status": "sent", "message_id": message_id})


@tool("search_gmail")
def _search_gmail_permission_denied(query: str) -> str:
    """Search Gmail for emails matching a query."""
    return json.dumps({"error": "permission denied: insufficient Gmail scopes to read messages"})


@tool
def create_event(summary: str, start: str, end: str) -> str:
    """Create a new Google Calendar event."""
    return json.dumps({"id": "evt_abc123", "summary": summary, "start": start, "end": end, "status": "confirmed"})


@tool("create_event")
def _create_event_rate_limited(summary: str, start: str, end: str) -> str:
    """Create a new Google Calendar event."""
    return json.dumps({"error": "rate limit exceeded: Calendar API write quota exhausted"})


MOCK_GMAIL_TOOLS = [search_gmail, get_message, send_reply]
MOCK_GMAIL_ERROR_TOOLS = [_search_gmail_permission_denied]
MOCK_CALENDAR_MCP_TOOLS = [create_event]
MOCK_CALENDAR_ERROR_MCP_TOOLS = [_create_event_rate_limited]


# ── Workspace fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def ws_thread():
    """Fresh UUID thread ID for workspace agent tests (no customer_id)."""
    return f"ws-integ-{uuid.uuid4()}"


@pytest.fixture
def refund_email_graph():
    """Refund Email graph compiled with mock Gmail tools and an in-memory checkpointer."""
    from graph.refund_email.graph import compile_graph
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return compile_graph(MOCK_GMAIL_TOOLS, SqliteSaver(conn))


@pytest.fixture
def refund_email_error_graph():
    """Refund Email graph where search_gmail always returns permission-denied."""
    from graph.refund_email.graph import compile_graph
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return compile_graph(MOCK_GMAIL_ERROR_TOOLS, SqliteSaver(conn))


@pytest.fixture
def calendar_graph():
    """Calendar graph compiled with real CLI tools + mock create_event MCP tool."""
    from graph.calendar.graph import compile_graph, CLI_TOOLS
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return compile_graph(CLI_TOOLS + MOCK_CALENDAR_MCP_TOOLS, SqliteSaver(conn))


@pytest.fixture
def calendar_error_graph():
    """Calendar graph where create_event always returns a rate-limit error."""
    from graph.calendar.graph import compile_graph, CLI_TOOLS
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    return compile_graph(CLI_TOOLS + MOCK_CALENDAR_ERROR_MCP_TOOLS, SqliteSaver(conn))
