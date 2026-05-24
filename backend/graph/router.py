import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from graph.customer_service.graph import graph as _cs_graph, get_async_graph as _cs_get_async_graph
from graph.refund_email.graph import compile_graph as _re_compile_graph, get_async_graph as _re_get_async_graph
from graph.calendar.graph import compile_graph as _cal_compile_graph, get_async_graph as _cal_get_async_graph, CLI_TOOLS as _cal_cli_tools
from graph.mcp_client import mcp_manager

_VALID_TYPES = ["customer_service", "refund_email", "calendar"]

_re_conn = None
_re_graph = None
_cal_conn = None
_cal_graph = None


def _get_refund_email_graph():
    global _re_conn, _re_graph

    if _re_graph is None:
        _re_conn = sqlite3.connect("checkpoints_refund_email.db", check_same_thread=False)
        _re_graph = _re_compile_graph(
            mcp_manager.get_tools("refund_email"),
            SqliteSaver(_re_conn),
        )
    return _re_graph


def _get_calendar_graph():
    global _cal_conn, _cal_graph

    if _cal_graph is None:
        mcp_tools = mcp_manager.get_tools("calendar")
        if not mcp_tools:
            raise RuntimeError(
                "Calendar MCP tools are not available. "
                "Ensure the workspace MCP service is running before accessing the calendar graph."
            )
        _cal_conn = sqlite3.connect("checkpoints_calendar.db", check_same_thread=False)
        _cal_graph = _cal_compile_graph(_cal_cli_tools + mcp_tools, SqliteSaver(_cal_conn))

    return _cal_graph


def get_graph(agent_type: str):
    if agent_type == "customer_service":
        return _cs_graph
    if agent_type == "refund_email":
        return _get_refund_email_graph()
    if agent_type == "calendar":
        return _get_calendar_graph()
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: {_VALID_TYPES}")


async def get_async_graph(agent_type: str):
    if agent_type == "customer_service":
        return await _cs_get_async_graph()
    if agent_type == "refund_email":
        return await _re_get_async_graph()
    if agent_type == "calendar":
        return await _cal_get_async_graph()
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: {_VALID_TYPES}")
