"""
Integration test suite — Workspace Agents (Refund Email + Calendar).

Requires: OPENROUTER_API_KEY env var, live LLM.
Session-persistence tests (RE-05, Cal-10, Cross-12) also require MySQL
(docker compose up mysql) and are skipped automatically when unreachable.

Run:
    uv run pytest tests/integration/test_workspace_agents.py -m integration -v
"""

import asyncio
import json
import sqlite3
import uuid
import pytest
import openai
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, AIMessage

from tests.integration.conftest import (
    handle_rate_limit,
    MOCK_GMAIL_TOOLS,
    MOCK_CALENDAR_CLI_TOOLS,
    MOCK_CALENDAR_MCP_TOOLS,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def ws_invoke(graph, message: str, thread_id: str) -> dict:
    """Invoke a workspace agent graph without a customer_id."""
    try:
        return graph.invoke(
            {"messages": [HumanMessage(content=message)], "customer_id": None},
            config={"configurable": {"thread_id": thread_id}},
        )
    except openai.RateLimitError as exc:
        handle_rate_limit(exc)


def tool_names_used(messages: list) -> set[str]:
    """Return the set of tool names the planner called (from AIMessage.tool_calls)."""
    names: set[str] = set()
    for m in messages:
        if isinstance(m, AIMessage):
            for tc in getattr(m, "tool_calls", []) or []:
                name = (
                    tc.get("name")
                    if isinstance(tc, dict)
                    else getattr(tc, "name", None)
                )
                if name:
                    names.add(name)
    return names


def last_ai_content(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content.lower()
    return ""


def parse_sse(text: str) -> list[dict]:
    events = []
    current: dict = {}
    for line in text.splitlines():
        if line.startswith("event:"):
            current["event"] = line[len("event:") :].strip()
        elif line.startswith("data:"):
            raw = line[len("data:") :].strip()
            try:
                current["data"] = json.loads(raw)
            except json.JSONDecodeError:
                current["data"] = raw
        elif line == "" and current:
            events.append(current)
            current = {}
    if current:
        events.append(current)
    return events


def planner_tool_names_from_events(events: list[dict]) -> set[str]:
    names: set[str] = set()
    for event in events:
        if event.get("event") != "planner_result":
            continue
        data = event.get("data", {})
        for tool_call in data.get("tool_calls", []):
            name = tool_call.get("name")
            if name:
                names.add(name)
    return names


def response_text_from_events(events: list[dict]) -> str:
    for event in reversed(events):
        if event.get("event") == "response_end":
            data = event.get("data", {})
            return str(data.get("response", "")).lower()
    return ""


def _maybe_skip_rate_limit(message: str) -> None:
    lowered = message.lower()
    if "per-day" in lowered or "per_day" in lowered or "per day" in lowered:
        pytest.skip(f"OpenRouter daily quota exhausted — rerun tomorrow: {message}")


async def stream_workspace_request(
    graph_by_agent_type: dict[str, object],
    *,
    message: str,
    agent_type: str,
    thread_id: str,
) -> list[dict]:
    async def _get_graph(requested_agent_type: str):
        graph = graph_by_agent_type.get(requested_agent_type)
        if graph is None:
            raise ValueError(f"Unexpected test agent_type {requested_agent_type!r}")
        return graph

    from routes.chat import ChatRequest, _event_stream

    req = ChatRequest(
        message=message,
        agent_type=agent_type,
        thread_id=thread_id,
    )

    chunks: list[str] = []
    with patch("routes.chat._get_async_graph", new=_get_graph):
        async for chunk in _event_stream(req):
            chunks.append(chunk)

    events = parse_sse("".join(chunks))
    for event in events:
        if event.get("event") != "error":
            continue
        data = event.get("data", {})
        error = str(data.get("error", "unknown error"))
        _maybe_skip_rate_limit(error)
        raise AssertionError(f"/chat/stream returned error event: {error}")
    return events


def get_session_via_api(thread_id: str) -> dict:
    from main import app

    client = TestClient(app)
    resp = client.get(f"/sessions/{thread_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


def make_mock_llm(*responses: AIMessage) -> MagicMock:
    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = list(responses)
    return mock_llm


# ── Refund Email Agent — 5 cases ──────────────────────────────────────────────


@pytest.mark.integration
def test_refund_01_interactive_query_triggers_search_gmail(
    refund_email_graph, ws_thread
):
    """'What refund emails came in today?' -> search_gmail tool called; summary returned."""
    result = ws_invoke(
        refund_email_graph, "What refund emails came in today?", ws_thread
    )

    assert "messages" in result
    used = tool_names_used(result["messages"])
    assert (
        "search_gmail" in used
    ), f"Expected search_gmail to be called for an inbox query. Tools used: {used}"
    content = last_ai_content(result["messages"])
    assert len(content) > 0, "Expected a non-empty summary in the last AI message"


@pytest.mark.integration
def test_refund_02_batch_processing_triggers_full_6_step_workflow(
    refund_email_graph, ws_thread
):
    """'Process all refund emails' -> full SEARCH → READ → CLASSIFY → DRAFT → SEND → REPORT workflow."""
    result = ws_invoke(
        refund_email_graph,
        "Process all unread refund emails in my inbox",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    # SEARCH step
    assert (
        "search_gmail" in used
    ), f"Expected search_gmail in batch workflow (SEARCH step). Tools used: {used}"
    # READ step
    assert (
        "get_message" in used
    ), f"Expected get_message in batch workflow (READ step). Tools used: {used}"
    # SEND step
    assert (
        "send_reply" in used
    ), f"Expected send_reply in batch workflow (SEND step). Tools used: {used}"

    # CLASSIFY step — the AI messages must mention classification labels before sending
    all_ai_content = " ".join(
        m.content.lower()
        for m in result["messages"]
        if isinstance(m, AIMessage) and m.content
    )
    classify_keywords = ("refund_request", "return_request", "complaint", "other")
    assert any(
        kw in all_ai_content for kw in classify_keywords
    ), (
        f"Expected at least one classification label ({classify_keywords}) in AI reasoning "
        f"during the CLASSIFY step. AI content snippet: {all_ai_content[:500]}"
    )

    # REPORT step — the final response must contain a summary with counts or actions taken
    final_content = last_ai_content(result["messages"])
    report_keywords = (
        "processed", "emails", "sent", "replied", "classified",
        "summary", "report", "total", "found",
    )
    assert any(
        kw in final_content for kw in report_keywords
    ), (
        f"Expected a REPORT summary in the final response (keywords: {report_keywords}). "
        f"Got: {final_content[:300]}"
    )


_VALID_CATEGORIES = ("refund_request", "return_request", "complaint", "other")


@pytest.mark.integration
@pytest.mark.parametrize(
    "email_body,expected_category",
    [
        (
            "Hi, I received order #1234 and the item arrived completely broken. "
            "I want a full refund immediately. This is unacceptable.",
            "refund_request",
        ),
        (
            "Hello, I would like to return the shoes I ordered last week. "
            "They don't fit and I need a different size or my money back.",
            "return_request",
        ),
        (
            "Your service has been terrible lately. Deliveries are always late "
            "and your support team never responds. I'm very disappointed.",
            "complaint",
        ),
        (
            "Hi, can you tell me what your store hours are this weekend? "
            "I'd like to come in and browse your new collection.",
            "other",
        ),
    ],
    ids=["refund_request", "return_request", "complaint", "other"],
)
def test_refund_03_email_classification_identifies_correct_category(
    refund_email_graph, ws_thread, email_body, expected_category
):
    """Agent classifies each email body -> response contains the specific correct category label."""
    message = f"Classify this customer email: '{email_body}'"
    result = ws_invoke(refund_email_graph, message, ws_thread)

    content = last_ai_content(result["messages"])
    assert expected_category in content, (
        f"Expected category '{expected_category}' in response. Got: {content[:300]}"
    )


@pytest.mark.integration
def test_refund_04_verifier_catches_gmail_permission_denied(
    refund_email_error_graph, ws_thread
):
    """Gmail search returns permission-denied -> verifier marks valid=False."""
    result = ws_invoke(
        refund_email_error_graph,
        "What refund emails came in today?",
        ws_thread,
    )

    assert result["verification"] is not None, "verification field must be populated"
    assert result["verification"]["valid"] is False, (
        f"Verifier should reject permission-denied error. "
        f"verification={result['verification']}"
    )


def _try_db_connection():
    """Return a live DB connection or skip the test if MySQL is unreachable."""
    try:
        from db.connection import get_connection

        conn = get_connection()
        conn.ping(reconnect=False)
        return conn
    except Exception as exc:
        pytest.skip(f"MySQL not reachable — skipping session-persistence check: {exc}")


def cleanup_sessions(*thread_ids: str) -> None:
    conn = _try_db_connection()
    try:
        clean = conn.cursor()
        for thread_id in thread_ids:
            clean.execute(
                "DELETE FROM session_messages WHERE thread_id = %s", (thread_id,)
            )
            clean.execute("DELETE FROM sessions WHERE thread_id = %s", (thread_id,))
        conn.commit()
    finally:
        conn.close()


@pytest.mark.integration
def test_refund_05_session_persists_with_agent_type_and_null_customer_id(
    ws_thread, tmp_path
):
    """Refund Email runs without customer_id; session row carries agent_type='refund_email' and customer_id=NULL."""
    preflight = _try_db_connection()
    preflight.close()

    async def _run():
        from graph.refund_email.graph import compile_graph
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / "refund-route.db")
        ) as checkpointer:
            graph = compile_graph(MOCK_GMAIL_TOOLS, checkpointer)
            return await stream_workspace_request(
                {"refund_email": graph},
                message="Are there any refund requests in my inbox today?",
                agent_type="refund_email",
                thread_id=ws_thread,
            )

    events = asyncio.run(_run())
    used = planner_tool_names_from_events(events)
    assert (
        "search_gmail" in used
    ), f"Expected /chat/stream Refund Email path to call search_gmail. Tools used: {used}"
    response = response_text_from_events(events)
    assert len(response) > 0, "Expected a streamed AI response from /chat/stream"

    conn = None
    try:
        session_payload = get_session_via_api(ws_thread)
        assert session_payload["session"]["agent_type"] == "refund_email"
        assert session_payload["session"]["customer_id"] is None
        assert [msg["role"] for msg in session_payload["messages"][:2]] == ["human", "ai"]
        assert (
            session_payload["messages"][0]["content"]
            == "Are there any refund requests in my inbox today?"
        )

        conn = _try_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT agent_type, customer_id FROM sessions WHERE thread_id = %s",
            (ws_thread,),
        )
        row = cursor.fetchone()
    finally:
        cleanup_sessions(ws_thread)
        try:
            conn.close()
        except Exception:
            pass

    assert row is not None, f"Session row not found for thread_id={ws_thread}"
    assert (
        row["agent_type"] == "refund_email"
    ), f"Expected agent_type='refund_email', got {row['agent_type']!r}"
    assert (
        row["customer_id"] is None
    ), f"Expected customer_id=NULL for workspace agent, got {row['customer_id']!r}"


# ── Calendar Agent — 5 cases ──────────────────────────────────────────────────


@pytest.mark.integration
def test_calendar_06_read_query_routes_to_today_events_cli(calendar_graph, ws_thread):
    """'What's on my calendar today?' -> today_events CLI tool called."""
    result = ws_invoke(calendar_graph, "What's on my calendar today?", ws_thread)

    assert "messages" in result
    used = tool_names_used(result["messages"])
    assert "today_events" in used, (
        f"Expected today_events (CLI tool) to be called for a read query. "
        f"Tools used: {used}"
    )


@pytest.mark.integration
def test_calendar_07_write_operation_calls_create_calendar_event(
    calendar_graph, ws_thread
):
    """'Schedule a Sprint Review tomorrow at 2pm' -> create_calendar_event MCP tool called."""
    result = ws_invoke(
        calendar_graph,
        "Schedule a team meeting called 'Sprint Review' tomorrow at 2pm for 1 hour",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    assert (
        "create_calendar_event" in used
    ), f"Expected create_calendar_event to be called for a write request. Tools used: {used}"
    content = last_ai_content(result["messages"])
    assert any(
        kw in content
        for kw in ("scheduled", "created", "confirmed", "event", "meeting")
    ), f"Expected confirmation in response. Got: {content[:300]}"


@pytest.mark.integration
def test_calendar_08_free_slot_query_uses_suggest_meeting_time(
    calendar_graph, ws_thread
):
    """'Find a free 30-minute slot this week' -> suggest_meeting_time MCP tool called."""
    result = ws_invoke(
        calendar_graph,
        "Find a free 30-minute slot this week for a one-on-one meeting",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    assert (
        "suggest_meeting_time" in used
    ), f"Expected suggest_meeting_time to be called. Tools used: {used}"
    content = last_ai_content(result["messages"])
    time_keywords = [
        "am",
        "pm",
        "today",
        "tomorrow",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "morning",
        "afternoon",
        "slot",
        "available",
        "free",
        "time",
        "hour",
        "minute",
    ]
    assert any(
        kw in content for kw in time_keywords
    ), f"Expected time-related content in response. Got: {content[:300]}"


@pytest.mark.integration
def test_calendar_09_verifier_catches_calendar_rate_limit(
    calendar_error_graph, ws_thread
):
    """Calendar API returns rate-limit error on create_calendar_event -> verifier marks valid=False."""
    result = ws_invoke(
        calendar_error_graph,
        "Schedule a meeting called 'Daily Standup' tomorrow at 9am for 30 minutes",
        ws_thread,
    )

    assert result["verification"] is not None, "verification field must be populated"
    assert result["verification"]["valid"] is False, (
        f"Verifier should reject rate-limit error. "
        f"verification={result['verification']}"
    )


@pytest.mark.integration
def test_calendar_10_session_persists_with_agent_type_and_null_customer_id(
    ws_thread, tmp_path
):
    """Calendar runs without customer_id; session row carries agent_type='calendar' and customer_id=NULL."""
    preflight = _try_db_connection()
    preflight.close()

    async def _run():
        from graph.calendar.graph import compile_graph
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / "calendar-route.db")
        ) as checkpointer:
            graph = compile_graph(
                MOCK_CALENDAR_CLI_TOOLS + MOCK_CALENDAR_MCP_TOOLS,
                checkpointer,
            )
            return await stream_workspace_request(
                {"calendar": graph},
                message="What calendars do I have access to?",
                agent_type="calendar",
                thread_id=ws_thread,
            )

    events = asyncio.run(_run())
    used = planner_tool_names_from_events(events)
    assert used, "Expected Calendar /chat/stream path to emit planner tool calls"
    response = response_text_from_events(events)
    assert len(response) > 0, "Expected a streamed AI response from /chat/stream"

    conn = None
    try:
        session_payload = get_session_via_api(ws_thread)
        assert session_payload["session"]["agent_type"] == "calendar"
        assert session_payload["session"]["customer_id"] is None
        assert [msg["role"] for msg in session_payload["messages"][:2]] == ["human", "ai"]
        assert (
            session_payload["messages"][0]["content"]
            == "What calendars do I have access to?"
        )

        conn = _try_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT agent_type, customer_id FROM sessions WHERE thread_id = %s",
            (ws_thread,),
        )
        row = cursor.fetchone()
    finally:
        cleanup_sessions(ws_thread)
        try:
            conn.close()
        except Exception:
            pass

    assert row is not None, f"Session row not found for thread_id={ws_thread}"
    assert (
        row["agent_type"] == "calendar"
    ), f"Expected agent_type='calendar', got {row['agent_type']!r}"
    assert (
        row["customer_id"] is None
    ), f"Expected customer_id=NULL for workspace agent, got {row['customer_id']!r}"


