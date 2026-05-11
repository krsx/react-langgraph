from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from db.connection import get_connection


@tool
def order_lookup(order_id: int, config: RunnableConfig) -> dict:
    """Look up order details for the current customer by order ID."""
    customer_id = config["configurable"]["customer_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT order_id, customer_id, product_name, status, order_date, delivery_date "
            "FROM orders WHERE order_id = %s AND customer_id = %s",
            (order_id, customer_id),
        )
        row = cursor.fetchone()
        if row is None:
            return {"error": f"Order {order_id} not found or not accessible."}
        return dict(row)
    finally:
        conn.close()


@tool
def customer_profile(config: RunnableConfig) -> dict:
    """Retrieve the current customer's profile."""
    customer_id = config["configurable"]["customer_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT customer_id, name, email, created_at "
            "FROM customers WHERE customer_id = %s",
            (customer_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return {"error": f"Customer {customer_id} not found."}
        return dict(row)
    finally:
        conn.close()


class RefundTool:
    """Validates and initiates a refund: SELECT status FROM orders WHERE order_id = ? AND customer_id = ?, then UPDATE orders SET status = 'refund_requested' WHERE order_id = ? AND customer_id = ? (only if status = 'delivered')"""


class ComplaintLoggerTool:
    """Logs a complaint: INSERT INTO complaints (customer_id, order_id, issue, status) VALUES (?, ?, ?, 'open')"""


class MemoryTool:
    """Reads or writes long-term memory: SELECT key, value FROM customer_memory WHERE customer_id = ? / INSERT INTO customer_memory (customer_id, key, value) VALUES (?, ?, ?)"""