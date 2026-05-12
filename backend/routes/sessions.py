from fastapi import APIRouter, HTTPException

from db.connection import get_connection

router = APIRouter(prefix="/sessions")


@router.get("")
def list_sessions():
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT s.thread_id, s.customer_id, s.created_at,
                   (SELECT content FROM session_messages
                    WHERE thread_id = s.thread_id AND role = 'human'
                    ORDER BY created_at ASC LIMIT 1) AS first_message
            FROM sessions s
            ORDER BY s.created_at DESC
            """
        )
        return cursor.fetchall()
    finally:
        conn.close()


@router.get("/{session_id}")
def get_session(session_id: str):
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT thread_id FROM sessions WHERE thread_id = %s", (session_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Session not found")
        cursor.execute(
            """
            SELECT message_id, role, content, created_at
            FROM session_messages
            WHERE thread_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()
