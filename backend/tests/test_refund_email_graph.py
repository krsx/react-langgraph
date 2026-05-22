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
