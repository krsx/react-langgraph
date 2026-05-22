import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from graph.customer_service.graph import graph as _cs_graph, get_async_graph as _cs_get_async_graph
from graph.refund_email.graph import compile_graph as _re_compile_graph, get_async_graph as _re_get_async_graph
from graph.calendar.graph import compile_graph as _cal_compile_graph, get_async_graph as _cal_get_async_graph, CLI_TOOLS as _cal_cli_tools

_VALID_TYPES = ["customer_service", "refund_email", "calendar"]

_re_conn = sqlite3.connect("checkpoints_refund_email.db", check_same_thread=False)
_re_graph = _re_compile_graph([], SqliteSaver(_re_conn))

_cal_conn = sqlite3.connect("checkpoints_calendar.db", check_same_thread=False)
_cal_graph = _cal_compile_graph(_cal_cli_tools, SqliteSaver(_cal_conn))


def get_graph(agent_type: str):
    if agent_type == "customer_service":
        return _cs_graph
    if agent_type == "refund_email":
        return _re_graph
    if agent_type == "calendar":
        return _cal_graph
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: {_VALID_TYPES}")


async def get_async_graph(agent_type: str):
    if agent_type == "customer_service":
        return await _cs_get_async_graph()
    if agent_type == "refund_email":
        return await _re_get_async_graph()
    if agent_type == "calendar":
        return await _cal_get_async_graph()
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: {_VALID_TYPES}")
