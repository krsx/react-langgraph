import pytest
import json
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def make_tool_msg(content: dict, tool_call_id: str = "tc1") -> ToolMessage:
    return ToolMessage(content=json.dumps(content), tool_call_id=tool_call_id)


def make_state(messages=None, memory_context=None):
    return {
        "customer_id": 1,
        "messages": messages or [],
        "memory_context": memory_context,
        "tool_results": None,
        "verification": None,
    }


# ── Cycle 1: Verifier valid=True when no tool errors ────────────────────────

def test_verifier_valid_when_no_tool_messages():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="hello"),
        AIMessage(content="How can I help?"),
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is True
    assert result["verification"]["override_message"] is None


def test_verifier_valid_when_tool_results_are_clean():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="Check order 5678"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "order_lookup", "args": {"order_id": 5678}}]),
        make_tool_msg({"order_id": 5678, "status": "delivered"}),
        AIMessage(content="Your order 5678 has been delivered."),
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is True
    assert result["verification"]["override_message"] is None


# ── Cycle 2: Verifier valid=False + override when error not acknowledged ─────

def test_verifier_invalid_with_override_when_error_not_acknowledged():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="Check order 0"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "order_lookup", "args": {"order_id": 0}}]),
        make_tool_msg({"error": "Order 0 not found or not accessible."}),
        AIMessage(content="Your order is on its way!"),  # hallucination
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is False
    assert result["verification"]["override_message"] is not None
    assert "not" in result["verification"]["override_message"].lower()


# ── Cycle 3: Verifier valid=False + no override when LLM acknowledges ────────

def test_verifier_invalid_no_override_when_error_acknowledged():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="Check order 0"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "order_lookup", "args": {"order_id": 0}}]),
        make_tool_msg({"error": "Order 0 not found or not accessible."}),
        AIMessage(content="I'm sorry, I couldn't find order 0. It may not exist."),
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is False
    assert result["verification"]["override_message"] is None


# ── Cycle 4: build_system_prompt — no sections for empty context ─────────────

def test_build_system_prompt_empty_context_has_no_sections():
    from graph.customer_service.planner import build_system_prompt

    prompt = build_system_prompt([])

    assert "Customer History" not in prompt
    assert "Complaint History" not in prompt


# ── Cycle 5: build_system_prompt — Customer History for memory entries ────────

def test_build_system_prompt_includes_customer_history():
    from graph.customer_service.planner import build_system_prompt

    context = [
        {"type": "memory", "key": "late_delivery_1", "value": "Order 1001 was late"},
        {"type": "memory", "key": "complaint_count", "value": "2"},
    ]
    prompt = build_system_prompt(context)

    assert "Customer History" in prompt
    assert "late_delivery_1" in prompt
    assert "Order 1001 was late" in prompt


# ── Cycle 6: build_system_prompt — Complaint History for complaint entries ────

def test_build_system_prompt_includes_complaint_history():
    from graph.customer_service.planner import build_system_prompt

    context = [
        {"type": "complaint", "order_id": 2222, "issue": "Item damaged", "status": "open", "created_at": "2026-01-01"},
    ]
    prompt = build_system_prompt(context)

    assert "Complaint History" in prompt
    assert "2222" in prompt
    assert "Item damaged" in prompt


# ── Cycle 7: end-to-end graph.invoke with real LLM ───────────────────────────

@pytest.mark.integration
def test_graph_invoke_end_to_end_with_real_llm():
    from graph.customer_service.graph import graph, RECURSION_LIMIT
    from langchain_core.messages import HumanMessage

    result = graph.invoke(
        {"messages": [HumanMessage(content="Where is order 12345?")], "customer_id": 1},
        config={
            "configurable": {"thread_id": "e2e-test-1", "customer_id": 1},
            "recursion_limit": RECURSION_LIMIT,
        },
    )

    assert "messages" in result
    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert len(last.content) > 0
    assert result["verification"]["valid"] is not None


# ── Cycle 8: tool_results audit trail is populated ───────────────────────────

def test_verifier_populates_tool_results_on_clean_run():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="Check order 5678"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "order_lookup", "args": {"order_id": 5678}}]),
        make_tool_msg({"order_id": 5678, "status": "delivered"}),
        AIMessage(content="Your order 5678 has been delivered."),
    ])
    result = verifier(state)

    assert "tool_results" in result
    assert result["tool_results"] == [{"order_id": 5678, "status": "delivered"}]


def test_verifier_populates_empty_tool_results_when_no_tool_messages():
    from graph.shared.verifier import verifier

    state = make_state(messages=[HumanMessage(content="hello"), AIMessage(content="Hi!")])
    result = verifier(state)

    assert result["tool_results"] == []


# ── Cycle 9: empty lookup detection ──────────────────────────────────────────

def test_verifier_invalid_when_tool_returns_empty_list():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="What are my past orders?"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "memory_tool", "args": {"action": "read"}}]),
        make_tool_msg({"memories": []}),
        AIMessage(content="Your order history is full of recent purchases!"),  # hallucination
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is False
    checks = result["verification"]["checks"]
    assert any("empty lookup" in c for c in checks)


def test_verifier_valid_when_non_empty_list_in_tool_result():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="What are my memories?"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "memory_tool", "args": {"action": "read"}}]),
        make_tool_msg({"memories": [{"key": "pref", "value": "fast shipping"}]}),
        AIMessage(content="You prefer fast shipping."),
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is True


# ── Cycle 10: override replaces hallucinated assistant message ────────────────

def test_verifier_appends_override_message_to_messages():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="Check order 0"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "order_lookup", "args": {"order_id": 0}}]),
        make_tool_msg({"error": "Order 0 not found or not accessible."}),
        AIMessage(content="Your order is on its way!"),  # hallucination
    ])
    result = verifier(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    override_msg = result["messages"][0]
    assert isinstance(override_msg, AIMessage)
    assert result["verification"]["override_message"] in override_msg.content


def test_verifier_does_not_append_messages_when_llm_acknowledged():
    from graph.shared.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="Check order 0"),
        AIMessage(content="", tool_calls=[{"id": "tc1", "name": "order_lookup", "args": {"order_id": 0}}]),
        make_tool_msg({"error": "Order 0 not found or not accessible."}),
        AIMessage(content="I'm sorry, I couldn't find order 0. It may not exist."),
    ])
    result = verifier(state)

    assert "messages" not in result or result.get("messages") is None or result.get("messages") == []


# ── Cycle 11: failure-case correctness (mock graph, no real LLM) ─────────────

def test_graph_invoke_failure_case_sets_override(monkeypatch):
    """When the LLM hallucinates over a tool error, verifier must surface the override."""
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
    import json

    # Build a minimal state that looks like post-planner (tool error + hallucination)
    tool_err_msg = ToolMessage(
        content=json.dumps({"error": "Order 99999 not found or not accessible."}),
        tool_call_id="tc-fake",
    )
    hallucinated_ai = AIMessage(content="Your order 99999 will arrive tomorrow!")

    state = make_state(messages=[
        HumanMessage(content="Where is order 99999?"),
        AIMessage(content="", tool_calls=[{"id": "tc-fake", "name": "order_lookup", "args": {"order_id": 99999}}]),
        tool_err_msg,
        hallucinated_ai,
    ])

    from graph.shared.verifier import verifier
    result = verifier(state)

    assert result["verification"]["valid"] is False
    assert result["verification"]["override_message"] is not None
    assert "messages" in result
    final_msg = result["messages"][0]
    assert isinstance(final_msg, AIMessage)
    assert "could not" in final_msg.content.lower()