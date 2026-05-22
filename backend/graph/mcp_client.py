import os
from typing import Any

_GMAIL_PREFIXES = ("gmail", "search_gmail", "get_message", "send_message", "send_reply", "list_labels")
_CALENDAR_PREFIXES = ("calendar", "create_event", "update_event", "delete_event", "suggest_meeting", "rsvp",
                      "list_calendar", "get_calendar")


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
        command = os.environ.get("WORKSPACE_MCP_COMMAND")
        if not command:
            return

        from langchain_mcp_adapters.client import MultiServerMCPClient

        args = os.environ.get("WORKSPACE_MCP_ARGS", "").split() if os.environ.get("WORKSPACE_MCP_ARGS") else []
        self._client = MultiServerMCPClient(
            {"workspace": {"command": command, "args": args, "transport": "stdio"}}
        )
        self._tools = await self._client.get_tools()

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
            self._tools = []

    def get_tools(self, agent_type: str) -> list[Any]:
        if agent_type == "refund_email":
            return [t for t in self._tools if _is_gmail_tool(t)]
        if agent_type == "calendar":
            return [t for t in self._tools if _is_calendar_tool(t)]
        return []


mcp_manager = McpClientManager()
