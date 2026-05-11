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
    from graph.verifier import verifier

    state = make_state(messages=[
        HumanMessage(content="hello"),
        AIMessage(content="How can I help?"),
    ])
    result = verifier(state)

    assert result["verification"]["valid"] is True
    assert result["verification"]["override_message"] is None


def test_verifier_valid_when_tool_results_are_clean():
    from graph.verifier import verifier

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
    from graph.verifier import verifier

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
    from graph.verifier import verifier

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
    from graph.planner import build_system_prompt

    prompt = build_system_prompt([])

    assert "Customer History" not in prompt
    assert "Open Complaints" not in prompt


# ── Cycle 5: build_system_prompt — Customer History for memory entries ────────

def test_build_system_prompt_includes_customer_history():
    from graph.planner import build_system_prompt

    context = [
        {"type": "memory", "key": "late_delivery_1", "value": "Order 1001 was late"},
        {"type": "memory", "key": "complaint_count", "value": "2"},
    ]
    prompt = build_system_prompt(context)

    assert "Customer History" in prompt
    assert "late_delivery_1" in prompt
    assert "Order 1001 was late" in prompt


# ── Cycle 6: build_system_prompt — Open Complaints for complaint entries ──────

def test_build_system_prompt_includes_open_complaints():
    from graph.planner import build_system_prompt

    context = [
        {"type": "complaint", "order_id": 2222, "issue": "Item damaged", "status": "open", "created_at": "2026-01-01"},
    ]
    prompt = build_system_prompt(context)

    assert "Open Complaints" in prompt
    assert "2222" in prompt
    assert "Item damaged" in prompt


# ── Cycle 7: end-to-end graph.invoke with real LLM ───────────────────────────

@pytest.mark.integration
def test_graph_invoke_end_to_end_with_real_llm():
    from graph.graph import graph, RECURSION_LIMIT
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