import pytest
import sys


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("graph.refund_email"):
            sys.modules.pop(mod, None)


# ── Cycle 1: graph compiles with mock tools ───────────────────────────────────

def test_create_builder_compiles_with_empty_tool_list():
    from graph.refund_email.graph import create_builder
    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3

    builder = create_builder([])
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    graph = builder.compile(checkpointer=SqliteSaver(conn))
    assert graph is not None


# ── Cycle 2: graph topology — correct nodes, no memory nodes ─────────────────

def test_graph_has_correct_nodes_and_no_memory_nodes():
    from graph.refund_email.graph import create_builder

    builder = create_builder([])
    node_names = set(builder.nodes.keys())

    assert "planner" in node_names
    assert "tools" in node_names
    assert "verifier" in node_names
    assert "memory_loader" not in node_names
    assert "memory_update" not in node_names


# ── Cycle 3: system prompt encodes 6-step workflow ────────────────────────────

def test_system_prompt_contains_all_six_workflow_steps():
    from graph.refund_email.planner import build_system_prompt

    prompt = build_system_prompt()

    for step in ("SEARCH", "READ", "CLASSIFY", "DRAFT", "SEND", "REPORT"):
        assert step in prompt, f"System prompt missing step: {step}"


# ── Cycle 4: system prompt encodes all 4 classification labels ────────────────

def test_system_prompt_contains_all_four_classification_labels():
    from graph.refund_email.planner import build_system_prompt

    prompt = build_system_prompt()

    for label in ("REFUND_REQUEST", "RETURN_REQUEST", "COMPLAINT", "OTHER"):
        assert label in prompt, f"System prompt missing classification: {label}"


# ── Cycle 5: router dispatches "refund_email" ─────────────────────────────────

def test_router_get_graph_dispatches_refund_email():
    from graph.router import get_graph
    g = get_graph("refund_email")
    assert g is not None


# ── Cycle 6: get_async_graph caches on repeated calls ─────────────────────────

def test_get_async_graph_returns_same_instance_on_repeated_calls():
    import asyncio
    import graph.refund_email.graph as re_module

    re_module._async_graph = None
    re_module._async_checkpointer_cm = None

    async def run():
        g1 = await re_module.get_async_graph()
        g2 = await re_module.get_async_graph()
        return g1, g2

    g1, g2 = asyncio.run(run())
    assert g1 is g2


# ── Cycle 7: integration — graph invoke with mock tools returns AIMessage ──────

@pytest.mark.integration
def test_graph_invoke_with_mock_gmail_tools_returns_ai_message():
    import sqlite3
    import json
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.refund_email.graph import compile_graph

    @tool
    def search_gmail(query: str) -> str:
        """Search Gmail for emails matching a query."""
        return json.dumps([{"id": "msg1", "subject": "Refund request", "snippet": "I want a refund"}])

    @tool
    def get_message(message_id: str) -> str:
        """Get the full content of a Gmail message by ID."""
        return json.dumps({"id": message_id, "body": "Please refund my order #1234."})

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([search_gmail, get_message], SqliteSaver(conn))

    result = g.invoke(
        {"messages": [HumanMessage(content="What refund emails came in today?")], "customer_id": None},
        config={"configurable": {"thread_id": "re-test-1"}},
    )

    assert "messages" in result
    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert len(last.content) > 0


# ── Cycle 8: batch workflow produces multiple tool calls across the 6 steps ────

