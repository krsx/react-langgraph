# Report 2 — AI Workspace Agent Suite

| Field | Value |
|---|---|
| **Title** | AI Workspace Agent Suite: Autonomous Google Workspace Agents Using ReAct, LangGraph, and MCP |
| **Course** | LLM Application Development |
| **Student Name** | *(fill in)* |
| **Student ID** | *(fill in)* |
| **Date** | May 2026 |
| **Institution** | National Taiwan University of Science and Technology (NTUST) |

---

## Abstract

This report documents the design and implementation of the AI Workspace Agent Suite, a system of two autonomous AI agents that connect to a live Google Workspace account and perform real-world business tasks through natural language. The **Refund Email Agent** monitors a Gmail inbox, classifies customer emails by intent (refund request, return request, complaint, or unrelated), and sends professional threaded replies without human intervention. The **Calendar Agent** answers natural-language questions about a Google Calendar, creates and modifies events, checks free time slots, and sends RSVPs. Both agents share a common architecture: the ReAct (Reasoning + Acting) pattern implemented with LangGraph `StateGraph`, powered by an LLM via LangChain, and connected to Google Workspace through the open-source `google_workspace_mcp` server over stdio transport. The Calendar Agent adds a second tool surface — lightweight `workspace-cli` subprocess calls for fast read-only queries. This report covers the system architecture, the implementation of each agent, the MCP client integration layer, and the test case design used to validate the system.

---

## 1. Introduction and Objectives

Modern enterprises rely heavily on email and calendar workflows that consume significant human attention. Responding to customer refund requests, scheduling meetings, and managing calendar events are repetitive tasks that follow well-defined patterns — making them prime candidates for AI automation.

This project aims to demonstrate that a small number of well-structured AI agents, built on open standards and connected to real productivity APIs, can reliably automate these workflows. The specific objectives are:

1. **Build two autonomous agents** — one for Gmail-based customer service (refund/return email processing) and one for Google Calendar management — using a shared ReAct architecture.
2. **Implement the ReAct pattern** using LangGraph's `StateGraph` abstraction, enabling the agents to reason about multi-step tasks, call tools, observe results, and iterate until the task is complete.
3. **Connect agents to Google Workspace** through the Model Context Protocol (MCP), an open standard for AI tool integration, using secure local stdio transport that keeps data on-device.
4. **Demonstrate a dual-tool strategy** in the Calendar Agent, combining fast CLI subprocess calls for read operations with full MCP tool calls for write operations.
5. **Validate correctness** through structured test cases covering each agent's functional requirements, tool selection logic, and shared infrastructure behavior.

The system is implemented as a full-stack application with a FastAPI backend hosting the LangGraph agents and a React frontend for user interaction. This report focuses on the backend agent architecture and implementation — the workspace agent modules that extend the base customer service platform.

---

## 2. Background and Related Work

### 2.1 The ReAct Pattern

The ReAct (Reasoning + Acting) paradigm, introduced by Yao et al. (2023), interleaves chain-of-thought reasoning with concrete actions in an iterative loop. Unlike pure chain-of-thought prompting, which generates reasoning traces without external grounding, ReAct agents can call tools, observe the results, and adjust their reasoning accordingly. This closed-loop design enables agents to handle multi-step tasks where the correct sequence of actions depends on intermediate results — for example, searching an inbox, reading specific emails based on search results, classifying their content, and composing replies.

In our implementation, the ReAct loop is realized as a cycle between two graph nodes: `planner` (the LLM reasoning step) and `tools` (the action execution step). The loop continues until the LLM produces a response with no tool calls, at which point the graph terminates.

### 2.2 LangGraph StateGraph

LangGraph provides a directed-graph abstraction for building stateful, multi-step agent workflows. Its `StateGraph` class allows developers to define nodes (Python functions), edges (transitions between nodes), and conditional edges (routing decisions based on state). The key abstraction that enables ReAct is the `add_messages` reducer on the state's `messages` field: rather than replacing the message list on each step, new messages are appended, preserving the full conversation history — including all prior tool calls and results — across every iteration of the loop.

LangGraph also provides the `ToolNode` prebuilt node, which automatically dispatches structured tool call JSON from the LLM to the correct tool implementation and wraps results in `ToolMessage` objects. Combined with `tools_condition` (a prebuilt conditional edge function), these components reduce the implementation of a ReAct agent to a handful of lines defining the graph topology.

### 2.3 Model Context Protocol (MCP)

The Model Context Protocol (MCP) is an open standard (now under the Linux Foundation) that defines a JSON-RPC interface for AI models to discover, invoke, and receive results from external tools. MCP decouples the tool-calling LLM from the tool implementation: the LLM emits structured tool calls, the MCP client forwards them to an MCP server, and the server translates them into API calls (in our case, Google Workspace APIs). This separation means the same agent code works with any MCP-compatible tool server without modification.

