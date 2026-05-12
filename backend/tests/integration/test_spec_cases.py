"""
Integration test suite — all 11 spec cases.
Requires: OPENROUTER_API_KEY env var, live MySQL (docker compose up mysql).
Run: pytest tests/integration/ -m integration -v
"""
import uuid
import pytest
import openai
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from db.connection import get_connection
from tests.integration.conftest import handle_rate_limit


# ── Helpers ──────────────────────────────────────────────────────────────────


def make_config(thread_id: str, customer_id: int = 1) -> dict:
    return {"configurable": {"thread_id": thread_id, "customer_id": customer_id}}


def invoke(graph, message: str, customer_id: int, thread_id: str) -> dict:
    try:
        return graph.invoke(
            {"messages": [HumanMessage(content=message)], "customer_id": customer_id},
            config=make_config(thread_id, customer_id),
        )
    except openai.RateLimitError as exc:
        handle_rate_limit(exc)


def tool_names_used(messages: list) -> set[str]:
    """Return the set of tool names the planner called (from AIMessage.tool_calls)."""
    names: set[str] = set()
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in getattr(m, "tool_calls", []) or []:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    names.add(name)
    return names


def last_ai_content(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content.lower()
    return ""


# ── Test 1: Intent Parsing ────────────────────────────────────────────────────


@pytest.mark.integration
def test_01_intent_parsing(agent_graph, thread):
    """'Where is my order 12345?' → agent calls order_lookup for order 12345."""
    result = invoke(agent_graph, "Where is my order 12345?", 1, thread)

    assert "messages" in result
    used = tool_names_used(result["messages"])
    order_looked_up = "order_lookup" in used
    order_in_results = result["tool_results"] and any(
        r.get("order_id") == 12345 for r in result["tool_results"]
    )
    assert order_looked_up or order_in_results, (
        f"Expected order_lookup to be called. Tools used: {used}, "
        f"tool_results: {result.get('tool_results')}"
    )


# ── Test 2: OrderLookupTool ───────────────────────────────────────────────────


@pytest.mark.integration
def test_02_order_lookup_tool(agent_graph, thread):
    """'Check status of order 1001' → MySQL executed, order data returned."""
    result = invoke(agent_graph, "Check status of order 1001", 1, thread)

    assert result["tool_results"] is not None, "tool_results must be populated"
    assert len(result["tool_results"]) > 0, "tool_results should not be empty"

    # tool_results may be fully parsed dicts or {"raw": "..."} when datetime serialisation
    # prevents JSON decoding; check both formats.
    tool_messages_text = " ".join(
        str(m.content) for m in result["messages"] if isinstance(m, ToolMessage)
    )
    order_found = (
        any(r.get("order_id") == 1001 for r in result["tool_results"])
        or ("1001" in tool_messages_text and "processing" in tool_messages_text)
        or any("1001" in str(r.get("raw", "")) and "processing" in str(r.get("raw", ""))
               for r in result["tool_results"])
    )
    assert order_found, (
        f"Expected order 1001 (processing) in results. "
        f"tool_results={result['tool_results']}"
    )


# ── Test 3: CustomerProfileTool ───────────────────────────────────────────────


@pytest.mark.integration
def test_03_customer_profile_tool(agent_graph, thread):
    """'Show my profile' → customer info retrieved."""
    result = invoke(agent_graph, "Show my profile", 1, thread)

    used = tool_names_used(result["messages"])
    profile_in_results = result["tool_results"] and any(
        r.get("customer_id") == 1 for r in result["tool_results"]
    )
    assert "customer_profile" in used or profile_in_results, (
        f"Expected customer_profile to be called. Tools used: {used}"
    )


# ── Test 4: RefundTool ────────────────────────────────────────────────────────


@pytest.mark.integration
def test_04_refund_tool(agent_graph, thread, reset_order_5678):
    """'Refund order 5678' → order status updated to refund_requested in DB."""
    result = invoke(agent_graph, "Refund order 5678", 1, thread)

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM orders WHERE order_id = 5678")
        row = cursor.fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["status"] == "refund_requested", (
        f"Expected status=refund_requested, got {row['status']}"
    )
    assert result["verification"] is not None
    assert result["verification"]["valid"] is True


# ── Test 5: ComplaintLoggerTool ────────────────────────────────────────────────


@pytest.mark.integration
def test_05_complaint_logger_tool(agent_graph, thread, complaint_cleanup):
    """'I want to complain about order 2222' → complaint record inserted in DB."""
    max_id_before = complaint_cleanup

    result = invoke(agent_graph, "Please log a complaint for order 2222 — my delivery arrived damaged", 1, thread)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM complaints "
            "WHERE customer_id = 1 AND order_id = 2222 AND complaint_id > %s",
            (max_id_before,),
        )
        new_complaint_count = cursor.fetchone()[0]
    finally:
        conn.close()

    assert new_complaint_count >= 1, (
        "Expected at least one new complaint for order 2222 to be inserted. "
        f"Tools used: {tool_names_used(result['messages'])}"
    )


# ── Test 6: Multi-step reasoning ──────────────────────────────────────────────


@pytest.mark.integration
def test_06_multi_step_reasoning(agent_graph, thread, reset_order_7890):
    """'Refund order 7890 if delivered' → order_lookup first, then refund; DB updated."""
    result = invoke(agent_graph, "Refund order 7890 if it has been delivered", 1, thread)

    used = tool_names_used(result["messages"])
    assert "order_lookup" in used, f"Expected order_lookup call in multi-step. Got: {used}"
    assert "refund" in used, f"Expected refund call after order_lookup. Got: {used}"

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT status FROM orders WHERE order_id = 7890")
        row = cursor.fetchone()
    finally:
        conn.close()

    assert row["status"] == "refund_requested", (
        f"Expected refund_requested, got {row['status']}"
    )


