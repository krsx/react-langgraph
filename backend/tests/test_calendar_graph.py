import pytest
import sys


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("graph.calendar") and mod != "graph.calendar.cli_tools":
            sys.modules.pop(mod, None)


# ── Cycle 1: graph compiles with mock tools ───────────────────────────────────

def test_create_builder_compiles_with_empty_tool_list():
    from graph.calendar.graph import create_builder
    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3

    builder = create_builder([])
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    graph = builder.compile(checkpointer=SqliteSaver(conn))
    assert graph is not None


# ── Cycle 2: graph topology — correct nodes, no memory nodes ─────────────────

def test_graph_has_correct_nodes_and_no_memory_nodes():
    from graph.calendar.graph import create_builder

    builder = create_builder([])
    node_names = set(builder.nodes.keys())

    assert "planner" in node_names
    assert "tools" in node_names
    assert "verifier" in node_names
    assert "memory_loader" not in node_names
    assert "memory_update" not in node_names


# ── Cycle 3: system prompt encodes workflow steps ─────────────────────────────

def test_system_prompt_contains_workflow_steps():
    from graph.calendar.planner import build_system_prompt

    prompt = build_system_prompt()

    for step in ("QUERY", "LIST", "DRAFT", "SCHEDULE", "CONFIRM", "RESPOND"):
        assert step in prompt, f"System prompt missing step: {step}"


# ── Cycle 4: system prompt covers key operation types ────────────────────────

def test_system_prompt_mentions_key_calendar_operations():
    from graph.calendar.planner import build_system_prompt

    prompt = build_system_prompt()

    for keyword in ("today_events", "list_events", "create_event", "update_event", "delete_event"):
        assert keyword in prompt, f"System prompt missing operation: {keyword}"


# ── Cycle 5: router dispatches "calendar" ────────────────────────────────────

def test_router_get_graph_dispatches_calendar():
    from graph.router import get_graph
    g = get_graph("calendar")
    assert g is not None


# ── Cycle 6: get_async_graph merges CLI tools + MCP tools ────────────────────

def test_get_async_graph_merges_cli_and_mcp_tools():
    import asyncio
    from unittest.mock import patch
    from langchain_core.tools import tool
    import graph.calendar.graph as cal_module

    cal_module._async_graph = None
    cal_module._async_checkpointer_cm = None

    @tool
    def create_event(summary: str) -> str:
        """Create a calendar event."""
        return "ok"

    captured: dict = {}
    original_compile = cal_module.compile_graph

    def capturing_compile(tools, checkpointer):
        captured["tools"] = list(tools)
        return original_compile(tools, checkpointer)

    async def run():
        with patch.object(cal_module, "mcp_manager") as mock_mgr, \
             patch.object(cal_module, "compile_graph", side_effect=capturing_compile):
            mock_mgr.get_tools.return_value = [create_event]
            g = await cal_module.get_async_graph()
            return g, mock_mgr.get_tools.call_args

    graph_obj, call_args = asyncio.run(run())
    assert graph_obj is not None
    assert call_args[0][0] == "calendar"
    tool_names = [t.name for t in captured["tools"]]
    assert "create_event" in tool_names
    assert "today_events" in tool_names


# ── Cycle 7: get_async_graph caches on repeated calls ─────────────────────────

def test_get_async_graph_returns_same_instance_on_repeated_calls():
    import asyncio
    import graph.calendar.graph as cal_module

    cal_module._async_graph = None
    cal_module._async_checkpointer_cm = None

    async def run():
        g1 = await cal_module.get_async_graph()
        g2 = await cal_module.get_async_graph()
        return g1, g2

    g1, g2 = asyncio.run(run())
    assert g1 is g2
