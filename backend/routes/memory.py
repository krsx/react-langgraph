from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.connection import get_connection

router = APIRouter(prefix="/memory")


class MemoryEntry(BaseModel):
    key: str
    value: str


@router.get("/{customer_id}")
def get_memory(customer_id: int):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT `key`, value, created_at FROM customer_memory WHERE customer_id = %s",
            (customer_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


@router.put("/{customer_id}")
def upsert_memory(customer_id: int, entries: list[MemoryEntry]):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for entry in entries:
            cursor.execute(
                "INSERT INTO customer_memory (customer_id, `key`, value) VALUES (%s, %s, %s)"
                " ON DUPLICATE KEY UPDATE value = VALUES(value)",
                (customer_id, entry.key, entry.value),
            )
        conn.commit()
        return {"updated": len(entries)}
    finally:
        conn.close()


@router.delete("/{customer_id}/{key}")
def delete_memory(customer_id: int, key: str):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM customer_memory WHERE customer_id = %s AND `key` = %s",
            (customer_id, key),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Memory entry not found")
        return {"deleted": True}
    finally:
        conn.close()