In this project, we use the `google_workspace_mcp` server, an open-source MCP server that exposes Gmail and Google Calendar operations as MCP tools. The server handles OAuth 2.0 authentication, API pagination, and error handling, presenting a clean tool interface to the agent.

### 2.4 Stdio Transport — Local-First Security

MCP supports multiple transport mechanisms. We use **stdio transport**, where the MCP server runs as a local subprocess communicating via stdin/stdout pipes. This design ensures that all data — email content, calendar events, OAuth tokens — remains on the local machine. No network ports are opened, no data passes through third-party intermediaries, and the server's lifecycle is tied to the agent's process. This is a deliberate security choice: workspace data is sensitive, and stdio transport eliminates an entire class of network-based attack vectors.

---

## 3. System Architecture

### 3.1 Shared ReAct Loop

Both agents share an identical three-node graph topology. The `planner` node invokes the LLM with the full message history. If the LLM emits tool calls, the `tools_condition` conditional edge routes to the `tools` node, which executes them and appends `ToolMessage` results to the state. Control then returns to `planner` for the next reasoning step. When the LLM produces a response with no tool calls, the edge routes to `verifier` for a post-response quality check, and then to `END`.

```mermaid
flowchart TD
    A[User Input - HumanMessage] --> B[planner]
    B --> C{tools_condition}
    C -->|has tool_calls| D[tools - ToolNode]
    C -->|no tool_calls| E[verifier]
    D --> B
    E --> F[END]

    style B fill:#4A90D9,color:#fff
    style D fill:#7B68EE,color:#fff
    style E fill:#E67E22,color:#fff
    style F fill:#27AE60,color:#fff
```

A single user request may trigger 5–15 iterations of the `planner → tools` loop before the agent produces its final answer. The `verifier` node inspects tool results for errors (permission denied, rate limits, empty lookups) and, if the LLM's final response did not acknowledge the error, overrides it with a clear failure message.

### 3.2 Top-Level System Architecture

The two agents share the MCP client infrastructure but operate on different Google API surfaces. The Calendar Agent additionally has access to CLI subprocess tools for fast read-only queries.

```mermaid
flowchart LR
    subgraph Agents
        RA[Refund Email Agent]
        CA[Calendar Agent]
    end

    subgraph Tools
        MCP[workspace-mcp Server - stdio]
        CLI[workspace-cli - subprocess]
    end

    subgraph Google APIs
        GMAIL[Gmail API]
        GCAL[Google Calendar API]
    end

    RA -->|MCP tools| MCP
    CA -->|MCP tools| MCP
    CA -->|CLI tools| CLI

    MCP -->|OAuth 2.0| GMAIL
    MCP -->|OAuth 2.0| GCAL
    CLI -->|OAuth 2.0| GCAL

    style RA fill:#E74C3C,color:#fff
    style CA fill:#3498DB,color:#fff
    style MCP fill:#9B59B6,color:#fff
    style CLI fill:#1ABC9C,color:#fff
```

### 3.3 Frontend Access

The workspace agents are accessed through the same React frontend that hosts the base customer service agent. The frontend provides a chat interface where users can select the agent type (customer service, refund email, or calendar) and interact via natural language. The backend's `/chat/stream` SSE endpoint routes requests to the appropriate LangGraph agent based on the request payload. For the Refund Email Agent, users can also trigger the fully autonomous batch processing mode through the chat interface.

---

## 4. Implementation — Refund Email Agent

The Refund Email Agent is implemented in `backend/graph/refund_email/` and consists of two modules: `graph.py` (graph construction) and `planner.py` (LLM node with system prompt).

### 4.1 Automated Workflow

The agent follows a six-step workflow when triggered in batch mode:

```text
SEARCH inbox → READ each email → CLASSIFY intent →
DRAFT reply from template → SEND threaded reply → REPORT summary
```

Each step corresponds to one or more tool calls within the ReAct loop. A batch run processing three emails typically requires 10–15 tool calls across multiple loop iterations.

### 4.2 Gmail MCP Tool Inventory

The agent uses Gmail-specific MCP tools loaded from the `workspace-mcp` server and filtered by the `McpClientManager`. The following table summarizes the available tools:

| Tool Name | Purpose | Key Parameters |
|---|---|---|
| `search_gmail_messages` | Search inbox with Gmail query operators | `query`, `max_results` |
| `get_gmail_message_content` | Read full body and metadata of one email | `message_id` |
| `get_gmail_messages_content_batch` | Fetch up to 25 emails in one call | `message_ids`, `format` |
| `send_gmail_message` | Send or reply to an email (threaded) | `to`, `subject`, `body`, `thread_id` |
| `create_gmail_draft` | Save a draft for human review | `to`, `subject`, `body` |
| `get_gmail_thread` | Read full conversation thread | `thread_id` |
| `list_gmail_labels` | List all Gmail labels and folders | *(none)* |

