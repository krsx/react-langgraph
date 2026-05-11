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
    from graph.state import AgentState
    import typing

    hints = typing.get_type_hints(AgentState)
    assert "messages" in hints
    assert "customer_id" in hints
    assert "memory_context" in hints
    assert "tool_results" in hints
    assert "verification" in hints


# ── Cycle 2: Graph compiles ──────────────────────────────────────────────────

def test_graph_is_importable():
    from graph.graph import graph
    assert graph is not None


# ── Cycle 3: Graph is invocable end-to-end ───────────────────────────────────

def test_graph_invoke_returns_agent_state_shaped_dict():
    from graph.graph import graph
    from langchain_core.messages import HumanMessage

    result = graph.invoke(
        {"messages": [HumanMessage(content="hello")], "customer_id": 1},
        config={"configurable": {"thread_id": "test-thread-1"}, "recursion_limit": 10},
    )

    assert "messages" in result
    assert "customer_id" in result
    assert "memory_context" in result
    assert "tool_results" in result
    assert "verification" in result


# ── Cycle 4: tools.py exposes all 5 tool class stubs ────────────────────────

def test_tools_module_exposes_all_tools():
    from graph import tools

    # order_lookup and customer_profile are now real @tool functions
    assert hasattr(tools, "order_lookup")
    assert hasattr(tools, "customer_profile")
    # remaining three are still class stubs pending future issues
    assert hasattr(tools, "RefundTool")
    assert hasattr(tools, "ComplaintLoggerTool")
    assert hasattr(tools, "MemoryTool")


def test_tool_stubs_have_docstrings():
    from graph.tools import RefundTool, ComplaintLoggerTool, MemoryTool

    for cls in (RefundTool, ComplaintLoggerTool, MemoryTool):
        assert cls.__doc__, f"{cls.__name__} must have a docstring"


def test_order_lookup_and_customer_profile_are_langchain_tools():
    from graph.tools import order_lookup, customer_profile
    from langchain_core.tools import BaseTool

    assert isinstance(order_lookup, BaseTool)
    assert isinstance(customer_profile, BaseTool)