# ── Cross-agent — 2 cases ─────────────────────────────────────────────────────


@pytest.mark.integration
def test_cross_11_router_dispatches_all_agent_types_when_calendar_mcp_is_available(
    monkeypatch,
):
    """get_graph() and get_async_graph() dispatch the correct graph for each agent_type and reject unknown types."""
    import graph.router as router_module
    from graph.router import get_graph, get_async_graph
    from graph.mcp_client import mcp_manager

    # Reset cached graphs so they rebuild from our mock tool surface
    monkeypatch.setattr(router_module, "_re_graph", None, raising=False)
    monkeypatch.setattr(router_module, "_re_conn", None, raising=False)
    monkeypatch.setattr(router_module, "_cal_graph", None, raising=False)
    monkeypatch.setattr(router_module, "_cal_conn", None, raising=False)
    monkeypatch.setattr(
        mcp_manager, "_tools", MOCK_GMAIL_TOOLS + MOCK_CALENDAR_MCP_TOOLS, raising=False
    )

    # ── Synchronous router (get_graph) ──────────────────────────────────────

    assert get_graph("customer_service") is not None

    re_graph = get_graph("refund_email")
    assert re_graph is not None
    re_mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {"id": "t1", "name": "search_gmail", "args": {"query": "refund"}}
            ],
        ),
        AIMessage(content="I found refund emails in your inbox."),
    )
    with patch("graph.refund_email.planner.create_llm", return_value=re_mock_llm):
        re_result = ws_invoke(
            re_graph, "What refund emails came in?", f"cross11-re-{uuid.uuid4()}"
        )
    assert "search_gmail" in tool_names_used(
        re_result["messages"]
    ), "RE graph dispatch must route through Gmail tools, not calendar tools"

    cal_graph = get_graph("calendar")
    assert cal_graph is not None
    cal_mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {"id": "t1", "name": "today_events", "args": {"calendar_id": "primary"}}
            ],
        ),
        AIMessage(content="You have a daily standup today."),
    )
    with patch("graph.calendar.planner.create_llm", return_value=cal_mock_llm):
        cal_result = ws_invoke(
            cal_graph, "What's on my calendar today?", f"cross11-cal-{uuid.uuid4()}"
        )
    assert "today_events" in tool_names_used(
        cal_result["messages"]
    ), "Calendar graph dispatch must route through Calendar CLI tools, not Gmail tools"

    with pytest.raises(ValueError, match="unknown_agent"):
        get_graph("unknown_agent")

    # ── Async router (get_async_graph) — production path used by /chat/stream ──

    async def _verify_async_dispatch():
        async_cs = await get_async_graph("customer_service")
        assert async_cs is not None, "get_async_graph must return customer_service graph"

        async_re = await get_async_graph("refund_email")
        assert async_re is not None, "get_async_graph must return refund_email graph"

        async_cal = await get_async_graph("calendar")
        assert async_cal is not None, "get_async_graph must return calendar graph"

        with pytest.raises(ValueError, match="unknown_agent"):
            await get_async_graph("unknown_agent")

    asyncio.run(_verify_async_dispatch())


