"""
Integration test suite — Workspace Agents (Refund Email + Calendar).

Requires: OPENROUTER_API_KEY env var, live LLM.
Session-persistence tests (RE-05, Cal-10, Cross-12) also require MySQL
(docker compose up mysql) and are skipped automatically when unreachable.

Run:
    uv run pytest tests/integration/test_workspace_agents.py -m integration -v
"""

import sqlite3
import uuid
import pytest
import openai
from unittest.mock import MagicMock, patch
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
def test_refund_02_batch_processing_triggers_multi_step_tools(
    refund_email_graph, ws_thread
):
    """'Process all refund emails' -> search_gmail, get_message, and send_reply all called."""
    result = ws_invoke(
        refund_email_graph,
        "Process all unread refund emails in my inbox",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    assert (
        "search_gmail" in used
    ), f"Expected search_gmail in batch workflow. Tools used: {used}"
    assert (
        "get_message" in used
    ), f"Expected get_message after search_gmail in batch workflow. Tools used: {used}"
    assert (
        "send_reply" in used
    ), f"Expected send_reply in batch workflow (SEND step). Tools used: {used}"


_VALID_CATEGORIES = ("refund_request", "return_request", "complaint", "other")


@pytest.mark.integration
def test_refund_03_email_classification_identifies_refund_request(
    refund_email_graph, ws_thread
):
    """Agent classifies a refund email body -> response contains an explicit category label."""
    message = (
        "Classify this customer email: "
        "'Hi, I received order #1234 and the item arrived completely broken. "
        "I want a full refund immediately. This is unacceptable.'"
    )
    result = ws_invoke(refund_email_graph, message, ws_thread)

    content = last_ai_content(result["messages"])
    assert any(
        cat in content for cat in _VALID_CATEGORIES
    ), f"Expected one of {_VALID_CATEGORIES} in response. Got: {content[:300]}"


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


@pytest.mark.integration
def test_refund_05_session_persists_with_agent_type_and_null_customer_id(
    refund_email_graph, ws_thread
):
    """Refund Email runs without customer_id; session row carries agent_type='refund_email' and customer_id=NULL."""
    from routes.chat import _persist_session_start

    # Verify graph executes without customer_id
    result = ws_invoke(
        refund_email_graph,
        "Are there any refund requests in my inbox today?",
        ws_thread,
    )
    assert (
        result["customer_id"] is None
    ), "Refund Email agent must not require customer_id"
    assert "messages" in result
    last = result["messages"][-1]
    assert isinstance(
        last, AIMessage
    ), f"Expected AIMessage as last message, got {type(last)}"
    assert len(last.content) > 0, "Expected a non-empty response"

    # Verify session row is persisted with correct agent_type and customer_id=NULL
    conn = _try_db_connection()
    try:
        _persist_session_start(
            ws_thread, None, "Are there any refund requests?", "refund_email"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT agent_type, customer_id FROM sessions WHERE thread_id = %s",
            (ws_thread,),
        )
        row = cursor.fetchone()
    finally:
        try:
            clean = conn.cursor()
            clean.execute(
                "DELETE FROM session_messages WHERE thread_id = %s", (ws_thread,)
            )
            clean.execute("DELETE FROM sessions WHERE thread_id = %s", (ws_thread,))
            conn.commit()
        finally:
            conn.close()

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
    mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tc1",
                    "name": "today_events",
                    "args": {"calendar_id": "primary"},
                }
            ],
        ),
        AIMessage(content="You have a daily standup on your calendar today."),
    )

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
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
    mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tc1",
                    "name": "create_calendar_event",
                    "args": {
                        "summary": "Sprint Review",
                        "start": "2024-01-16T14:00:00",
                        "end": "2024-01-16T15:00:00",
                    },
                }
            ],
        ),
        AIMessage(content="I've scheduled the Sprint Review for tomorrow at 2 PM."),
    )

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
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
    mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tc1",
                    "name": "suggest_meeting_time",
                    "args": {
                        "duration_minutes": 30,
                        "time_min": "2024-01-15T08:00:00",
                        "time_max": "2024-01-19T18:00:00",
                    },
                }
            ],
        ),
        AIMessage(content="I found a free 30-minute slot on Monday at 2:00 PM."),
    )

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
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
    mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tc1",
                    "name": "create_calendar_event",
                    "args": {
                        "summary": "Daily Standup",
                        "start": "2024-01-16T09:00:00",
                        "end": "2024-01-16T09:30:00",
                    },
                }
            ],
        ),
        AIMessage(content="I've scheduled the Daily Standup for tomorrow at 9 AM."),
    )

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
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
    calendar_graph, ws_thread
):
    """Calendar runs without customer_id; session row carries agent_type='calendar' and customer_id=NULL."""
    from routes.chat import _persist_session_start

    mock_llm = make_mock_llm(
        AIMessage(
            content="", tool_calls=[{"id": "tc1", "name": "list_calendars", "args": {}}]
        ),
        AIMessage(
            content="You have access to your Primary Calendar and the Engineering Team calendar."
        ),
    )

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
        result = ws_invoke(
            calendar_graph,
            "What calendars do I have access to?",
            ws_thread,
        )

    assert result["customer_id"] is None, "Calendar agent must not require customer_id"
    assert "messages" in result
    last = result["messages"][-1]
    assert isinstance(
        last, AIMessage
    ), f"Expected AIMessage as last message, got {type(last)}"
    assert len(last.content) > 0, "Expected a non-empty response"

    # Verify session row is persisted with correct agent_type and customer_id=NULL
    conn = _try_db_connection()
    try:
        _persist_session_start(
            ws_thread, None, "What calendars do I have access to?", "calendar"
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT agent_type, customer_id FROM sessions WHERE thread_id = %s",
            (ws_thread,),
        )
        row = cursor.fetchone()
    finally:
        try:
            clean = conn.cursor()
            clean.execute(
                "DELETE FROM session_messages WHERE thread_id = %s", (ws_thread,)
            )
            clean.execute("DELETE FROM sessions WHERE thread_id = %s", (ws_thread,))
            conn.commit()
        finally:
            conn.close()

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
    """get_graph() dispatches the correct graph for each agent_type and rejects unknown types."""
    import graph.router as router_module
    from graph.router import get_graph
    from graph.mcp_client import mcp_manager

    # Reset cached graphs so they rebuild from our mock tool surface
    monkeypatch.setattr(router_module, "_re_graph", None, raising=False)
    monkeypatch.setattr(router_module, "_re_conn", None, raising=False)
    monkeypatch.setattr(router_module, "_cal_graph", None, raising=False)
    monkeypatch.setattr(router_module, "_cal_conn", None, raising=False)
    monkeypatch.setattr(
        mcp_manager, "_tools", MOCK_GMAIL_TOOLS + MOCK_CALENDAR_MCP_TOOLS, raising=False
    )

    # customer_service graph is non-None
    assert get_graph("customer_service") is not None

    # RE graph: invoke with mock LLM → search_gmail called (proves Gmail tool surface)
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

    # Calendar graph: invoke with mock LLM → today_events called (proves Calendar tool surface)
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

    # Unknown agent_type must be rejected
    with pytest.raises(ValueError, match="unknown_agent"):
        get_graph("unknown_agent")


