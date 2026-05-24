import pytest
from unittest.mock import MagicMock, patch, AsyncMock


# ── Cycle 8: get_tools filters by agent_type ──────────────────────────────────

def test_get_tools_refund_email_returns_gmail_tools():
    from graph.mcp_client import McpClientManager

    gmail_tool = MagicMock()
    gmail_tool.name = "search_gmail"
    calendar_tool = MagicMock()
    calendar_tool.name = "list_calendar_events"

    manager = McpClientManager.__new__(McpClientManager)
    manager._tools = [gmail_tool, calendar_tool]

    tools = manager.get_tools("refund_email")

    assert gmail_tool in tools
    assert calendar_tool not in tools


# ── Cycle 9: get_tools filters calendar tools ─────────────────────────────────

def test_get_tools_calendar_returns_calendar_tools():
    from graph.mcp_client import McpClientManager

    gmail_tool = MagicMock()
    gmail_tool.name = "search_gmail"
    calendar_tool = MagicMock()
    calendar_tool.name = "list_calendar_events"

    manager = McpClientManager.__new__(McpClientManager)
    manager._tools = [gmail_tool, calendar_tool]

    tools = manager.get_tools("calendar")

    assert calendar_tool in tools
    assert gmail_tool not in tools


# ── Cycle 10: lifespan skips MCP init when env var absent ─────────────────────

def test_mcp_manager_start_skips_when_env_var_absent(monkeypatch):
    import asyncio
    from graph.mcp_client import McpClientManager

    monkeypatch.delenv("WORKSPACE_MCP_COMMAND", raising=False)

    manager = McpClientManager()
    asyncio.run(manager.start())

    assert manager._client is None
    assert manager._tools == []


# ── Cycle 11: lifespan initializes MCP client when env var present ────────────

def test_mcp_manager_start_initializes_when_env_var_present(monkeypatch):
    import asyncio
    from graph.mcp_client import McpClientManager

    monkeypatch.setenv("WORKSPACE_MCP_COMMAND", "workspace-mcp")

    mock_client = AsyncMock()
    mock_tool = MagicMock()
    mock_tool.name = "search_gmail"
    mock_client.get_tools = AsyncMock(return_value=[mock_tool])

    with patch("langchain_mcp_adapters.client.MultiServerMCPClient", return_value=mock_client):
        manager = McpClientManager()
        asyncio.run(manager.start())

    assert manager._tools == [mock_tool]


# ── Cycle 12: get_tools customer_service returns empty list ───────────────────

def test_get_tools_customer_service_returns_empty():
    from graph.mcp_client import McpClientManager

    gmail_tool = MagicMock()
    gmail_tool.name = "search_gmail"

    manager = McpClientManager.__new__(McpClientManager)
    manager._tools = [gmail_tool]

    tools = manager.get_tools("customer_service")

    assert tools == []


# ── Cycle 13: get_tools unknown agent_type raises ValueError ──────────────────

def test_get_tools_unknown_type_raises_value_error():
    from graph.mcp_client import McpClientManager

    manager = McpClientManager.__new__(McpClientManager)
    manager._tools = []

    with pytest.raises(ValueError, match="unknown_agent"):
        manager.get_tools("unknown_agent")


# ── Cycle 14: stop() clears state without raising NotImplementedError ─────────

def test_mcp_manager_stop_clears_state_without_raising():
    """stop() must not raise even when MultiServerMCPClient.__aexit__ raises NotImplementedError."""
    import asyncio
    from graph.mcp_client import McpClientManager

    mock_client = MagicMock()
    mock_client.__aexit__ = MagicMock(side_effect=NotImplementedError("context manager not supported"))
    manager = McpClientManager()
    manager._client = mock_client
    manager._tools = [MagicMock()]

    asyncio.run(manager.stop())

    assert manager._client is None
    assert manager._tools == []


# ── Cycle 15: app lifespan closes all async graphs on shutdown ───────────────

def test_app_lifespan_closes_all_async_graphs(monkeypatch):
    import importlib
    from fastapi.testclient import TestClient

    start = AsyncMock()
    stop = AsyncMock()
    close_customer = AsyncMock()
    close_refund = AsyncMock()
    close_calendar = AsyncMock()

    monkeypatch.setattr("graph.mcp_client.mcp_manager.start", start)
    monkeypatch.setattr("graph.mcp_client.mcp_manager.stop", stop)
    monkeypatch.setattr("graph.customer_service.graph.close_async_graph", close_customer)
    monkeypatch.setattr("graph.refund_email.graph.close_async_graph", close_refund)
    monkeypatch.setattr("graph.calendar.graph.close_async_graph", close_calendar)

    main = importlib.import_module("main")
    main = importlib.reload(main)

    with TestClient(main.app):
        pass

    start.assert_awaited_once()
    stop.assert_awaited_once()
    close_customer.assert_awaited_once()
    close_refund.assert_awaited_once()
    close_calendar.assert_awaited_once()
