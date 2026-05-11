from db.connection import get_connection
from graph.state import AgentState


def memory_loader(state: AgentState) -> dict:
    customer_id = state.get("customer_id")

    if customer_id is None:
        return {"memory_context": [], "tool_results": None, "verification": None}

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT `key`, value FROM customer_memory WHERE customer_id = %s",
            (customer_id,),
        )
        memory_entries = [
            {"type": "memory", "key": r["key"], "value": r["value"]}
            for r in cursor.fetchall()
        ]

        cursor.execute(
            "SELECT order_id, issue, status, created_at FROM complaints WHERE customer_id = %s",
            (customer_id,),
        )
        complaint_entries = [
            {"type": "complaint", "order_id": r["order_id"], "issue": r["issue"],
             "status": r["status"], "created_at": str(r["created_at"])}
            for r in cursor.fetchall()
        ]

        return {
            "memory_context": memory_entries + complaint_entries,
            "tool_results": None,
            "verification": None,
        }
    finally:
        conn.close()
