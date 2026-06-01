import asyncio
import os
import subprocess
from typing import Any

_GMAIL_PREFIXES = ("gmail", "message", "send_reply", "list_labels", "label")
_CALENDAR_PREFIXES = ("calendar", "event", "schedule", "meeting", "rsvp", "today_event", "slot")

_MCP_LOCAL_PORT = 8889
_MCP_LOCAL_URL = f"http://localhost:{_MCP_LOCAL_PORT}/mcp"


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
        self._server_proc: subprocess.Popen | None = None

    @property
    def server_url(self) -> str:
        return _MCP_LOCAL_URL

    async def start(self) -> None:
        import httpx
        from langchain_mcp_adapters.client import MultiServerMCPClient

        command = os.environ.get("WORKSPACE_MCP_COMMAND")
        if not command:
            return

        base_args = (
            os.environ.get("WORKSPACE_MCP_ARGS", "").split()
            if os.environ.get("WORKSPACE_MCP_ARGS")
            else []
        )

        # Start workspace-mcp as a local HTTP server so both langchain_mcp_adapters
        # and the workspace-cli subprocess can reach it via localhost.
        server_env = {
            **os.environ,
            "WORKSPACE_MCP_HOST": "localhost",
            "WORKSPACE_MCP_PORT": str(_MCP_LOCAL_PORT),
            "OAUTHLIB_INSECURE_TRANSPORT": "1",
        }
        self._server_proc = subprocess.Popen(
            [command, *base_args, "--transport", "streamable-http"],
            env=server_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait up to 30 s for the server to accept connections
        async with httpx.AsyncClient() as client:
            for _ in range(30):
                try:
                    await client.get(_MCP_LOCAL_URL, timeout=1.0)
                    break
                except Exception:
                    await asyncio.sleep(1)

        self._client = MultiServerMCPClient(
            {"workspace": {"url": _MCP_LOCAL_URL, "transport": "streamable_http"}}
        )
        self._tools = await self._client.get_tools()

    async def stop(self) -> None:
        self._client = None
        self._tools = []
        if self._server_proc is not None:
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_proc.kill()
            self._server_proc = None

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