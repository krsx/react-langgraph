import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator

from config import get_config
from db.connection import get_connection
from graph.router import get_async_graph as _get_async_graph

router = APIRouter(prefix="/chat")

_WORKSPACE_AGENT_TYPES = {"refund_email", "calendar"}
_ALL_AGENT_TYPES = {"customer_service"} | _WORKSPACE_AGENT_TYPES


class ChatRequest(BaseModel):
    message: str
    customer_id: int | None = None
    agent_type: str = "customer_service"
    thread_id: str | None = None
    provider: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def validate_agent_type_and_customer_id(self) -> "ChatRequest":
        if self.agent_type not in _ALL_AGENT_TYPES:
            raise ValueError(f"Unknown agent_type '{self.agent_type}'. Must be one of: {sorted(_ALL_AGENT_TYPES)}")
        if self.agent_type == "customer_service" and self.customer_id is None:
            raise ValueError("customer_id is required for agent_type 'customer_service'")
        if self.agent_type in _WORKSPACE_AGENT_TYPES and self.customer_id is not None:
            raise ValueError(f"customer_id must not be provided for workspace agent_type '{self.agent_type}'")
        return self


def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _normalize_tool_result(value: object) -> object:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"raw": value}
    if isinstance(value, (dict, list, bool, int, float)) or value is None:
        return value
    return {"raw": str(value)}


def _build_tool_result_payloads(thread_id: str, output: object) -> list[dict]:
    if not isinstance(output, dict):
        return [{"thread_id": thread_id, "tool_name": "tool", "results": _normalize_tool_result(output)}]

    messages = output.get("messages")
    if not isinstance(messages, list) or len(messages) == 0:
        return [{"thread_id": thread_id, "tool_name": "tool", "results": _normalize_tool_result(output)}]

    payloads: list[dict] = []
    for message in messages:
        payloads.append({
            "thread_id": thread_id,
            "tool_name": getattr(message, "name", "tool"),
            "results": _normalize_tool_result(getattr(message, "content", None)),
        })

    return payloads


def _persist_session_start(thread_id: str, customer_id: int | None, human_message: str, agent_type: str) -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO sessions (thread_id, customer_id, agent_type) VALUES (%s, %s, %s)",
            (thread_id, customer_id, agent_type),
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
    cfg = get_config()
    provider = req.provider or "openrouter"
    model = req.model or (cfg.OLLAMA_DEFAULT_MODEL if provider == "ollama" else cfg.DEFAULT_MODEL)

    input_state = {
        "messages": [{"role": "human", "content": req.message}],
        "customer_id": req.customer_id,
    }
    config = {
        "configurable": {
            "thread_id": thread_id,
            "customer_id": req.customer_id,
            "provider": provider,
            "model": model,
        }
    }

    response_tokens: list[str] = []

    _persist_session_start(thread_id, req.customer_id, req.message, req.agent_type)

    try:
        graph = await _get_async_graph(req.agent_type)
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
                for payload in _build_tool_result_payloads(thread_id, output):
                    yield _sse("tool_result", payload)

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
                output = data.get("output") or {}
                key = output.get("key") if isinstance(output, dict) else None
                value = output.get("value") if isinstance(output, dict) else None
                yield _sse("memory_updated", {
                    "thread_id": thread_id,
                    "key": key if isinstance(key, str) else "",
                    "value": value if isinstance(value, str) else "",
                })

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
