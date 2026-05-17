import pytest
from langchain_core.messages import HumanMessage, ToolMessage

pytestmark = pytest.mark.integration


def make_state(customer_id, messages=None, tool_results=None):
    return {
        "customer_id": customer_id,
        "messages": messages or [],
        "memory_context": None,
        "tool_results": tool_results,
        "verification": None,
    }


# ── Cycle 1: Memory Loader returns type="memory" entries ────────────────────

@pytest.mark.integration
def test_memory_loader_returns_memory_entries_for_customer():
    from graph.memory_loader import memory_loader

    result = memory_loader(make_state(1))

    assert "memory_context" in result
    memory_entries = [e for e in result["memory_context"] if e["type"] == "memory"]
    assert len(memory_entries) >= 1
    assert all("key" in e and "value" in e for e in memory_entries)


# ── Cycle 2: Memory Loader returns type="complaint" entries ─────────────────

@pytest.mark.integration
def test_memory_loader_returns_complaint_entries_for_customer():
    from graph.memory_loader import memory_loader

    result = memory_loader(make_state(1))

    complaint_entries = [e for e in result["memory_context"] if e["type"] == "complaint"]
    assert len(complaint_entries) >= 1
    assert all("order_id" in e and "issue" in e and "status" in e for e in complaint_entries)


# ── Cycle 3: Memory Loader returns [] for customer with no data ─────────────

@pytest.mark.integration
def test_memory_loader_returns_empty_list_for_customer_with_no_data():
    from db.connection import get_connection
    from graph.memory_loader import memory_loader

    customer_id = 999999
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
        cursor.execute(
            "INSERT INTO customers (customer_id, name, email) VALUES (%s, %s, %s)",
            (customer_id, "Empty Customer", "empty.customer@example.com"),
        )
        conn.commit()

        result = memory_loader(make_state(customer_id))

        assert result["memory_context"] == []
    finally:
        cleanup_cursor = conn.cursor()
        cleanup_cursor.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
        conn.commit()
        conn.close()


# ── Cycle 4: Memory Update writes last_interaction_summary ──────────────────

@pytest.mark.integration
def test_memory_update_writes_interaction_summary():
    from graph.memory_update import memory_update
    from db.connection import get_connection

    state = make_state(
        customer_id=1,
        messages=[
            HumanMessage(content="Refund order 7890"),
            ToolMessage(
                content='{"order_id": 7890, "status": "refund_requested"}',
                tool_call_id="call_1",
                name="refund",
            ),
        ],
    )

    memory_update(state)

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT value FROM customer_memory WHERE customer_id = 1 AND `key` = 'last_interaction_summary'"
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    assert row is not None
    assert "Refund order 7890" in row["value"]
    assert "refund" in row["value"]


# ── Cycle 5: Memory Update upserts (no duplicate on repeat call) ────────────

@pytest.mark.integration
def test_memory_update_upserts_on_repeat_call():
    from graph.memory_update import memory_update
    from db.connection import get_connection

    state = make_state(1, messages=[HumanMessage(content="Check order 1001")])
    memory_update(state)
    memory_update(state)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM customer_memory WHERE customer_id = 1 AND `key` = 'last_interaction_summary'"
        )
        count = cursor.fetchone()[0]
    finally:
        conn.close()

    assert count == 1


# ── Cycle 6: Memory Update skips write when customer_id is None ─────────────

@pytest.mark.integration
def test_memory_update_skips_write_when_no_customer_id():
    from graph.memory_update import memory_update

    state = make_state(None, messages=[HumanMessage(content="hello")])
    result = memory_update(state)

    assert result == {}
