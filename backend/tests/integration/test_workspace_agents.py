"""
Integration test suite — Workspace Agents (Refund Email + Calendar).

Requires: OPENROUTER_API_KEY env var, live LLM.
MySQL is NOT required — session-persistence is verified at the graph-state level
(SQL/API layer is covered by test_sessions_agent_type.py unit tests).

Run:
    uv run pytest tests/integration/test_workspace_agents.py -m integration -v
"""
import sqlite3
import uuid
import pytest
import openai
from langchain_core.messages import HumanMessage, AIMessage

from tests.integration.conftest import (
    handle_rate_limit,
    MOCK_GMAIL_TOOLS,
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
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    names.add(name)
    return names


def last_ai_content(messages: list) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            return m.content.lower()
    return ""


# ── Refund Email Agent — 5 cases ──────────────────────────────────────────────

@pytest.mark.integration
def test_re_01_interactive_query_triggers_search_gmail(refund_email_graph, ws_thread):
    """'What refund emails came in today?' -> search_gmail tool called; summary returned."""
    result = ws_invoke(refund_email_graph, "What refund emails came in today?", ws_thread)

    assert "messages" in result
    used = tool_names_used(result["messages"])
    assert "search_gmail" in used, (
        f"Expected search_gmail to be called for an inbox query. Tools used: {used}"
    )
    content = last_ai_content(result["messages"])
    assert len(content) > 0, "Expected a non-empty summary in the last AI message"


@pytest.mark.integration
def test_re_02_batch_processing_triggers_multi_step_tools(refund_email_graph, ws_thread):
    """'Process all refund emails' -> both search_gmail and get_message called."""
    result = ws_invoke(
        refund_email_graph,
        "Process all unread refund emails in my inbox",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    assert "search_gmail" in used, (
        f"Expected search_gmail in batch workflow. Tools used: {used}"
    )
    assert "get_message" in used, (
        f"Expected get_message after search_gmail in batch workflow. Tools used: {used}"
    )


@pytest.mark.integration
def test_re_03_email_classification_identifies_refund_request(refund_email_graph, ws_thread):
    """Agent classifies a refund email body -> response contains a classification label."""
    message = (
        "Classify this customer email: "
        "'Hi, I received order #1234 and the item arrived completely broken. "
        "I want a full refund immediately. This is unacceptable.'"
    )
    result = ws_invoke(refund_email_graph, message, ws_thread)

    content = last_ai_content(result["messages"])
    assert any(label in content for label in ("refund_request", "refund")), (
        f"Expected classification label in response. Got: {content[:300]}"
    )


@pytest.mark.integration
def test_re_04_verifier_catches_gmail_permission_denied(refund_email_error_graph, ws_thread):
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


@pytest.mark.integration
def test_re_05_graph_executes_without_customer_id(refund_email_graph, ws_thread):
    """Refund Email graph runs with customer_id=None and returns a valid AIMessage."""
    result = ws_invoke(
        refund_email_graph,
        "Are there any refund requests in my inbox today?",
        ws_thread,
    )

    assert result["customer_id"] is None, (
        "Refund Email agent must not require customer_id"
    )
    assert "messages" in result
    last = result["messages"][-1]
    assert isinstance(last, AIMessage), (
        f"Expected AIMessage as last message, got {type(last)}"
    )
    assert len(last.content) > 0, "Expected a non-empty response"


# ── Calendar Agent — 5 cases ──────────────────────────────────────────────────

@pytest.mark.integration
def test_cal_06_read_query_routes_to_today_events_cli(calendar_graph, ws_thread):
    """'What's on my calendar today?' -> today_events CLI tool called."""
    result = ws_invoke(calendar_graph, "What's on my calendar today?", ws_thread)

    assert "messages" in result
    used = tool_names_used(result["messages"])
    assert "today_events" in used, (
        f"Expected today_events (CLI tool) to be called for a read query. "
        f"Tools used: {used}"
    )


@pytest.mark.integration
def test_cal_07_write_operation_calls_create_event(calendar_graph, ws_thread):
    """'Schedule a Sprint Review tomorrow at 2pm' -> create_event MCP tool called."""
    result = ws_invoke(
        calendar_graph,
        "Schedule a team meeting called 'Sprint Review' tomorrow at 2pm for 1 hour",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    assert "create_event" in used, (
        f"Expected create_event to be called for a write request. Tools used: {used}"
    )
    content = last_ai_content(result["messages"])
    assert any(kw in content for kw in ("scheduled", "created", "confirmed", "event", "meeting")), (
        f"Expected confirmation in response. Got: {content[:300]}"
    )


@pytest.mark.integration
def test_cal_08_free_slot_query_uses_list_tools(calendar_graph, ws_thread):
    """'Find a free 30-minute slot this week' -> calendar list tool called; response has time content."""
    result = ws_invoke(
        calendar_graph,
        "Find a free 30-minute slot this week for a one-on-one meeting",
        ws_thread,
    )

    used = tool_names_used(result["messages"])
    calendar_list_tools = {"today_events", "list_events", "list_calendars"}
    assert used & calendar_list_tools, (
        f"Expected at least one calendar list tool to be called. Tools used: {used}"
    )
    content = last_ai_content(result["messages"])
    time_keywords = [
        "am", "pm", "today", "tomorrow", "monday", "tuesday", "wednesday",
        "thursday", "friday", "morning", "afternoon", "slot", "available",
        "free", "time", "hour", "minute",
    ]
    assert any(kw in content for kw in time_keywords), (
        f"Expected time-related content in response. Got: {content[:300]}"
    )


@pytest.mark.integration
def test_cal_09_verifier_catches_calendar_rate_limit(calendar_error_graph, ws_thread):
    """Calendar API returns rate-limit error on create_event -> verifier marks valid=False."""
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
def test_cal_10_graph_executes_without_customer_id(calendar_graph, ws_thread):
    """Calendar graph runs with customer_id=None and returns a valid AIMessage."""
    result = ws_invoke(
        calendar_graph,
        "What calendars do I have access to?",
        ws_thread,
    )

    assert result["customer_id"] is None, (
        "Calendar agent must not require customer_id"
    )
    assert "messages" in result
    last = result["messages"][-1]
    assert isinstance(last, AIMessage), (
        f"Expected AIMessage as last message, got {type(last)}"
    )
    assert len(last.content) > 0, "Expected a non-empty response"


# ── Cross-agent — 2 cases ─────────────────────────────────────────────────────

@pytest.mark.integration
def test_cross_11_router_dispatches_all_agent_types():
    """get_graph() returns a compiled graph for all three agent types; unknown raises ValueError."""
    from graph.router import get_graph

    assert get_graph("customer_service") is not None
    assert get_graph("refund_email") is not None
    assert get_graph("calendar") is not None

    with pytest.raises(ValueError, match="unknown_agent"):
        get_graph("unknown_agent")


@pytest.mark.integration
def test_cross_12_session_isolation_across_agent_types(ws_thread):
    """RE and Calendar threads sharing a checkpointer do not bleed tool usage across threads."""
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.refund_email.graph import compile_graph as re_compile
    from graph.calendar.graph import compile_graph as cal_compile, CLI_TOOLS

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    re_graph = re_compile(MOCK_GMAIL_TOOLS, checkpointer)
    cal_graph = cal_compile(CLI_TOOLS + MOCK_CALENDAR_MCP_TOOLS, checkpointer)

    re_thread = f"re-{ws_thread}"
    cal_thread = f"cal-{ws_thread}"

    re_result = ws_invoke(re_graph, "What refund emails came in today?", re_thread)
    cal_result = ws_invoke(cal_graph, "What's on my calendar today?", cal_thread)

    re_tools = tool_names_used(re_result["messages"])
    cal_tools = tool_names_used(cal_result["messages"])

    # Calendar-only tools must not appear in the RE thread
    assert "today_events" not in re_tools, (
        f"RE thread must not use Calendar CLI tools. RE tools: {re_tools}"
    )
    # Gmail-only tools must not appear in the Calendar thread
    assert "search_gmail" not in cal_tools, (
        f"Calendar thread must not use Gmail tools. Cal tools: {cal_tools}"
    )
    # Both agents run without customer_id
    assert re_result["customer_id"] is None
    assert cal_result["customer_id"] is None
