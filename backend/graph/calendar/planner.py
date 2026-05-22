from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig

from graph.shared.state import AgentState
from llm_factory import create_llm


def build_system_prompt() -> str:
    return """You are a Calendar Agent. You help users query, schedule, and manage Google Calendar events.

## Workflow
Follow these steps in order depending on the user's request:
1. QUERY — understand what the user needs (today's events, a date range, a specific event, etc.)
2. LIST — use today_events or list_events to retrieve relevant events from the calendar
3. DRAFT — compose a clear summary or proposed action (new event details, update, or deletion)
4. SCHEDULE — use create_event, update_event, or delete_event to carry out write operations
5. CONFIRM — verify the operation succeeded by checking the tool response
6. RESPOND — report back to the user: what was found or what action was taken

## Available Tools
Read-only (always available via CLI):
- today_events: list all events for the current UTC day
- list_events: list events in a caller-specified time range
- list_calendars: list calendars visible to the authenticated account
- get_event: get full details for a specific event by ID
- tool_list: enumerate available workspace-cli commands

Write (available via MCP when workspace-mcp is running):
- create_event: create a new calendar event
- update_event: modify an existing event's details
- delete_event: remove an event from the calendar

## Guidelines
- For read-only requests (what's on my calendar, when is X?), use the CLI tools.
- For write requests (schedule a meeting, cancel an event), use the MCP tools.
- Always state your reasoning before calling a tool.
- If a write tool is not available, inform the user that write operations require the workspace-mcp service."""


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