@pytest.mark.integration
def test_cross_12_session_isolation_across_agent_types(ws_thread):
    """RE and Calendar sessions created in sequence are isolated: correct agent_type per thread, no tool bleed."""
    from routes.chat import _persist_session_start
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.refund_email.graph import compile_graph as re_compile
    from graph.calendar.graph import compile_graph as cal_compile

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    re_graph = re_compile(MOCK_GMAIL_TOOLS, checkpointer)
    cal_graph = cal_compile(
        MOCK_CALENDAR_CLI_TOOLS + MOCK_CALENDAR_MCP_TOOLS, checkpointer
    )

    re_thread = f"re-{ws_thread}"
    cal_thread = f"cal-{ws_thread}"

    refund_mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {"id": "tc1", "name": "search_gmail", "args": {"query": "refund"}}
            ],
        ),
        AIMessage(content="I found refund emails in your inbox."),
    )
    calendar_mock_llm = make_mock_llm(
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "tc1",
                    "name": "today_events",
                    "args": {"calendar_id": "primary"},
                }
            ],
        ),
        AIMessage(content="You have a daily standup today."),
    )

    with patch(
        "graph.refund_email.planner.create_llm", return_value=refund_mock_llm
    ), patch("graph.calendar.planner.create_llm", return_value=calendar_mock_llm):
        re_result = ws_invoke(re_graph, "What refund emails came in today?", re_thread)
        cal_result = ws_invoke(cal_graph, "What's on my calendar today?", cal_thread)

    re_tools = tool_names_used(re_result["messages"])
    cal_tools = tool_names_used(cal_result["messages"])

    # Calendar-only tools must not appear in the RE thread
    assert (
        "today_events" not in re_tools
    ), f"RE thread must not use Calendar CLI tools. RE tools: {re_tools}"
    # Gmail-only tools must not appear in the Calendar thread
    assert (
        "search_gmail" not in cal_tools
    ), f"Calendar thread must not use Gmail tools. Cal tools: {cal_tools}"
    # Both agents run without customer_id
    assert re_result["customer_id"] is None
    assert cal_result["customer_id"] is None

    # Verify DB session isolation: each thread persists with correct agent_type
    db_conn = _try_db_connection()
    try:
        _persist_session_start(
            re_thread, None, "What refund emails came in today?", "refund_email"
        )
        _persist_session_start(
            cal_thread, None, "What's on my calendar today?", "calendar"
        )
        cursor = db_conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT thread_id, agent_type, customer_id FROM sessions "
            "WHERE thread_id IN (%s, %s)",
            (re_thread, cal_thread),
        )
        rows = {r["thread_id"]: r for r in cursor.fetchall()}
    finally:
        try:
            clean = db_conn.cursor()
            for tid in (re_thread, cal_thread):
                clean.execute(
                    "DELETE FROM session_messages WHERE thread_id = %s", (tid,)
                )
                clean.execute("DELETE FROM sessions WHERE thread_id = %s", (tid,))
            db_conn.commit()
        finally:
            db_conn.close()

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
