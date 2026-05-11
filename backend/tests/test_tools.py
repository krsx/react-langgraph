import pytest
import os

pytestmark = pytest.mark.integration

CONFIG = {"configurable": {"customer_id": 1, "thread_id": "test-tools"}}
OTHER_CONFIG = {"configurable": {"customer_id": 2, "thread_id": "test-tools"}}


# ── Cycle 1: order_lookup returns full dict for valid order ──────────────────

@pytest.mark.integration
def test_order_lookup_returns_order_dict_for_valid_order():
    from graph.tools import order_lookup

    result = order_lookup.invoke({"order_id": 5678}, config=CONFIG)

    assert result["order_id"] == 5678
    assert result["customer_id"] == 1
    assert result["status"] == "delivered"
    assert "product_name" in result
    assert "order_date" in result
    assert "delivery_date" in result


# ── Cycle 2: order_lookup returns error dict for non-existent order ──────────

@pytest.mark.integration
def test_order_lookup_returns_error_for_nonexistent_order():
    from graph.tools import order_lookup

    result = order_lookup.invoke({"order_id": 0}, config=CONFIG)

    assert "error" in result
    assert "0" in result["error"]


# ── Cycle 3: order_lookup enforces customer scoping ──────────────────────────

@pytest.mark.integration
def test_order_lookup_rejects_cross_customer_access():
    from graph.tools import order_lookup

    result = order_lookup.invoke({"order_id": 5678}, config=OTHER_CONFIG)

    assert "error" in result


# ── Cycle 4: customer_profile returns full customer dict ─────────────────────

@pytest.mark.integration
def test_customer_profile_returns_customer_dict():
    from graph.tools import customer_profile

    result = customer_profile.invoke({}, config=CONFIG)

    assert result["customer_id"] == 1
    assert "name" in result
    assert "email" in result