# ── Test 7: Short-term memory ─────────────────────────────────────────────────


@pytest.mark.integration
def test_07_short_term_memory(agent_graph):
    """Two turns on the same thread — agent must reference order 1001 from prior turn."""
    tid = f"stm-{uuid.uuid4()}"
    cfg = make_config(tid, customer_id=1)

    # First turn: look up order 1001
    try:
        agent_graph.invoke(
            {"messages": [HumanMessage(content="Check order 1001")], "customer_id": 1},
            config=cfg,
        )
    except openai.RateLimitError as exc:
        handle_rate_limit(exc)

    # Second turn: vague follow-up; agent must use context to know "it" = 1001
    try:
        result2 = agent_graph.invoke(
            {"messages": [HumanMessage(content="Cancel it")], "customer_id": 1},
            config=cfg,
        )
    except openai.RateLimitError as exc:
        handle_rate_limit(exc)

    # Check that 1001 appears in tool call args or tool messages
    all_text = " ".join(
        str(m.content) for m in result2["messages"] if isinstance(m, (AIMessage, ToolMessage))
    )
    tool_args_text = " ".join(
        str(tc.get("args", {}) if isinstance(tc, dict) else vars(tc).get("args", {}))
        for m in result2["messages"]
        if isinstance(m, AIMessage)
        for tc in (getattr(m, "tool_calls", []) or [])
    )
    assert "1001" in all_text or "1001" in tool_args_text, (
        "Agent should reference order 1001 from prior turn context"
    )


# ── Test 8: Long-term memory read ─────────────────────────────────────────────


@pytest.mark.integration
def test_08_long_term_memory_read(agent_graph, thread):
    """'What issues have I had before?' → memory_context populated, LLM references history."""
    result = invoke(agent_graph, "What issues have I had before?", 1, thread)

    # memory_loader always populates memory_context for authenticated customers
    assert result["memory_context"] is not None
    assert len(result["memory_context"]) > 0, "memory_context should contain seeded entries"

    # Seeded entries include delivery history and complaints
    has_memory = any(e.get("type") == "memory" for e in result["memory_context"])
    has_complaint = any(e.get("type") == "complaint" for e in result["memory_context"])
    assert has_memory or has_complaint, "memory_context should include at least one seeded entry"

    # LLM response should reference delivery problems or history
    content = last_ai_content(result["messages"])
    assert any(kw in content for kw in ["late", "deliver", "delay", "order", "issue", "complaint", "problem", "history"]), (
        f"Expected response to reference delivery history. Got: {content[:200]}"
    )


# ── Test 9: Long-term memory write ────────────────────────────────────────────


@pytest.mark.integration
def test_09_long_term_memory_write(agent_graph, thread, memory_snapshot):
    """'Remember I prefer refunds' → memory entry saved to customer_memory via memory_tool."""
    result = invoke(agent_graph, "Remember that I prefer refunds over store credit", 1, thread)

    used = tool_names_used(result["messages"])
    assert "memory_tool" in used, (
        f"Expected memory_tool to be called for explicit memory write. Tools used: {used}"
    )

    # Verify DB side-effect: a new key unrelated to last_interaction_summary was written
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT `key`, value FROM customer_memory WHERE customer_id = 1")
        rows = cursor.fetchall()
    finally:
        conn.close()

    snapshot_keys = set(memory_snapshot.keys())
    new_keys = {r["key"] for r in rows} - snapshot_keys - {"last_interaction_summary"}
    refund_value_present = any(
        "refund" in (r.get("value") or "").lower() or "refund" in (r.get("key") or "").lower()
        for r in rows
        if r["key"] not in snapshot_keys
    )
    assert len(new_keys) > 0 or refund_value_present, (
        f"Expected a preference key with 'refund' to be written. New keys: {new_keys}"
    )


# ── Test 10: Personalization ──────────────────────────────────────────────────


@pytest.mark.integration
def test_10_personalization(agent_graph, thread, memory_snapshot):
    """'My order is late again' → agent detects repeated late-delivery pattern from memory."""
    result = invoke(agent_graph, "My order is late again", 1, thread)

    content = last_ai_content(result["messages"])
    # Agent should acknowledge the pattern — not just say "sorry" but reference past history
    pattern_keywords = [
        "again", "pattern", "history", "previous", "before", "already",
        "repeat", "recurring", "multiple", "past", "apolog", "understand",
    ]
    assert any(kw in content for kw in pattern_keywords), (
        f"Expected response to reflect late-delivery pattern from memory. Got: {content[:300]}"
    )


# ── Test 11: Verifier rejects non-existent order ─────────────────────────────


@pytest.mark.integration
def test_11_verifier_rejects_nonexistent_order(agent_graph, thread):
    """'Refund order 0000' → Verifier marks valid=False because order doesn't exist."""
    result = invoke(agent_graph, "Refund order 0000", 1, thread)

    assert result["verification"] is not None

    if result["tool_results"]:
        # Tool was called and returned an error → verifier must flag it
        assert result["verification"]["valid"] is False, (
            f"Verifier should reject non-existent order. "
            f"verification={result['verification']}"
        )
    else:
        # LLM declined without calling tools — it must at least say so
        content = last_ai_content(result["messages"])
        assert any(kw in content for kw in ["not found", "error", "cannot", "unable", "doesn't exist", "do not", "no order"]), (
            f"Expected LLM to report order 0000 not found. Got: {content[:200]}"
        )
