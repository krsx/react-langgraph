import sqlite3
from contextlib import AbstractAsyncContextManager

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from graph.shared.state import AgentState
from graph.customer_service.memory_loader import memory_loader
from graph.customer_service.planner import planner
from graph.customer_service.tools import (
    order_lookup,
    customer_profile,
    refund,
    complaint_logger,
    memory_tool,
)
from graph.shared.verifier import verifier
from graph.customer_service.memory_update import memory_update

CHECKPOINT_DB_PATH = "checkpoints.db"
RECURSION_LIMIT = 10

_TOOLS = [order_lookup, customer_profile, refund, complaint_logger, memory_tool]

_conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
_checkpointer = SqliteSaver(_conn)
_async_checkpointer_cm: AbstractAsyncContextManager[AsyncSqliteSaver] | None = None
_async_graph = None


def create_builder() -> StateGraph:
    builder = StateGraph(AgentState)
    builder.add_node("memory_loader", memory_loader)
    builder.add_node("planner", planner)
    builder.add_node("tools", ToolNode(_TOOLS))
    builder.add_node("verifier", verifier)
    builder.add_node("memory_update", memory_update)

    builder.set_entry_point("memory_loader")
    builder.add_edge("memory_loader", "planner")
    builder.add_conditional_edges(
        "planner", tools_condition, {"tools": "tools", END: "verifier"}
    )
    builder.add_edge("tools", "planner")
    builder.add_edge("verifier", "memory_update")
    builder.add_edge("memory_update", END)
    return builder


def compile_graph(checkpointer):
    return (
        create_builder()
        .compile(checkpointer=checkpointer)
        .with_config({"recursion_limit": RECURSION_LIMIT})
    )


builder = create_builder()
graph = compile_graph(_checkpointer)


async def get_async_graph():
    global _async_checkpointer_cm, _async_graph

    if _async_graph is None:
        _async_checkpointer_cm = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
        checkpointer = await _async_checkpointer_cm.__aenter__()
        _async_graph = compile_graph(checkpointer)

    return _async_graph


async def close_async_graph() -> None:
    global _async_checkpointer_cm, _async_graph

    if _async_checkpointer_cm is not None:
        await _async_checkpointer_cm.__aexit__(None, None, None)
        _async_checkpointer_cm = None
        _async_graph = None
