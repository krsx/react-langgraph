import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool


def _run_cli(args: list[str], timeout: int = 30) -> str:
    from graph.mcp_client import _MCP_LOCAL_URL

    cmd = ["workspace-cli", "--url", _MCP_LOCAL_URL, *args]
    env = {**os.environ, "WORKSPACE_MCP_URL": _MCP_LOCAL_URL, "OAUTHLIB_INSECURE_TRANSPORT": "1"}
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return f"workspace-cli timed out after {timeout} seconds."
    except (FileNotFoundError, PermissionError):
        return "workspace-cli was not found. Install workspace-mcp and ensure it is in PATH."

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


def _email() -> str:
    return os.environ.get("WORKSPACE_USER_EMAIL", "")


@tool
def today_events(calendar_id: str = "primary") -> str:
    """List events for the current UTC day from a calendar."""
    time_min, time_max = _utc_day_bounds()
    return _run_cli([
        "call", "get_events",
        f"calendar_id={calendar_id}",
        f"time_min={time_min}",
        f"time_max={time_max}",
        f"user_google_email={_email()}",
    ])


@tool
def list_events(
    time_min: str,
    time_max: str | None = None,
    max_results: int = 10,
    calendar_id: str = "primary",
) -> str:
    """List events in a caller-provided range from a calendar."""
    args = [
        "call", "get_events",
        f"calendar_id={calendar_id}",
        f"time_min={time_min}",
        f"max_results={max_results}",
        f"user_google_email={_email()}",
    ]
    if time_max:
        args.append(f"time_max={time_max}")
    return _run_cli(args)


@tool
def list_calendars() -> str:
    """List calendars available to the authenticated account."""
    return _run_cli([
        "call", "list_calendars",
        f"user_google_email={_email()}",
    ])


@tool
def get_event(event_id: str, calendar_id: str = "primary") -> str:
    """Get full details for a calendar event by event ID."""
    return _run_cli([
        "call", "get_events",
        f"event_id={event_id}",
        f"calendar_id={calendar_id}",
        f"user_google_email={_email()}",
    ])


@tool
def tool_list() -> str:
    """List available workspace-cli tools for debugging and discovery."""
    return _run_cli(["list"])