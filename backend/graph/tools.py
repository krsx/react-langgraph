from graph.state import AgentState


def tool_node(state: AgentState) -> dict:
    return {"tool_results": []}


class OrderLookupTool:
    """Retrieves order details for a customer: SELECT * FROM orders WHERE order_id = ? AND customer_id = ?"""


class CustomerProfileTool:
    """Retrieves customer profile information: SELECT * FROM customers WHERE customer_id = ?"""


class RefundTool:
    """Initiates a refund for a delivered order: UPDATE orders SET status = 'refund_requested' WHERE order_id = ? AND customer_id = ?"""


class ComplaintLoggerTool:
    """Logs a complaint against an order: INSERT INTO complaints (customer_id, order_id, issue, status) VALUES (?, ?, ?, 'open')"""


class MemoryTool:
    """Reads or writes long-term customer memory: SELECT key, value FROM customer_memory WHERE customer_id = ? / INSERT INTO customer_memory (customer_id, key, value) VALUES (?, ?, ?)"""
