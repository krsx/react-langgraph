import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from graph.state import AgentState
from graph.memory_loader import memory_loader
from graph.planner import planner
from graph.tools import order_lookup, customer_profile, refund, complaint_logger, memory_tool
from graph.verifier import verifier
from graph.memory_update import memory_update

builder = StateGraph(AgentState)

builder.add_node("memory_loader", memory_loader)
builder.add_node("planner", planner)
builder.add_node("tools", ToolNode([order_lookup, customer_profile, refund, complaint_logger, memory_tool]))
builder.add_node("verifier", verifier)
builder.add_node("memory_update", memory_update)

builder.set_entry_point("memory_loader")
builder.add_edge("memory_loader", "planner")
builder.add_conditional_edges("planner", tools_condition, {"tools": "tools", END: "verifier"})
builder.add_edge("tools", "planner")
builder.add_edge("verifier", "memory_update")
builder.add_edge("memory_update", END)

_conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
_checkpointer = SqliteSaver(_conn)

graph = builder.compile(checkpointer=_checkpointer)

RECURSION_LIMIT = 10
