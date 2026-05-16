from datetime import datetime, timezone
from langchain_core.messages import HumanMessage, ToolMessage

from db.connection import get_connection
from graph.state import AgentState


def memory_update(state: AgentState) -> dict:
    customer_id = state.get("customer_id")
    if not customer_id:
        return {}

    messages = state.get("messages") or []
    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not human_messages:
        return {}

    last_human = human_messages[-1].content
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    tool_names = "none"
    tool_summary = "none"
    if tool_messages:
        tool_names = ", ".join(getattr(m, "name", "tool") for m in tool_messages)
        tool_summary = str([m.content for m in tool_messages])[:200]

    timestamp = datetime.now(timezone.utc).isoformat()
    summary = f"[{timestamp}] User: {last_human} | Tools used: {tool_names} | Outcome: {tool_summary}"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO customer_memory (customer_id, `key`, value) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE value = %s",
            (customer_id, "last_interaction_summary", summary, summary),
        )
        conn.commit()
    finally:
        conn.close()

    return {"key": "last_interaction_summary", "value": summary}
