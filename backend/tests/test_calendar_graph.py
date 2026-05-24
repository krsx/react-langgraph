import pytest
import sys


@pytest.fixture(autouse=True)
def clean_imports():
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("graph.calendar") and mod != "graph.calendar.cli_tools":
            sys.modules.pop(mod, None)


# ── Cycle 1: graph compiles with mock tools ───────────────────────────────────

def test_create_builder_compiles_with_empty_tool_list():
    from graph.calendar.graph import create_builder
    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3

    builder = create_builder([])
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    graph = builder.compile(checkpointer=SqliteSaver(conn))
    assert graph is not None


# ── Cycle 2: graph topology — correct nodes, no memory nodes ─────────────────

def test_graph_has_correct_nodes_and_no_memory_nodes():
    from graph.calendar.graph import create_builder

    builder = create_builder([])
    node_names = set(builder.nodes.keys())

    assert "planner" in node_names
    assert "tools" in node_names
    assert "verifier" in node_names
    assert "memory_loader" not in node_names
    assert "memory_update" not in node_names


# ── Cycle 3: system prompt encodes workflow steps ─────────────────────────────

def test_system_prompt_contains_workflow_steps():
    from graph.calendar.planner import build_system_prompt

    prompt = build_system_prompt()

    for step in ("QUERY", "LIST", "DRAFT", "SCHEDULE", "CONFIRM", "RESPOND"):
        assert step in prompt, f"System prompt missing step: {step}"


# ── Cycle 4: system prompt covers key operation types ────────────────────────

def test_system_prompt_mentions_key_calendar_operations():
    from graph.calendar.planner import build_system_prompt

    prompt = build_system_prompt()

    for keyword in ("today_events", "list_events", "create_event", "update_event", "delete_event"):
        assert keyword in prompt, f"System prompt missing operation: {keyword}"


# ── Cycle 5: router dispatches "calendar" ────────────────────────────────────

def test_router_get_graph_dispatches_calendar():
    from unittest.mock import patch
    from langchain_core.tools import tool
    import graph.router as router_module

    router_module._cal_graph = None
    router_module._cal_conn = None

    @tool
    def create_event(summary: str) -> str:
        """Create a calendar event."""
        return "ok"

    with patch.object(router_module, "mcp_manager") as mock_mgr:
        mock_mgr.get_tools.return_value = [create_event]
        g = router_module.get_graph("calendar")

    assert g is not None


# ── Cycle 6: get_async_graph merges CLI tools + MCP tools ────────────────────

def test_get_async_graph_merges_cli_and_mcp_tools():
    import asyncio
    from unittest.mock import patch
    from langchain_core.tools import tool
    import graph.calendar.graph as cal_module

    cal_module._async_graph = None
    cal_module._async_checkpointer_cm = None

    @tool
    def create_event(summary: str) -> str:
        """Create a calendar event."""
        return "ok"

    captured: dict = {}
    original_compile = cal_module.compile_graph

    def capturing_compile(tools, checkpointer):
        captured["tools"] = list(tools)
        return original_compile(tools, checkpointer)

    async def run():
        with patch.object(cal_module, "mcp_manager") as mock_mgr, \
             patch.object(cal_module, "compile_graph", side_effect=capturing_compile):
            mock_mgr.get_tools.return_value = [create_event]
            g = await cal_module.get_async_graph()
            return g, mock_mgr.get_tools.call_args

    graph_obj, call_args = asyncio.run(run())
    assert graph_obj is not None
    assert call_args[0][0] == "calendar"
    tool_names = [t.name for t in captured["tools"]]
    assert "create_event" in tool_names
    assert "today_events" in tool_names


# ── Cycle 7: get_async_graph caches on repeated calls when MCP tools are present

def test_get_async_graph_returns_same_instance_on_repeated_calls():
    import asyncio
    from unittest.mock import patch
    from langchain_core.tools import tool
    import graph.calendar.graph as cal_module

    cal_module._async_graph = None
    cal_module._async_checkpointer_cm = None

    @tool
    def create_event(summary: str) -> str:
        """Create a calendar event."""
        return "ok"

    async def run():
        with patch.object(cal_module, "mcp_manager") as mock_mgr:
            mock_mgr.get_tools.return_value = [create_event]
            g1 = await cal_module.get_async_graph()
            g2 = await cal_module.get_async_graph()
            return g1, g2

    g1, g2 = asyncio.run(run())
    assert g1 is g2


# ── Cycle 8: system prompt covers the full calendar MCP tool surface ──────────

def test_system_prompt_mentions_full_mcp_calendar_surface():
    from graph.calendar.planner import build_system_prompt

    prompt = build_system_prompt()

    for keyword in ("suggest_meeting", "rsvp"):
        assert keyword in prompt.lower(), f"System prompt missing MCP calendar tool: {keyword}"


# ── Cycle 9: explicit failure when MCP tools are unavailable ─────────────────

def test_get_async_graph_raises_when_mcp_tools_unavailable():
    import asyncio
    from unittest.mock import patch
    import graph.calendar.graph as cal_module

    cal_module._async_graph = None
    cal_module._async_checkpointer_cm = None

    async def run():
        with patch.object(cal_module, "mcp_manager") as mock_mgr:
            mock_mgr.get_tools.return_value = []
            await cal_module.get_async_graph()

    with pytest.raises(RuntimeError, match="[Cc]alendar MCP tools"):
        asyncio.run(run())


