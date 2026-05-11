from datetime import datetime, timezone
from langchain_core.messages import HumanMessage

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
    tool_results = state.get("tool_results")
    tool_names = "none"
    tool_summary = "none"
    if tool_results:
        tool_names = ", ".join(
            str(r.get("tool", r.get("order_id", "tool"))) for r in tool_results
        )
        tool_summary = str(tool_results)[:200]

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

    return {}