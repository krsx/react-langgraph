import sqlite3
from contextlib import AbstractAsyncContextManager

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from graph.shared.state import AgentState
from graph.shared.verifier import verifier
from graph.calendar.planner import make_planner
from graph.calendar.cli_tools import (
    today_events,
    list_events,
    list_calendars,
    get_event,
    tool_list,
)
from graph.mcp_client import mcp_manager

CHECKPOINT_DB_PATH = "checkpoints_calendar.db"
RECURSION_LIMIT = 50

CLI_TOOLS = [today_events, list_events, list_calendars, get_event, tool_list]

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
        mcp_tools = mcp_manager.get_tools("calendar")
        if not mcp_tools:
            raise RuntimeError(
                "Calendar MCP tools are not available. "
                "Ensure the workspace MCP service is running before accessing the calendar graph."
            )
        cli_names = {t.name for t in CLI_TOOLS}
        tools = CLI_TOOLS + [t for t in mcp_tools if t.name not in cli_names]

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