def test_batch_workflow_produces_multiple_tool_calls_across_steps():
    import sqlite3
    import json
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.refund_email.graph import compile_graph

    @tool
    def search_gmail(query: str) -> str:
        """Search Gmail for emails matching a query."""
        return json.dumps([{"id": "msg1", "subject": "Refund request"}])

    @tool
    def get_message(message_id: str) -> str:
        """Get the full content of a Gmail message by ID."""
        return json.dumps({"id": message_id, "body": "Please refund my order #1234."})

    @tool
    def send_reply(message_id: str, body: str) -> str:
        """Send a reply to an email."""
        return json.dumps({"status": "sent"})

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "search_gmail", "args": {"query": "refund OR return"}}],
            )
        elif call_count[0] == 2:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc2", "name": "get_message", "args": {"message_id": "msg1"}}],
            )
        elif call_count[0] == 3:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc3", "name": "send_reply", "args": {"message_id": "msg1", "body": "We have received your refund request."}}],
            )
        else:
            return AIMessage(content="Processed 1 email: 1 REFUND_REQUEST. Sent 1 reply.")

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([search_gmail, get_message, send_reply], SqliteSaver(conn))

    from langgraph.errors import GraphRecursionError
    try:
        with patch("graph.refund_email.planner.create_llm", return_value=mock_llm):
            result = g.invoke(
                {"messages": [HumanMessage(content="Process all refund emails")], "customer_id": None},
                config={"configurable": {"thread_id": "re-batch-test-1"}},
            )
    except GraphRecursionError:
        pytest.fail("Batch workflow hit GraphRecursionError — planner loop did not terminate")

    tool_call_names = [
        tc["name"]
        for msg in result["messages"]
        if hasattr(msg, "tool_calls") and msg.tool_calls
        for tc in msg.tool_calls
    ]

    assert "search_gmail" in tool_call_names
    assert "get_message" in tool_call_names
    assert "send_reply" in tool_call_names
    assert len(tool_call_names) >= 3

    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert len(last.content) > 0


# ── Cycle 9: classification labels appear in planner output ──────────────────

def test_classification_labels_produced_in_agent_response():
    import sqlite3
    import json
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.refund_email.graph import compile_graph

    @tool
    def get_message(message_id: str) -> str:
        """Get the full content of a Gmail message by ID."""
        return json.dumps({"id": message_id, "body": "I want to return my order and get a full refund."})

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "get_message", "args": {"message_id": "msg42"}}],
            )
        else:
            return AIMessage(
                content="Classification: REFUND_REQUEST. The customer is requesting a monetary refund for their order."
            )

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([get_message], SqliteSaver(conn))

    with patch("graph.refund_email.planner.create_llm", return_value=mock_llm):
        result = g.invoke(
            {"messages": [HumanMessage(content="Classify email msg42")], "customer_id": None},
            config={"configurable": {"thread_id": "re-classify-test-1"}},
        )

    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content]
    assert ai_messages, "Expected at least one AIMessage with content"

    all_content = " ".join(m.content for m in ai_messages)
    valid_labels = {"REFUND_REQUEST", "RETURN_REQUEST", "COMPLAINT", "OTHER"}
    assert any(label in all_content for label in valid_labels), (
        f"Expected one of {valid_labels} in agent output, got: {all_content!r}"
    )


# ── Cycle 10: verifier marks run invalid on Gmail permission/API failure ──────

def test_verifier_marks_invalid_on_gmail_permission_error():
    import sqlite3
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.refund_email.graph import compile_graph

    @tool
    def search_gmail(query: str) -> str:
        """Search Gmail for emails matching a query."""
        return "Permission denied: insufficient OAuth scope for Gmail access"

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "search_gmail", "args": {"query": "refund"}}],
            )
        else:
            # Hallucinates — does not acknowledge the permission error
            return AIMessage(content="I found 3 refund emails and processed them all successfully.")

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([search_gmail], SqliteSaver(conn))

    with patch("graph.refund_email.planner.create_llm", return_value=mock_llm):
        result = g.invoke(
            {"messages": [HumanMessage(content="Process all refund emails")], "customer_id": None},
            config={"configurable": {"thread_id": "re-perm-test-1"}},
        )

    verification = result.get("verification", {})
    assert verification.get("valid") is False, "Verifier must mark run invalid on permission error"
    assert verification.get("override_message") is not None, "Verifier must set override message"
    assert "permission" in verification["override_message"].lower() or \
           "could not" in verification["override_message"].lower()
