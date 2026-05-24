import json
from langchain_core.messages import AIMessage, ToolMessage

from graph.shared.state import AgentState


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def _parse_tool_content(tm: ToolMessage) -> dict:
    try:
        content = json.loads(tm.content) if isinstance(tm.content, str) else tm.content
        return content if isinstance(content, dict) else {"raw": str(content)}
    except (json.JSONDecodeError, TypeError):
        return {"raw": tm.content}


def verifier(state: AgentState) -> dict:
    messages = state.get("messages") or []

    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    if not tool_messages:
        return {
            "verification": {"valid": True, "checks": ["no tool calls"], "override_message": None},
            "tool_results": [],
        }

    parsed_results = [_parse_tool_content(tm) for tm in tool_messages]

    _MCP_PATTERNS = ("permission denied", "authentication", "rate limit", "quota", "jsonrpc error")

    def _mcp_error(text: str) -> str | None:
        lower = text.lower()
        for pat in _MCP_PATTERNS:
            if pat in lower:
                return text
        return None

    errors = [c["error"] for c in parsed_results if "error" in c]

    mcp_errors: list[str] = []
    for c in parsed_results:
        if isinstance(c, dict):
            for v in c.values():
                if isinstance(v, str):
                    hit = _mcp_error(v)
                    if hit:
                        mcp_errors.append(hit)
        elif isinstance(c, str):
            hit = _mcp_error(c)
            if hit:
                mcp_errors.append(hit)

    for tm in tool_messages:
        if isinstance(tm.content, str) and "error" not in (
            json.loads(tm.content) if _is_json(tm.content) else {}
        ):
            hit = _mcp_error(tm.content)
            if hit:
                mcp_errors.append(hit)

    empty_lookups = [
        f"empty result for '{k}'"
        for c in parsed_results
        for k, v in c.items()
        if isinstance(v, list) and len(v) == 0
    ]
    all_issues = errors + mcp_errors + empty_lookups

    if not all_issues:
        return {
            "verification": {"valid": True, "checks": ["all checks passed"], "override_message": None},
            "tool_results": parsed_results,
        }

    last_ai = next((m for m in reversed(messages) if isinstance(m, AIMessage)), None)
    ai_content = (last_ai.content or "").lower() if last_ai else ""

    error_keywords = [
        "not found", "error", "cannot", "could not", "unable", "invalid",
        "not exist", "not accessible", "no results", "empty",
        "permission", "authentication", "rate limit", "quota", "jsonrpc",
    ]
    llm_acknowledged = any(kw in ai_content for kw in error_keywords)

    override = None if llm_acknowledged else f"I could not complete that request: {all_issues[0]}"

    result: dict = {
        "verification": {
            "valid": False,
            "checks": (
                [f"tool error: {e}" for e in errors]
                + [f"mcp error: {e}" for e in mcp_errors]
                + [f"empty lookup: {e}" for e in empty_lookups]
            ),
            "override_message": override,
        },
        "tool_results": parsed_results,
    }

    if override:
        result["messages"] = [AIMessage(content=override)]

    return result
