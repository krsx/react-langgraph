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


@tool
def list_events(
    time_min: str,
    time_max: str | None = None,
    max_results: int = 10,
    calendar_id: str = "primary",
) -> str:
    """List events in a caller-provided range from a calendar."""
    args = [
        "call",
        "list_calendar_events",
        "--calendarId",
        calendar_id,
        "--timeMin",
        time_min,
    ]
    if time_max:
        args.extend(["--timeMax", time_max])
    args.extend(
        [
            "--maxResults",
            str(max_results),
            "--singleEvents",
            "true",
            "--orderBy",
            "startTime",
        ]
    )
    return _run_cli(args)


@tool
def list_calendars() -> str:
    """List calendars available to the authenticated account."""
    return _run_cli(["call", "list_calendars"])


@tool
def get_event(event_id: str, calendar_id: str = "primary") -> str:
    """Get full details for a calendar event by event ID."""
    return _run_cli(
        [
            "call",
            "get_calendar_event",
            "--eventId",
            event_id,
            "--calendarId",
            calendar_id,
        ]
    )


@tool
def tool_list() -> str:
    """List available workspace-cli tools for debugging and discovery."""
    return _run_cli(["list"])