@pytest.mark.integration
def test_cross_12_session_isolation_across_agent_types(ws_thread, tmp_path):
    """RE and Calendar sessions created in sequence are isolated: correct agent_type per thread, no tool bleed."""
    from graph.refund_email.graph import compile_graph as re_compile
    from graph.calendar.graph import compile_graph as cal_compile
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    preflight = _try_db_connection()
    preflight.close()

    re_thread = f"re-{ws_thread}"
    cal_thread = f"cal-{ws_thread}"

    async def _run():
        async with AsyncSqliteSaver.from_conn_string(
            str(tmp_path / "cross-route.db")
        ) as checkpointer:
            re_graph = re_compile(MOCK_GMAIL_TOOLS, checkpointer)
            cal_graph = cal_compile(
                MOCK_CALENDAR_CLI_TOOLS + MOCK_CALENDAR_MCP_TOOLS,
                checkpointer,
            )
            events_by_type = {"refund_email": re_graph, "calendar": cal_graph}
            re_events = await stream_workspace_request(
                events_by_type,
                message="What refund emails came in today?",
                agent_type="refund_email",
                thread_id=re_thread,
            )
            cal_events = await stream_workspace_request(
                events_by_type,
                message="What's on my calendar today?",
                agent_type="calendar",
                thread_id=cal_thread,
            )
            return re_events, cal_events

    re_events, cal_events = asyncio.run(_run())

    re_tools = planner_tool_names_from_events(re_events)
    cal_tools = planner_tool_names_from_events(cal_events)

    # Calendar-only tools must not appear in the RE thread
    assert (
        "today_events" not in re_tools
    ), f"RE thread must not use Calendar CLI tools. RE tools: {re_tools}"
    # Gmail-only tools must not appear in the Calendar thread
    assert (
        "search_gmail" not in cal_tools
    ), f"Calendar thread must not use Gmail tools. Cal tools: {cal_tools}"
    db_conn = None
    try:
        re_session = get_session_via_api(re_thread)
        cal_session = get_session_via_api(cal_thread)
        assert re_session["session"]["agent_type"] == "refund_email"
        assert cal_session["session"]["agent_type"] == "calendar"
        assert re_session["session"]["customer_id"] is None
        assert cal_session["session"]["customer_id"] is None

        db_conn = _try_db_connection()
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT thread_id, agent_type, customer_id FROM sessions "
            "WHERE thread_id IN (%s, %s)",
            (re_thread, cal_thread),
        )
        rows = {r["thread_id"]: r for r in cursor.fetchall()}
    finally:
        cleanup_sessions(re_thread, cal_thread)
        try:
            if db_conn is not None:
                db_conn.close()
        except Exception:
            pass

    assert re_thread in rows, f"RE session row not found in DB (thread_id={re_thread})"
    assert (
        cal_thread in rows
    ), f"Calendar session row not found in DB (thread_id={cal_thread})"
    assert (
        rows[re_thread]["agent_type"] == "refund_email"
    ), f"RE session must have agent_type='refund_email', got {rows[re_thread]['agent_type']!r}"
    assert (
        rows[cal_thread]["agent_type"] == "calendar"
    ), f"Calendar session must have agent_type='calendar', got {rows[cal_thread]['agent_type']!r}"
    assert (
        rows[re_thread]["customer_id"] is None
    ), "RE session must have customer_id=NULL"
    assert (
        rows[cal_thread]["customer_id"] is None
    ), "Calendar session must have customer_id=NULL"
