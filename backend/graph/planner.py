from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from graph.state import AgentState
from graph.tools import order_lookup, customer_profile, refund, complaint_logger, memory_tool
from llm_factory import create_llm

_TOOLS = [order_lookup, customer_profile, refund, complaint_logger, memory_tool]


def build_system_prompt(memory_context: list[dict] | None) -> str:
    lines = [
        "You are a helpful customer service agent.",
        "Think aloud before calling any tool — state your reasoning first, then act.",
    ]

    if memory_context:
        memory_entries = [e for e in memory_context if e.get("type") == "memory"]
        complaint_entries = [e for e in memory_context if e.get("type") == "complaint"]

        if memory_entries:
            lines.append("\nCustomer History:")
            for e in memory_entries:
                lines.append(f"- {e['key']}: {e['value']}")

        if complaint_entries:
            lines.append("\nComplaint History:")
            for e in complaint_entries:
                lines.append(f"- Order {e['order_id']}: {e['issue']} (status: {e['status']})")

    return "\n".join(lines)


def planner(state: AgentState, config: RunnableConfig) -> dict:
    system_prompt = build_system_prompt(state.get("memory_context"))
    llm_with_tools = create_llm().bind_tools(_TOOLS)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages, config=config)
    return {"messages": [response]}