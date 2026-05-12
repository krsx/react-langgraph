import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db.connection import get_connection
from graph.graph import graph

router = APIRouter(prefix="/chat")


class ChatRequest(BaseModel):
    message: str
    customer_id: int
    thread_id: str | None = None
    provider: str | None = None
    model: str | None = None


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _persist_session_start(thread_id: str, customer_id: int, human_message: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO sessions (thread_id, customer_id) VALUES (%s, %s)",
            (thread_id, customer_id),
        )
        cursor.execute(
            "INSERT INTO session_messages (thread_id, role, content) VALUES (%s, %s, %s)",
            (thread_id, "human", human_message),
        )
        conn.commit()
    finally:
        conn.close()


def _persist_ai_message(thread_id: str, content: str) -> None:
    if not content:
        return
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO session_messages (thread_id, role, content) VALUES (%s, %s, %s)",
            (thread_id, "ai", content),
        )
        conn.commit()
    finally:
        conn.close()


async def _event_stream(req: ChatRequest) -> AsyncGenerator[str, None]:
    thread_id = req.thread_id or str(uuid.uuid4())

    input_state = {
        "messages": [{"role": "human", "content": req.message}],
        "customer_id": req.customer_id,
    }
    config = {
        "configurable": {
            "thread_id": thread_id,
            "customer_id": req.customer_id,
            "provider": req.provider,
            "model": req.model,
        }
    }

    response_tokens: list[str] = []

    _persist_session_start(thread_id, req.customer_id, req.message)

    try:
        async for event in graph.astream_events(input_state, config=config, version="v2"):
            name = event.get("name", "")
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chain_end" and name == "memory_loader":
                output = data.get("output") or {}
                yield _sse("memory_loaded", {
                    "thread_id": thread_id,
                    "memory_context": output.get("memory_context", []),
                })

            elif kind == "on_chain_start" and name == "planner":
                yield _sse("planner_start", {"thread_id": thread_id})

            elif kind == "on_chain_end" and name == "planner":
                output = data.get("output") or {}
                messages = output.get("messages", [])
                last = messages[-1] if messages else None
                content = getattr(last, "content", "") if last is not None else ""
                raw_calls = getattr(last, "tool_calls", []) if last is not None else []
                tool_calls = [
                    {"name": tc["name"], "args": tc.get("args", {})}
                    for tc in raw_calls
                ]
                yield _sse("planner_result", {
                    "thread_id": thread_id,
                    "content": content,
                    "tool_calls": tool_calls,
                })

            elif kind == "on_chain_start" and name == "tools":
                yield _sse("tool_start", {"thread_id": thread_id})

            elif kind == "on_chain_end" and name == "tools":
                output = data.get("output") or {}
                yield _sse("tool_result", {
                    "thread_id": thread_id,
                    "results": str(output),
                })

            elif kind == "on_chain_end" and name == "verifier":
                output = data.get("output") or {}
                verification = output.get("verification") or {}
                yield _sse("verifier_result", {
                    "thread_id": thread_id,
                    "valid": verification.get("valid"),
                    "checks": verification.get("checks", []),
                    "override_message": verification.get("override_message"),
                })

            elif kind == "on_chain_end" and name == "memory_update":
                yield _sse("memory_updated", {"thread_id": thread_id})

            elif kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                token = getattr(chunk, "content", "") if chunk is not None else ""
                if token:
                    response_tokens.append(token)
                    yield _sse("response_token", {"thread_id": thread_id, "token": token})

        ai_response = "".join(response_tokens)
        _persist_ai_message(thread_id, ai_response)
        yield _sse("response_end", {
            "thread_id": thread_id,
            "response": ai_response,
        })

    except Exception as exc:
        yield _sse("error", {"thread_id": thread_id, "error": str(exc)})


@router.post("/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
