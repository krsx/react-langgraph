import pytest

pytestmark = pytest.mark.integration

CONFIG = {"configurable": {"customer_id": 1, "thread_id": "test-write-tools"}}
OTHER_CONFIG = {"configurable": {"customer_id": 2, "thread_id": "test-write-tools"}}


@pytest.fixture
def reset_order_7890():
    """Reset order 7890 back to delivered after refund tests mutate it."""
    yield
    from db.connection import get_connection
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE orders SET status = 'delivered' WHERE order_id = 7890",
        )
        conn.commit()
    finally:
        conn.close()


# ── Cycle 1: refund succeeds for eligible delivered order ────────────────────

@pytest.mark.integration
def test_refund_succeeds_for_delivered_order(reset_order_7890):
    from graph.customer_service.tools import refund

    result = refund.invoke({"order_id": 7890}, config=CONFIG)

    assert result["success"] is True
    assert result["order_id"] == 7890
    assert result["status"] == "refund_requested"


# ── Cycle 2: refund returns error for ineligible status ─────────────────────

@pytest.mark.integration
def test_refund_returns_error_for_ineligible_status():
    from graph.customer_service.tools import refund

    result = refund.invoke({"order_id": 1001}, config=CONFIG)

    assert "error" in result
    assert "processing" in result["error"]


# ── Cycle 3: refund returns error for non-existent / cross-customer order ───

@pytest.mark.integration
def test_refund_returns_error_for_nonexistent_order():
    from graph.customer_service.tools import refund

    result = refund.invoke({"order_id": 0}, config=CONFIG)

    assert "error" in result
    assert "not found" in result["error"]


@pytest.mark.integration
def test_refund_returns_error_for_cross_customer_access():
    from graph.customer_service.tools import refund

    result = refund.invoke({"order_id": 7890}, config=OTHER_CONFIG)

    assert "error" in result
    assert "does not belong" in result["error"]


# ── Cycle 4: complaint_logger inserts and returns complaint_id ───────────────

@pytest.mark.integration
def test_complaint_logger_returns_complaint_id():
    from graph.customer_service.tools import complaint_logger

    result = complaint_logger.invoke(
        {"order_id": 2222, "issue": "Item arrived damaged"}, config=CONFIG
    )

    assert result["success"] is True
    assert "complaint_id" in result
    assert isinstance(result["complaint_id"], int)


# ── Cycle 5: memory_tool read returns all entries ────────────────────────────

@pytest.mark.integration
def test_memory_tool_read_returns_all_entries():
    from graph.customer_service.tools import memory_tool

    result = memory_tool.invoke({"action": "read"}, config=CONFIG)

    assert "memories" in result
    assert len(result["memories"]) >= 3
    assert all("key" in m and "value" in m for m in result["memories"])


# ── Cycle 6: memory_tool read filters by key ────────────────────────────────

@pytest.mark.integration
def test_memory_tool_read_filters_by_key():
    from graph.customer_service.tools import memory_tool

    result = memory_tool.invoke(
        {"action": "read", "key": "late_delivery_pattern"}, config=CONFIG
    )

    assert "memories" in result
    assert len(result["memories"]) == 1
    assert result["memories"][0]["key"] == "late_delivery_pattern"


# ── Cycle 7: memory_tool write upserts (no duplicate on repeat) ─────────────

@pytest.mark.integration
def test_memory_tool_write_upserts_on_repeat_key():
    from graph.customer_service.tools import memory_tool
    from db.connection import get_connection

    memory_tool.invoke(
        {"action": "write", "key": "test_pref", "value": "first"}, config=CONFIG
    )
    memory_tool.invoke(
        {"action": "write", "key": "test_pref", "value": "second"}, config=CONFIG
    )

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT value FROM customer_memory WHERE customer_id = 1 AND `key` = 'test_pref'"
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    assert len(rows) == 1
    assert rows[0]["value"] == "second"


# ── Cycle 8: memory_tool returns error for unknown action ────────────────────

@pytest.mark.integration
def test_memory_tool_returns_error_for_unknown_action():
    from graph.customer_service.tools import memory_tool

    result = memory_tool.invoke({"action": "delete"}, config=CONFIG)

    assert "error" in result