import os
from typing import Any

_GMAIL_PREFIXES = ("gmail", "message", "send_reply", "list_labels", "label")
_CALENDAR_PREFIXES = ("calendar", "event", "schedule", "meeting", "rsvp", "today_event", "slot")


def _is_gmail_tool(tool: Any) -> bool:
    name = getattr(tool, "name", "").lower()
    return any(name.startswith(p) or p in name for p in _GMAIL_PREFIXES)


def _is_calendar_tool(tool: Any) -> bool:
    name = getattr(tool, "name", "").lower()
    return any(name.startswith(p) or p in name for p in _CALENDAR_PREFIXES)


class McpClientManager:
    def __init__(self) -> None:
        self._client = None
        self._tools: list[Any] = []

    async def start(self) -> None:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        url = os.environ.get("WORKSPACE_MCP_URL")
        if url:
            self._client = MultiServerMCPClient(
                {"workspace": {"url": url, "transport": "streamable_http"}}
            )
            self._tools = await self._client.get_tools()
            return

        command = os.environ.get("WORKSPACE_MCP_COMMAND")
        if not command:
            return

        args = os.environ.get("WORKSPACE_MCP_ARGS", "").split() if os.environ.get("WORKSPACE_MCP_ARGS") else []
        self._client = MultiServerMCPClient(
            {"workspace": {"command": command, "args": args, "transport": "stdio"}}
        )
        self._tools = await self._client.get_tools()

    async def stop(self) -> None:
        # MultiServerMCPClient uses on-demand sessions per tool call (no persistent subprocess).
        # __aexit__ intentionally raises NotImplementedError in the adapter library, so we
        # simply release our references — no subprocess cleanup is required.
        self._client = None
        self._tools = []

    def get_tools(self, agent_type: str) -> list[Any]:
        if agent_type == "refund_email":
            return [t for t in self._tools if _is_gmail_tool(t)]
        if agent_type == "calendar":
            return [t for t in self._tools if _is_calendar_tool(t)]
        if agent_type == "customer_service":
            return []
        raise ValueError(
            f"Unsupported agent_type '{agent_type}' for MCP tool filtering. "
            "Must be one of: refund_email, calendar, customer_service"
        )


mcp_manager = McpClientManager()