### 4.3 System Prompt

The system prompt defines the agent's identity, workflow rules, classification guide, and behavioral constraints. It is prepended to every LLM call as a `SystemMessage`. The full prompt, extracted from `backend/graph/refund_email/planner.py`:

```python
SYSTEM_PROMPT = f"""You are a Refund Email Agent. You read, classify, and reply to customer
refund and return emails in a Gmail inbox.
The authenticated Gmail account is {user_email}. Always pass this exact email when tools
require an email parameter.

## Batch Workflow (use when asked to process all refund emails)
Follow these steps in order, exactly once per batch command:
1. SEARCH — use search_gmail to find unread emails matching refund or return criteria
2. READ — use get_message to retrieve the full body of each email found
3. CLASSIFY — categorize each email as one of: REFUND_REQUEST, RETURN_REQUEST,
   COMPLAINT, or OTHER
4. DRAFT — compose a professional reply appropriate to the classification
5. SEND — use send_reply or send_message to send the drafted reply
6. REPORT — summarize what was processed: how many emails, their classifications,
   and actions taken

After delivering the REPORT, stop. Do not start another SEARCH unless the user sends
a new request.

## Interactive Queries
For specific questions (e.g. "What refund emails came in today?"), use the same tools
but follow the user's request directly rather than the full batch sequence. Return your
answer once and stop.

## Classification Guide
- REFUND_REQUEST: customer explicitly requests a monetary refund
- RETURN_REQUEST: customer wants to return or exchange an item
- COMPLAINT: customer expresses dissatisfaction without requesting a specific action
- OTHER: anything that does not fit the above categories

Always think aloud before calling a tool — state your reasoning first, then act."""
```

The prompt enforces several key constraints: the agent must follow the six-step workflow in sequence, must not restart the search loop after reporting, must classify each email into exactly one of four categories, and must reason aloud before each tool call. The `user_email` variable is injected from the `WORKSPACE_USER_EMAIL` environment variable to ensure the agent always uses the correct authenticated account.

### 4.4 Graph Construction

The graph is built in `backend/graph/refund_email/graph.py`. The `create_builder` function assembles the three-node topology:

```python
import sqlite3
from contextlib import AbstractAsyncContextManager

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from graph.shared.state import AgentState
from graph.shared.verifier import verifier
from graph.refund_email.planner import make_planner

CHECKPOINT_DB_PATH = "checkpoints_refund_email.db"
RECURSION_LIMIT = 50

_async_checkpointer_cm: AbstractAsyncContextManager[AsyncSqliteSaver] | None = None
_async_graph = None


def create_builder(tools: list) -> StateGraph:
    builder = StateGraph(AgentState)
    builder.add_node("planner", make_planner(tools))
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("verifier", verifier)

    builder.set_entry_point("planner")
    builder.add_conditional_edges(
        "planner", tools_condition, {"tools": "tools", END: "verifier"}
    )
    builder.add_edge("tools", "planner")
    builder.add_edge("verifier", END)
    return builder


def compile_graph(tools: list, checkpointer):
    return (
        create_builder(tools)
        .compile(checkpointer=checkpointer)
        .with_config({"recursion_limit": RECURSION_LIMIT})
    )


async def get_async_graph():
    global _async_checkpointer_cm, _async_graph

    if _async_graph is None:
        from graph.mcp_client import mcp_manager
        tools = mcp_manager.get_tools("refund_email")

        _async_checkpointer_cm = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
        checkpointer = await _async_checkpointer_cm.__aenter__()
        _async_graph = compile_graph(tools, checkpointer)

    return _async_graph


async def close_async_graph() -> None:
    global _async_checkpointer_cm, _async_graph

    if _async_checkpointer_cm is not None:
        await _async_checkpointer_cm.__aexit__(None, None, None)
        _async_checkpointer_cm = None
        _async_graph = None
```

Key design decisions in this code:

- **`RECURSION_LIMIT = 50`**: batch refund processing can legitimately loop across multiple emails, so the limit is set high enough to accommodate search-read-classify-reply cycles for a full inbox without masking infinite loops.
- **`AsyncSqliteSaver`**: provides persistent checkpointing so the agent's state survives process restarts. Each agent type uses its own checkpoint database file.
- **`verifier` node**: inserted between the LLM's final response and `END` to catch tool errors that the LLM may not have acknowledged in its response.
- **Lazy initialization**: `get_async_graph()` creates the graph on first call and caches it, avoiding repeated MCP tool loading on subsequent requests.

