from typing import Optional

from fastapi import APIRouter, Query

from db.connection import get_connection

router = APIRouter()


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
