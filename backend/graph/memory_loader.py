from graph.state import AgentState


def memory_loader(state: AgentState) -> dict:
    return {
        "memory_context": None,
        "tool_results": None,
        "verification": None,
    }
