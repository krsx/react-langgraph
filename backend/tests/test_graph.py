import asyncio
import pytest
import sys


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("graph"):
            sys.modules.pop(mod, None)


# ── Cycle 1: AgentState ──────────────────────────────────────────────────────

def test_agent_state_has_all_required_fields():
    from graph.shared.state import AgentState
    import typing

    hints = typing.get_type_hints(AgentState)
    assert "messages" in hints
    assert "customer_id" in hints
    assert "memory_context" in hints
    assert "tool_results" in hints
    assert "verification" in hints


# ── Cycle 2: Graph compiles ──────────────────────────────────────────────────

def test_graph_is_importable():
    from graph.customer_service.graph import graph
    assert graph is not None


# ── Cycle 3: Graph is invocable end-to-end ───────────────────────────────────

@pytest.mark.integration
def test_graph_invoke_returns_agent_state_shaped_dict():
    from graph.customer_service.graph import graph
    from langchain_core.messages import HumanMessage

    result = graph.invoke(
        {"messages": [HumanMessage(content="hello")], "customer_id": 1},
        config={"configurable": {"thread_id": "test-thread-1", "customer_id": 1}, "recursion_limit": 10},
    )

    assert "messages" in result
    assert "customer_id" in result
    assert "memory_context" in result
    assert "tool_results" in result
    assert "verification" in result


def test_compile_graph_supports_async_streaming_with_async_sqlite_saver(monkeypatch, tmp_path):
    import importlib
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    graph_module = importlib.import_module("graph.customer_service.graph")

    monkeypatch.setattr(graph_module, "memory_loader", lambda state: {"memory_context": []})
    monkeypatch.setattr(
        graph_module,
        "planner",
        lambda state, config: {"messages": [AIMessage(content="stubbed response")]},
    )
    monkeypatch.setattr(
        graph_module,
        "verifier",
        lambda state: {
            "verification": {"valid": True, "checks": [], "override_message": None},
            "tool_results": [],
        },
    )
    monkeypatch.setattr(graph_module, "memory_update", lambda state: {})

    async def run_stream():
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / "async-checkpoints.db")) as checkpointer:
            async_graph = graph_module.compile_graph(checkpointer)
            events = []
            async for event in async_graph.astream_events(
                {"messages": [HumanMessage(content="hello")], "customer_id": 1},
                config={"configurable": {"thread_id": "async-test-thread", "customer_id": 1}},
                version="v2",
            ):
                events.append((event["event"], event["name"]))
            return events

    events = asyncio.run(run_stream())

    assert ("on_chain_end", "memory_loader") in events
    assert ("on_chain_end", "planner") in events
    assert ("on_chain_end", "verifier") in events


# ── Cycle 4: tools.py exposes all 5 tool class stubs ────────────────────────

def test_tools_module_exposes_all_five_tools():
    from graph.customer_service import tools

    for name in ("order_lookup", "customer_profile", "refund", "complaint_logger", "memory_tool"):
        assert hasattr(tools, name), f"tools module must expose '{name}'"


def test_all_tools_are_langchain_tools():
    from graph.customer_service.tools import order_lookup, customer_profile, refund, complaint_logger, memory_tool
    from langchain_core.tools import BaseTool

    for t in (order_lookup, customer_profile, refund, complaint_logger, memory_tool):
        assert isinstance(t, BaseTool), f"{t} must be a LangChain BaseTool"
