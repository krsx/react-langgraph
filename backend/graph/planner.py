from langchain_core.messages import AIMessage
from graph.state import AgentState


def planner(state: AgentState) -> dict:
    return {"messages": [AIMessage(content="stub")]}
