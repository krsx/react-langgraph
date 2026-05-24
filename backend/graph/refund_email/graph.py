import sqlite3
from contextlib import AbstractAsyncContextManager

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from graph.shared.state import AgentState
from graph.shared.verifier import verifier
from graph.refund_email.planner import make_planner

CHECKPOINT_DB_PATH = "checkpoints_refund_email.db"
# Batch refund processing can legitimately loop across multiple emails.
# Keep enough headroom for search + read/send cycles without masking infinite loops.
RECURSION_LIMIT = 50

_async_checkpointer_cm: AbstractAsyncContextManager[AsyncSqliteSaver] | None = None
_async_graph = None


def create_builder(tools: list) -> StateGraph:
    builder = StateGraph(AgentState)
    builder.add_node("planner", make_planner(tools))
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("verifier", verifier)

    builder.set_entry_point("planner")
    builder.add_conditional_edges(
        "planner", tools_condition, {"tools": "tools", END: "verifier"}
    )
    builder.add_edge("tools", "planner")
    builder.add_edge("verifier", END)
    return builder


def compile_graph(tools: list, checkpointer):
    return (
        create_builder(tools)
        .compile(checkpointer=checkpointer)
        .with_config({"recursion_limit": RECURSION_LIMIT})
    )


async def get_async_graph():
    global _async_checkpointer_cm, _async_graph

    if _async_graph is None:
        from graph.mcp_client import mcp_manager
        tools = mcp_manager.get_tools("refund_email")

        _async_checkpointer_cm = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
        checkpointer = await _async_checkpointer_cm.__aenter__()
        _async_graph = compile_graph(tools, checkpointer)

    return _async_graph


async def close_async_graph() -> None:
    global _async_checkpointer_cm, _async_graph

    if _async_checkpointer_cm is not None:
        await _async_checkpointer_cm.__aexit__(None, None, None)
        _async_checkpointer_cm = None
        _async_graph = None
