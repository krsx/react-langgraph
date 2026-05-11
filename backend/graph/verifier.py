import json
from langchain_core.messages import AIMessage, ToolMessage

from graph.state import AgentState


def verifier(state: AgentState) -> dict:
    messages = state.get("messages") or []

    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    if not tool_messages:
        return {"verification": {"valid": True, "checks": ["no tool calls"], "override_message": None}}

    errors = []
    for tm in tool_messages:
        try:
            content = json.loads(tm.content) if isinstance(tm.content, str) else tm.content
            if isinstance(content, dict) and "error" in content:
                errors.append(content["error"])
        except (json.JSONDecodeError, TypeError):
            pass

    if not errors:
        return {"verification": {"valid": True, "checks": ["all checks passed"], "override_message": None}}

    last_ai = next(
        (m for m in reversed(messages) if isinstance(m, AIMessage)),
        None,
    )
    ai_content = (last_ai.content or "").lower() if last_ai else ""

    error_keywords = ["not found", "error", "cannot", "could not", "unable", "invalid", "not exist", "not accessible"]
    llm_acknowledged = any(kw in ai_content for kw in error_keywords)

    override = None if llm_acknowledged else f"I could not complete that request: {errors[0]}"

    return {
        "verification": {
            "valid": False,
            "checks": [f"tool error: {e}" for e in errors],
            "override_message": override,
        }
    }