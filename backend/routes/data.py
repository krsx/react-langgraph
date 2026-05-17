from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from db.connection import get_connection

router = APIRouter()


class CustomerCreate(BaseModel):
    name: str
    email: str


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class OrderCreate(BaseModel):
    customer_id: int
    product_name: str
    status: str


class OrderUpdate(BaseModel):
    customer_id: Optional[int] = None
    product_name: Optional[str] = None
    status: Optional[str] = None


class ComplaintCreate(BaseModel):
    customer_id: int
    order_id: int
    issue: str
    status: str


class ComplaintUpdate(BaseModel):
    customer_id: Optional[int] = None
    order_id: Optional[int] = None
    issue: Optional[str] = None
    status: Optional[str] = None


@router.get("/customers")
def list_customers():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM customers")
        return cursor.fetchall()
    finally:
        conn.close()


@router.get("/orders")
def list_orders(customer_id: Optional[int] = Query(None)):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if customer_id is not None:
            cursor.execute("SELECT * FROM orders WHERE customer_id = %s", (customer_id,))
        else:
            cursor.execute("SELECT * FROM orders")
        return cursor.fetchall()
    finally:
        conn.close()


@router.get("/complaints")
def list_complaints(customer_id: Optional[int] = Query(None)):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if customer_id is not None:
            cursor.execute("SELECT * FROM complaints WHERE customer_id = %s", (customer_id,))
        else:
            cursor.execute("SELECT * FROM complaints")
        return cursor.fetchall()
    finally:
        conn.close()


@router.post("/customers", status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COALESCE(MAX(customer_id), 0) + 1 AS next_id FROM customers")
        next_id = cursor.fetchone()["next_id"]

        cursor.execute(
            "INSERT INTO customers (customer_id, name, email) VALUES (%s, %s, %s)",
            (next_id, payload.name, payload.email),
        )
        conn.commit()

        cursor.execute(
            "SELECT customer_id, name, email FROM customers WHERE customer_id = %s",
            (next_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@router.put("/customers/{customer_id}")
def update_customer(customer_id: int, payload: CustomerUpdate):
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT customer_id FROM customers WHERE customer_id = %s", (customer_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        set_clause = ", ".join(f"{column} = %s" for column in update_data.keys())
        params = tuple(update_data.values()) + (customer_id,)
        cursor.execute(f"UPDATE customers SET {set_clause} WHERE customer_id = %s", params)
        conn.commit()
        cursor.execute(
            "SELECT customer_id, name, email FROM customers WHERE customer_id = %s",
            (customer_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT customer_id FROM customers WHERE customer_id = %s", (customer_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        cursor.execute("DELETE FROM complaints WHERE customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM orders WHERE customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM customer_memory WHERE customer_id = %s", (customer_id,))
        cursor.execute(
            "DELETE sm FROM session_messages sm "
            "JOIN sessions s ON sm.thread_id = s.thread_id "
            "WHERE s.customer_id = %s",
            (customer_id,),
        )
        cursor.execute("DELETE FROM sessions WHERE customer_id = %s", (customer_id,))
        cursor.execute("DELETE FROM customers WHERE customer_id = %s", (customer_id,))
        conn.commit()
        return {"deleted": True, "customer_id": customer_id}
    finally:
        conn.close()


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COALESCE(MAX(order_id), 0) + 1 AS next_id FROM orders")
        next_id = cursor.fetchone()["next_id"]
        cursor.execute(
            "INSERT INTO orders (order_id, customer_id, product_name, status) VALUES (%s, %s, %s, %s)",
            (next_id, payload.customer_id, payload.product_name, payload.status),
        )
        conn.commit()
        cursor.execute(
            "SELECT order_id, customer_id, product_name, status FROM orders WHERE order_id = %s",
            (next_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@router.put("/orders/{order_id}")
def update_order(order_id: int, payload: OrderUpdate):
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Order not found")

        set_clause = ", ".join(f"{column} = %s" for column in update_data.keys())
        params = tuple(update_data.values()) + (order_id,)
        cursor.execute(f"UPDATE orders SET {set_clause} WHERE order_id = %s", params)
        conn.commit()
        cursor.execute(
            "SELECT order_id, customer_id, product_name, status FROM orders WHERE order_id = %s",
            (order_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@router.delete("/orders/{order_id}")
def delete_order(order_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Order not found")

        cursor.execute("DELETE FROM complaints WHERE order_id = %s", (order_id,))
        cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
        conn.commit()
        return {"deleted": True, "order_id": order_id}
    finally:
        conn.close()


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
def create_complaint(payload: ComplaintCreate):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "INSERT INTO complaints (customer_id, order_id, issue, status) VALUES (%s, %s, %s, %s)",
            (payload.customer_id, payload.order_id, payload.issue, payload.status),
        )
        complaint_id = cursor.lastrowid
        conn.commit()
        cursor.execute(
            "SELECT complaint_id, customer_id, order_id, issue, status "
            "FROM complaints WHERE complaint_id = %s",
            (complaint_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@router.put("/complaints/{complaint_id}")
def update_complaint(complaint_id: int, payload: ComplaintUpdate):
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id FROM complaints WHERE complaint_id = %s", (complaint_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Complaint not found")

        set_clause = ", ".join(f"{column} = %s" for column in update_data.keys())
        params = tuple(update_data.values()) + (complaint_id,)
        cursor.execute(f"UPDATE complaints SET {set_clause} WHERE complaint_id = %s", params)
        conn.commit()
        cursor.execute(
            "SELECT complaint_id, customer_id, order_id, issue, status "
            "FROM complaints WHERE complaint_id = %s",
            (complaint_id,),
        )
        return cursor.fetchone()
    finally:
        conn.close()


@router.delete("/complaints/{complaint_id}")
def delete_complaint(complaint_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT complaint_id FROM complaints WHERE complaint_id = %s", (complaint_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Complaint not found")

        cursor.execute("DELETE FROM complaints WHERE complaint_id = %s", (complaint_id,))
        conn.commit()
        return {"deleted": True, "complaint_id": complaint_id}
    finally:
        conn.close()
