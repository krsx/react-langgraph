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