# ── Cycle 10: behavioral — read query routes through CLI list_events ──────────

def test_read_query_routes_through_cli_list_events_tool():
    import sqlite3
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.calendar.graph import compile_graph

    @tool
    def list_events(time_min: str, time_max: str) -> str:
        """List events in a time range."""
        return '[{"id": "evt1", "summary": "Team standup", "start": "2024-01-15T09:00:00"}]'

    @tool
    def create_event(summary: str, start: str, end: str) -> str:
        """Create a new calendar event."""
        return '{"id": "new_evt"}'

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "list_events",
                             "args": {"time_min": "2024-01-15T00:00:00", "time_max": "2024-01-19T23:59:59"}}],
            )
        return AIMessage(content="Here are the events for this week: Team standup on Monday.")

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([list_events, create_event], SqliteSaver(conn))

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
        result = g.invoke(
            {"messages": [HumanMessage(content="List events this week")], "customer_id": None},
            config={"configurable": {"thread_id": "cal-read-test-1"}},
        )

    tool_call_names = [
        tc["name"]
        for msg in result["messages"]
        if hasattr(msg, "tool_calls") and msg.tool_calls
        for tc in msg.tool_calls
    ]
    assert "list_events" in tool_call_names, "Date-range read query should use CLI list_events tool"
    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert len(last.content) > 0


# ── Cycle 11: behavioral — write request routes through MCP create_event ──────

def test_write_request_routes_through_mcp_create_event_tool():
    import sqlite3
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.calendar.graph import compile_graph

    @tool
    def today_events() -> str:
        """List today's events."""
        return "[]"

    @tool
    def create_event(summary: str, start: str, end: str) -> str:
        """Create a new calendar event."""
        return '{"id": "new_evt", "summary": "Team lunch", "start": "2024-01-19T12:00:00"}'

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "create_event",
                             "args": {"summary": "Team lunch",
                                      "start": "2024-01-19T12:00:00",
                                      "end": "2024-01-19T13:00:00"}}],
            )
        return AIMessage(content="I've scheduled the team lunch for next Friday at noon.")

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([today_events, create_event], SqliteSaver(conn))

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
        result = g.invoke(
            {"messages": [HumanMessage(content="Schedule a team lunch for next Friday at noon")],
             "customer_id": None},
            config={"configurable": {"thread_id": "cal-write-test-1"}},
        )

    tool_call_names = [
        tc["name"]
        for msg in result["messages"]
        if hasattr(msg, "tool_calls") and msg.tool_calls
        for tc in msg.tool_calls
    ]
    assert "create_event" in tool_call_names, "Write request should route through MCP create_event"
    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert len(last.content) > 0


# ── Cycle 12: behavioral — free-slot query returns non-empty AI response ──────

def test_free_slot_query_returns_nonempty_ai_response():
    import sqlite3
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.calendar.graph import compile_graph

    @tool
    def suggest_meeting_times(duration_minutes: int, time_min: str, time_max: str) -> str:
        """Suggest available meeting time slots."""
        return '[{"start": "2024-01-15T14:00:00", "end": "2024-01-15T14:30:00"}]'

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "suggest_meeting_times",
                             "args": {"duration_minutes": 30,
                                      "time_min": "2024-01-15T08:00:00",
                                      "time_max": "2024-01-19T18:00:00"}}],
            )
        return AIMessage(content="I found a free 30-minute slot on Monday at 2:00 PM.")

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([suggest_meeting_times], SqliteSaver(conn))

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
        result = g.invoke(
            {"messages": [HumanMessage(content="Find a free 30-minute slot this week")],
             "customer_id": None},
            config={"configurable": {"thread_id": "cal-freeslot-test-1"}},
        )

    last = result["messages"][-1]
    assert isinstance(last, AIMessage)
    assert len(last.content) > 0


# ── Cycle 13: behavioral — verifier catches failed calendar tool calls ─────────

def test_verifier_marks_invalid_on_failed_calendar_tool_call():
    import sqlite3
    from unittest.mock import MagicMock, patch
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import tool
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph.calendar.graph import compile_graph

    @tool
    def create_event(summary: str, start: str, end: str) -> str:
        """Create a new calendar event."""
        return "Permission denied: insufficient OAuth scope for Calendar write access"

    call_count = [0]

    def fake_invoke(messages, config=None, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return AIMessage(
                content="",
                tool_calls=[{"id": "tc1", "name": "create_event",
                             "args": {"summary": "Team lunch",
                                      "start": "2024-01-19T12:00:00",
                                      "end": "2024-01-19T13:00:00"}}],
            )
        return AIMessage(content="I've scheduled the team lunch for next Friday at noon.")

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value = mock_llm
    mock_llm.invoke.side_effect = fake_invoke

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    g = compile_graph([create_event], SqliteSaver(conn))

    with patch("graph.calendar.planner.create_llm", return_value=mock_llm):
        result = g.invoke(
            {"messages": [HumanMessage(content="Schedule a team lunch for next Friday at noon")],
             "customer_id": None},
            config={"configurable": {"thread_id": "cal-perm-test-1"}},
        )

    verification = result.get("verification", {})
    assert verification.get("valid") is False, "Verifier must mark run invalid on permission error"
    assert verification.get("override_message") is not None, "Verifier must provide override message"
