import sqlite3
import uuid
import pathlib

import openai as _openai
import pytest
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from db.connection import get_connection
from graph.graph import builder, RECURSION_LIMIT

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
