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


@tool
def refund(order_id: int, config: RunnableConfig) -> dict:
    """Initiate a refund for a delivered order. Only succeeds if order belongs to the customer and has status 'delivered'."""
    customer_id = config["configurable"]["customer_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT customer_id, status FROM orders WHERE order_id = %s",
            (order_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return {"error": f"Order {order_id} not found."}
        if row["customer_id"] != customer_id:
            return {"error": f"Order {order_id} does not belong to this customer."}
        if row["status"] != "delivered":
            return {
                "error": f"Order {order_id} is not eligible for refund (status: {row['status']})."
            }
        cursor.execute(
            "UPDATE orders SET status = 'refund_requested' WHERE order_id = %s AND customer_id = %s",
            (order_id, customer_id),
        )
        conn.commit()
        return {"success": True, "order_id": order_id, "status": "refund_requested"}
    finally:
        conn.close()


@tool
def complaint_logger(order_id: int, issue: str, config: RunnableConfig) -> dict:
    """Log a complaint about an order. IMPORTANT: always call order_lookup first to verify the order exists and belongs to the customer before asking the user for the issue description. Only succeeds if the order belongs to the current customer. Returns the new complaint ID."""
    customer_id = config["configurable"]["customer_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT customer_id FROM orders WHERE order_id = %s",
            (order_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return {"error": f"Order {order_id} not found."}
        if row["customer_id"] != customer_id:
            return {"error": f"Order {order_id} does not belong to this customer."}
        cursor.execute(
            "INSERT INTO complaints (customer_id, order_id, issue, status) VALUES (%s, %s, %s, 'open')",
            (customer_id, order_id, issue),
        )
        conn.commit()
        return {"success": True, "complaint_id": cursor.lastrowid}
    finally:
        conn.close()


@tool
def memory_tool(
    action: str, config: RunnableConfig, key: str = None, value: str = None
) -> dict:
    """Read or write long-term customer memory. action='read' retrieves entries (optionally filtered by key). action='write' upserts a key-value pair."""
    customer_id = config["configurable"]["customer_id"]
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if action == "read":
            if key:
                cursor.execute(
                    "SELECT `key`, value FROM customer_memory WHERE customer_id = %s AND `key` = %s",
                    (customer_id, key),
                )
            else:
                cursor.execute(
                    "SELECT `key`, value FROM customer_memory WHERE customer_id = %s",
                    (customer_id,),
                )
            return {"memories": [dict(r) for r in cursor.fetchall()]}
        elif action == "write":
            cursor.execute(
                "INSERT INTO customer_memory (customer_id, `key`, value) VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE value = %s",
                (customer_id, key, value, value),
            )
            conn.commit()
            return {"success": True}
        else:
            return {"error": f"Unknown action: {action}"}
    finally:
        conn.close()
