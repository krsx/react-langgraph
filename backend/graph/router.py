import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from graph.customer_service.graph import graph as _cs_graph, get_async_graph as _cs_get_async_graph
from graph.refund_email.graph import compile_graph as _re_compile_graph, get_async_graph as _re_get_async_graph

_VALID_TYPES = ["customer_service", "refund_email", "calendar"]

_re_conn = sqlite3.connect("checkpoints_refund_email.db", check_same_thread=False)
_re_graph = _re_compile_graph([], SqliteSaver(_re_conn))


def get_graph(agent_type: str):
    if agent_type == "customer_service":
        return _cs_graph
    if agent_type == "refund_email":
        return _re_graph
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: {_VALID_TYPES}")


async def get_async_graph(agent_type: str):
    if agent_type == "customer_service":
        return await _cs_get_async_graph()
    if agent_type == "refund_email":
        return await _re_get_async_graph()
    raise ValueError(f"Unknown agent_type '{agent_type}'. Must be one of: {_VALID_TYPES}")