### 4.5 Planner Node

The planner node is constructed by `make_planner(tools)`, which returns a closure with access to the tool-bound LLM:

```python
def make_planner(tools: list):
    def planner(state: AgentState, config: RunnableConfig) -> dict:
        configurable = config.get("configurable", {}) if config else {}
        provider = configurable.get("provider", None)
        model = configurable.get("model", None)

        llm_with_tools = create_llm(provider=provider, model=model).bind_tools(tools)
        messages = [SystemMessage(content=build_system_prompt())] + list(state["messages"])
        response = llm_with_tools.invoke(messages, config=config)
        return {"messages": [response]}

    return planner
```

The planner reads `provider` and `model` from the `RunnableConfig`, allowing per-request LLM selection. It prepends the system prompt to every invocation and returns the LLM's response (which may contain tool calls) as a new message appended to the state.

---

## 5. Implementation — Calendar Agent

The Calendar Agent is implemented in `backend/graph/calendar/` and consists of three modules: `graph.py` (graph construction), `planner.py` (LLM node with system prompt), and `cli_tools.py` (CLI subprocess tools).

### 5.1 Dual Tool Strategy

The Calendar Agent has access to two tool surfaces:

```text
Simple read queries  →  workspace-cli bash tools   (fast subprocess, no MCP overhead)
Create/Edit/Delete   →  Calendar MCP tools          (full CRUD, rich JSON response)
```

The LLM selects the appropriate tool surface based on the task type. This dual strategy reduces latency for common read operations (e.g., "What's on today?") while retaining full CRUD capabilities through MCP for write operations.

### 5.2 CLI Tools

The CLI tools are Python functions decorated with `@tool` from `langchain_core.tools`. They delegate to a shared `_run_cli()` subprocess helper. Below is the full implementation of `_run_cli()` and one representative tool function (`today_events`), extracted from `backend/graph/calendar/cli_tools.py`:

```python
import json
import subprocess
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool


def _run_cli(args: list[str], timeout: int = 15) -> str:
    cmd = ["workspace-cli", *args]
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"workspace-cli timed out after {timeout} seconds."
    except (FileNotFoundError, PermissionError):
        return "workspace-cli was not found. Install it and ensure it is available in PATH."

    output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        error_text = (completed.stderr or output or "unknown error").strip()
        return f"workspace-cli failed with exit code {completed.returncode}: {error_text}"

    if not output:
        return "workspace-cli returned no output."

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return output

    return json.dumps(parsed, indent=2, ensure_ascii=False)


def _utc_day_bounds() -> tuple[str, str]:
    now_utc = datetime.now(timezone.utc)
    day_start = datetime.combine(now_utc.date(), datetime.min.time(), timezone.utc)
    next_day_start = day_start + timedelta(days=1)
    return day_start.isoformat(), next_day_start.isoformat()


@tool
def today_events(calendar_id: str = "primary") -> str:
    """List events for the current UTC day from a calendar."""
    time_min, time_max = _utc_day_bounds()
    return _run_cli(
        [
            "call",
            "list_calendar_events",
            "--calendarId",
            calendar_id,
            "--timeMin",
            time_min,
            "--timeMax",
            time_max,
            "--singleEvents",
            "true",
            "--orderBy",
            "startTime",
        ]
    )
```

The `_run_cli()` function handles three error conditions: non-zero exit code, timeout (default 15 seconds), and missing binary. It attempts to parse stdout as JSON for structured output and falls back to raw text. The 15-second timeout prevents the agent from hanging on a stuck subprocess.

The remaining CLI tools follow the same pattern:

| Tool Name | CLI Command Executed | Use Case |
|---|---|---|
| `today_events` | `workspace-cli call list_calendar_events` (today's UTC range) | "What's on today?" |
| `list_events` | `workspace-cli call list_calendar_events` (custom range) | "Show me this week" |
| `list_calendars` | `workspace-cli call list_calendars` | "What calendars do I have?" |
| `get_event` | `workspace-cli call get_calendar_event --eventId <id>` | "Get details for that meeting" |
| `tool_list` | `workspace-cli list` | Debug / tool discovery |

### 5.3 Calendar MCP Tool Inventory

Write and scheduling operations use MCP tools loaded from the `workspace-mcp` server:

| Tool Name | Purpose | Key Parameters |
|---|---|---|
| `create_calendar_event` | Create a new calendar event | `summary`, `start`, `end`, `attendees` |
| `update_calendar_event` | Update an existing event | `calendarId`, `eventId`, `updates` |
| `delete_calendar_event` | Delete an event | `calendarId`, `eventId` |
| `suggest_meeting_time` | Find free slots across attendees | `attendees`, `duration` |
| `respond_to_calendar_event` | RSVP accept / decline / tentative | `calendarId`, `eventId`, `response` |
| `list_calendar_events` | List events in a date range | `calendarId`, `timeMin`, `timeMax` |
| `get_calendar_event` | Get one event by ID | `calendarId`, `eventId` |
| `list_calendars` | List all calendars the user has | *(none)* |

### 5.4 System Prompt

The Calendar Agent's system prompt includes today's date (dynamically computed), the user's timezone, the tool selection guide, and confirmation requirements for destructive operations. The full prompt, extracted from `backend/graph/calendar/planner.py`:

```python
SYSTEM_PROMPT = f"""You are a Calendar Agent.
The authenticated Google account is {user_email}. Always pass this exact email when tools
require an email parameter.
You help users query, schedule, and manage Google Calendar events.

Today is {today} in {timezone_name}.
Resolve relative dates and ranges such as today, tomorrow, this week, next week, and
next Friday yourself using that date context.
Do not ask the user to tell you today's date before using tools for ordinary scheduling
or free-slot requests.

## Workflow
Follow these steps in order depending on the user's request:
1. QUERY — understand what the user needs (today's events, a date range, a specific
   event, etc.)
2. LIST — use today_events or list_events to retrieve relevant events from the calendar
3. DRAFT — compose a clear summary or proposed action (new event details, update, or
   deletion)
4. SCHEDULE — use create_calendar_event, update_calendar_event,
   delete_calendar_event, suggest_meeting_time, or respond_to_calendar_event
   to carry out write or scheduling operations
5. CONFIRM — verify the operation succeeded by checking the tool response
6. RESPOND — report back to the user: what was found or what action was taken

## Available Tools
Read-only (always available via CLI):
- today_events: list all events for the current UTC day
- list_events: list events in a caller-specified time range
- list_calendars: list calendars visible to the authenticated account
- get_event: get full details for a specific event by ID
- tool_list: enumerate available workspace-cli commands

Write/Scheduling (available via MCP when workspace-mcp is running):
- create_calendar_event: create a new calendar event
- update_calendar_event: modify an existing event's details
- delete_calendar_event: remove an event from the calendar
- suggest_meeting_time: find available time slots for scheduling a meeting
- respond_to_calendar_event: respond to an event invitation (accept, decline,
  or tentative)

## Guidelines
- For read-only requests (what's on my calendar?, list events in a range, when is X?),
  use the CLI tools.
- For write requests (schedule a meeting, update or cancel an event), use the MCP tools.
- For free-slot or scheduling requests (find a free slot, suggest a meeting time),
  use the suggest_meeting_time MCP tool.
- For RSVP requests (accept or decline an invitation), use the
  respond_to_calendar_event MCP tool.
- For new event creation, the user has given enough information if they specify a title
  or subject plus a date/day reference plus a start time and either an end time or
  duration. In that case, call create_calendar_event directly.
- If the user omits timezone, assume {timezone_name}. Do not ask for timezone or
  confirmation before creating a new event unless the request is genuinely ambiguous.
- Use a tool instead of asking a clarifying question when the user has already given
  enough information to resolve the relative date and perform the action.
- If a write tool is not available, inform the user that write operations require the
  workspace-mcp service."""
```

Key design elements of this prompt:

- **Dynamic date injection**: `today` and `timezone_name` are computed at runtime using `datetime.now().astimezone()`, so the agent always knows the current date and local timezone without asking the user.
- **Tool selection guide**: explicitly maps request types to tool surfaces (CLI for reads, MCP for writes), guiding the LLM toward the correct tool without hardcoding the selection.
- **Confirmation rules**: the prompt instructs the agent to not ask for unnecessary confirmation on event creation when sufficient information is provided, reducing friction in the conversational flow.
- **Graceful degradation**: if MCP write tools are unavailable, the agent is instructed to inform the user rather than failing silently.

### 5.5 Graph Construction

The Calendar Agent's graph is built in `backend/graph/calendar/graph.py`. It follows the same topology as the Refund Email Agent but merges CLI tools with MCP tools:

```python
import sqlite3
from contextlib import AbstractAsyncContextManager

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import ToolNode, tools_condition

from graph.shared.state import AgentState
from graph.shared.verifier import verifier
from graph.calendar.planner import make_planner
from graph.calendar.cli_tools import (
    today_events,
    list_events,
    list_calendars,
    get_event,
    tool_list,
)
from graph.mcp_client import mcp_manager

CHECKPOINT_DB_PATH = "checkpoints_calendar.db"
RECURSION_LIMIT = 50

CLI_TOOLS = [today_events, list_events, list_calendars, get_event, tool_list]

_async_checkpointer_cm: AbstractAsyncContextManager[AsyncSqliteSaver] | None = None
_async_graph = None


def create_builder(tools: list) -> StateGraph:
    builder = StateGraph(AgentState)
    builder.add_node("planner", make_planner(tools))
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("verifier", verifier)

    builder.set_entry_point("planner")
    builder.add_conditional_edges(
        "planner", tools_condition, {"tools": "tools", END: "verifier"}
    )
    builder.add_edge("tools", "planner")
    builder.add_edge("verifier", END)
    return builder


def compile_graph(tools: list, checkpointer):
    return (
        create_builder(tools)
        .compile(checkpointer=checkpointer)
        .with_config({"recursion_limit": RECURSION_LIMIT})
    )


async def get_async_graph():
    global _async_checkpointer_cm, _async_graph

    if _async_graph is None:
        mcp_tools = mcp_manager.get_tools("calendar")
        if not mcp_tools:
            raise RuntimeError(
                "Calendar MCP tools are not available. "
                "Ensure the workspace MCP service is running before accessing "
                "the calendar graph."
            )
        cli_names = {t.name for t in CLI_TOOLS}
        tools = CLI_TOOLS + [t for t in mcp_tools if t.name not in cli_names]

        _async_checkpointer_cm = AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB_PATH)
        checkpointer = await _async_checkpointer_cm.__aenter__()
        _async_graph = compile_graph(tools, checkpointer)

    return _async_graph


async def close_async_graph() -> None:
    global _async_checkpointer_cm, _async_graph

    if _async_checkpointer_cm is not None:
        await _async_checkpointer_cm.__aexit__(None, None, None)
        _async_checkpointer_cm = None
        _async_graph = None
```

The tool merging logic in `get_async_graph()` is noteworthy: CLI tools are given priority (added first), and any MCP tools with the same name are excluded. This ensures that for read operations where both surfaces offer the same tool (e.g., `list_calendars`), the faster CLI version is used. MCP-only tools (e.g., `create_calendar_event`) are added from the MCP server.

---

## 6. MCP Client Integration

### 6.1 MCP Client Manager

The MCP client is managed by `McpClientManager`, a singleton class defined in `backend/graph/mcp_client.py`. It handles starting the MCP server subprocess, loading tools, filtering tools by agent type, and cleanup.

```python
import os
from typing import Any

_GMAIL_PREFIXES = ("gmail", "message", "send_reply", "list_labels", "label")
_CALENDAR_PREFIXES = ("calendar", "event", "schedule", "meeting", "rsvp",
                      "today_event", "slot")


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

        command = os.environ.get("WORKSPACE_MCP_COMMAND")
        if not command:
            return

        args = (os.environ.get("WORKSPACE_MCP_ARGS", "").split()
                if os.environ.get("WORKSPACE_MCP_ARGS") else [])

        env = {}
        for key in (
            "GOOGLE_OAUTH_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_SECRET",
            "WORKSPACE_MCP_CREDENTIALS_DIR",
            "GOOGLE_MCP_CREDENTIALS_DIR",
            "OAUTHLIB_INSECURE_TRANSPORT",
        ):
            val = os.environ.get(key)
            if val:
                env[key] = val

        connection: dict = {"command": command, "args": args, "transport": "stdio"}
        if env:
            connection["env"] = env

        self._client = MultiServerMCPClient({"workspace": connection})
        self._tools = await self._client.get_tools()

    async def stop(self) -> None:
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
```

### 6.2 Configuration Design

The MCP connection is configured entirely through environment variables, which are assembled into a connection dictionary at startup:

```python
connection = {
    "command": "uvx",                      # or the WORKSPACE_MCP_COMMAND env var
    "args": ["workspace-mcp",
             "--single-user",
             "--tool-tier", "core",
             "--permissions", "gmail:send"],
    "transport": "stdio",
    "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "...",
        "GOOGLE_OAUTH_CLIENT_SECRET": "..."
    }
}
```

Each configuration key serves a specific purpose:

| Key | Purpose |
|---|---|
| `command` | The executable to spawn (e.g., `uvx` for running the MCP server via `uv`) |
| `args` | Command-line arguments passed to the MCP server |
| `--single-user` | Configures OAuth 2.0 for a single Google account |
| `--tool-tier core` | Loads only ~20 essential tools instead of the full 100+ available |
| `--permissions` | Restricts the tool scope to only what each agent needs (e.g., `gmail:send` or `calendar`) |
| `transport: stdio` | Communication via stdin/stdout pipe — local only, no network ports |
| `env` | OAuth credentials injected from the host environment, never hardcoded |

### 6.3 Tool Filtering

The `get_tools()` method filters the loaded MCP tools by agent type using prefix-based name matching. The Refund Email Agent receives only Gmail-related tools, while the Calendar Agent receives only calendar-related tools. This ensures each agent operates within its designated scope — a form of least-privilege enforcement at the tool layer.

### 6.4 Shared State

Both agents use the same `AgentState` TypedDict, defined in `backend/graph/shared/state.py`:

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages:       Annotated[list, add_messages]
    customer_id:    int | None
    memory_context: list[dict] | None
    tool_results:   list[dict] | None
    verification:   dict | None
```

The `messages` field uses the `add_messages` reducer, which appends new messages rather than replacing the list. This is the mechanism that preserves the full conversation history across every iteration of the ReAct loop. The additional fields (`customer_id`, `memory_context`, `tool_results`, `verification`) are used by the base customer service agent and the verifier node; the workspace agents primarily use the `messages` field.

---

## 7. Test Cases

The following test cases validate the functional requirements of both agents against the streamlined test specification. Testing requires a live Google Workspace account with valid OAuth credentials and pre-seeded test data.

### 7.1 Test Data Generation

Test data is seeded into the live Google Workspace account using standalone Python scripts in the `scripts/` directory. These scripts use the Google API Python client directly (not workspace-cli or MCP) and authenticate via pre-cached OAuth credentials stored at `~/.google_workspace_mcp/credentials/`.

**Setup procedure:**

```bash
# One-time OAuth credential setup
python3 scripts/reauth_google.py --secrets ~/Downloads/client_secret_*.json

# Seed calendar events (10 events, Mon–Fri Jun 1–5 2026)
python3 scripts/seed_calendar_events.py --email $WORKSPACE_USER_EMAIL

# Seed test emails (8 emails, 2 per category)
python3 scripts/seed_test_emails.py --email $WORKSPACE_USER_EMAIL
```

All scripts support `--dry-run` to preview actions without mutating data. Cleanup scripts (`clear_seed_calendar.py`, `clear_test_emails.py`) delete only previously seeded data, making the workflow idempotent: clear then re-seed produces a clean test environment with no duplicates.

### 7.2 Calendar Agent Test Cases

The Calendar Agent is validated with 3 test prompts that cover event retrieval, event creation, and free-slot discovery. All prompts are executed against a calendar pre-populated with 10 events spanning Mon Jun 1 – Fri Jun 5, 2026.

**Pre-seeded Calendar Events (Table 1):**

| Date | Time | Event | Covers Test(s) |
|---|---|---|---|
| Mon Jun 1 | 09:00–10:00 | Team Standup | B1, B3 |
| Mon Jun 1 | 14:00–15:00 | Research Meeting | B1, B3 |
| Tue Jun 2 | 10:00–11:00 | Project Review | B1, B3 |
| Tue Jun 2 | 15:00–16:00 | Student Advising | B1 |
| Wed Jun 3 | 09:00–10:30 | Faculty Meeting | B1 |
| Wed Jun 3 | 14:00–15:00 | PhD Progress Review | B1 |
| Thu Jun 4 | 11:00–12:00 | Industry Collaboration Meeting | B1, B3 |
| Thu Jun 4 | 15:00–16:00 | Lab Weekly Meeting | B1 |
| Fri Jun 5 | 09:00–10:00 | Grant Proposal Discussion | B1, B2, B3 |
| Fri Jun 5 | 15:00–16:00 | Research Seminar | B1, B2 |

**Test Prompt B1 — Event Retrieval:**

| Field | Value |
|---|---|
| **Prompt** | "What's on my calendar?" |
| **Expected Behavior** | Agent retrieves all upcoming events; summarizes events by date and time; does not create or modify any calendar entries |
| **Expected Output** | Chronological list of all 10 seeded events with dates and times |

**Test Prompt B2 — Event Creation:**

| Field | Value |
|---|---|
| **Prompt** | "Schedule a team lunch for the coming Friday at noon for 1 hour." |
| **Expected Behavior** | Agent checks calendar availability; creates a new event titled "Team Lunch" on Friday 12:00–13:00; confirms successful creation |
| **Verification** | New "Team Lunch" event appears on Friday between existing events (no conflict with Grant Proposal Discussion at 09:00 or Research Seminar at 15:00) |

**Test Prompt B3 — Free Slot Discovery:**

| Field | Value |
|---|---|
| **Prompt** | "Find a free 30-minute slot for a call with john@example.com this week." |
| **Expected Behavior** | Agent reads existing calendar; identifies available 30-minute windows; proposes one or more candidate slots |
| **Valid Answers** | Monday 10:00–10:30, Monday 10:30–11:00, Tuesday 11:00–11:30, Thursday 13:00–13:30, or any other gap not overlapping seeded events |

**Calendar Agent Success Criteria:**

- Correct retrieval of all existing events
- Correct event creation with no scheduling conflicts
- Accurate free-time discovery (proposed slots do not overlap existing events)
- No runtime errors during execution

### 7.3 Refund Email Agent Test Cases

The Refund Email Agent is validated by processing 8 pre-seeded test emails — 2 per classification category. The agent is invoked with the prompt "Process all refund emails" and must read, classify, and respond to each email autonomously.

**Pre-seeded Test Emails (Table 2):**

| From | Subject | Category | Expected Action | Covers Test(s) |
|---|---|---|---|---|
| alice@customer.com | "I need a refund for my order" | REFUND_REQUEST | Send refund acknowledgement reply | A1 |
| frank@customer.com | "Request refund for damaged item" | REFUND_REQUEST | Send refund acknowledgement reply | A1 |
| bob@customer.com | "Return request for recent purchase" | RETURN_REQUEST | Send return instructions reply | A2 |
| grace@customer.com | "I want to return my order" | RETURN_REQUEST | Send return instructions reply | A2 |
| carol@customer.com | "Terrible experience — still waiting" | COMPLAINT | Send apology and escalation reply | A3 |
| henry@customer.com | "Unacceptable delivery service" | COMPLAINT | Send apology and escalation reply | A3 |
| promo@newsletter.com | "Exclusive deal just for you!" | OTHER | Skip — no reply sent | A4 |
| deals@offers.com | "Your weekly offers inside" | OTHER | Skip — no reply sent | A4 |

**Expected Processing Behavior:**

| Category | Count | Agent Action |
|---|---|---|
| REFUND_REQUEST | 2 | Classify as refund request; generate acknowledgement; send reply |
| RETURN_REQUEST | 2 | Classify as return request; send return instructions; send reply |
| COMPLAINT | 2 | Classify as complaint; send apology and escalation response |
| OTHER | 2 | Classify as other; no automated response; mark as informational |
| **Total Processed** | **8** | |
| **Replies Sent** | **6** | (REFUND_REQUEST + RETURN_REQUEST + COMPLAINT) |
| **Skipped** | **2** | (OTHER — no reply sent) |

**Expected Evaluation Summary:**

```
Processed 8 emails
REFUND_REQUEST: 2
RETURN_REQUEST: 2
COMPLAINT: 2
OTHER: 2
Replies Sent: 6
Skipped: 2
```

**Refund Email Agent Success Criteria:**

- 100% classification accuracy across all 4 categories
- All actionable emails (REFUND_REQUEST, RETURN_REQUEST, COMPLAINT) receive appropriate replies
- OTHER emails are correctly skipped — no reply sent
- Summary statistics match expected counts (8 processed, 6 replied, 2 skipped)
- No duplicate responses

### 7.4 Overall Acceptance Criteria

The system passes testing if:

1. Calendar Agent correctly performs event retrieval, event scheduling, and free-slot discovery across all 3 test prompts.
2. Refund Email Agent correctly classifies all 8 test emails into the expected categories.
3. Refund Email Agent sends appropriate responses for all 6 actionable emails and skips the 2 OTHER emails.
4. Summary reports from both agents match expected results.
5. No runtime errors occur during execution.

> **Note:** Detailed test results are provided in Appendix A (attached separately).

---

## 8. Conclusion

This report presented the design and implementation of the AI Workspace Agent Suite — two autonomous agents that perform real-world Gmail and Google Calendar tasks through natural language. The key contributions and findings are:

1. **The ReAct pattern, implemented via LangGraph's StateGraph, provides a robust foundation for multi-step agent workflows.** The three-node graph topology (`planner → tools → verifier`) is simple to reason about yet powerful enough to handle complex task sequences like batch email processing (10–15 tool calls per run).

2. **MCP with stdio transport delivers a clean separation between agent logic and API integration** while maintaining a strong security posture. The agent code is agnostic to the underlying Google API details — it only sees tool schemas and results. All data stays on-device.

3. **The dual-tool strategy in the Calendar Agent demonstrates a practical optimization pattern.** CLI subprocess calls avoid MCP overhead for read-only queries, while MCP tools handle the full CRUD surface. The LLM's tool selection, guided by the system prompt, reliably chooses the correct surface based on task type.

4. **Tool filtering at the MCP client layer enforces least-privilege access.** Each agent only sees the tools relevant to its domain, reducing the chance of unintended cross-domain tool calls.

5. **The verifier node adds a safety net** that catches tool errors the LLM may not have surfaced in its response, improving reliability for production use.

The system demonstrates that with careful prompt engineering, appropriate tool design, and a well-structured agent graph, LLM-based agents can reliably automate real-world productivity workflows. The architecture is modular — adding a new workspace agent (e.g., Google Drive, Google Contacts) requires only a new graph module with its own system prompt and tool set, while sharing the existing MCP infrastructure and ReAct topology.

---

## Appendix A — Test Results

See attached test results document.
