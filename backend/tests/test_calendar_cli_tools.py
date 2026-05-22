import subprocess


def test_run_cli_parses_json_output(monkeypatch):
    from graph.calendar.cli_tools import _run_cli

    captured = {}

    def fake_run(cmd, capture_output, text, timeout, check):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        captured["check"] = check
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"items":[{"id":"evt-1","summary":"Standup"}]}',
            stderr="",
        )

    monkeypatch.setattr("graph.calendar.cli_tools.subprocess.run", fake_run)

    result = _run_cli(["list"])

    assert '"items"' in result
    assert '"id": "evt-1"' in result
    assert captured["cmd"] == ["workspace-cli", "list"]
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["timeout"] == 15
    assert captured["check"] is False


def test_run_cli_timeout_returns_clear_error_message(monkeypatch):
    from graph.calendar.cli_tools import _run_cli

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="workspace-cli", timeout=8)

    monkeypatch.setattr("graph.calendar.cli_tools.subprocess.run", fake_run)

    result = _run_cli(["call", "list_calendars"], timeout=8)

    assert "timed out" in result
    assert "8" in result


def test_run_cli_missing_binary_returns_clear_error_message(monkeypatch):
    from graph.calendar.cli_tools import _run_cli

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("workspace-cli")

    monkeypatch.setattr("graph.calendar.cli_tools.subprocess.run", fake_run)

    result = _run_cli(["list"])

    assert "not found" in result
    assert "workspace-cli" in result


def test_run_cli_non_zero_exit_returns_clear_error_message(monkeypatch):
    from graph.calendar.cli_tools import _run_cli

    def fake_run(cmd, capture_output, text, timeout, check):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=2,
            stdout="",
            stderr="permission denied",
        )

    monkeypatch.setattr("graph.calendar.cli_tools.subprocess.run", fake_run)

    result = _run_cli(["call", "list_calendars"])

    assert "exit code 2" in result
    assert "permission denied" in result


def test_run_cli_falls_back_to_plain_stdout_when_not_json(monkeypatch):
    from graph.calendar.cli_tools import _run_cli

    def fake_run(cmd, capture_output, text, timeout, check):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="plain text output",
            stderr="",
        )

    monkeypatch.setattr("graph.calendar.cli_tools.subprocess.run", fake_run)

    result = _run_cli(["list"])

    assert result == "plain text output"


def test_today_events_passes_today_iso_range_to_run_cli(monkeypatch):
    from graph.calendar import cli_tools

    captured = {}

    monkeypatch.setattr(
        cli_tools,
        "_utc_day_bounds",
        lambda: ("2026-05-22T00:00:00+00:00", "2026-05-23T00:00:00+00:00"),
    )

    def fake_run_cli(args, timeout=15):
        captured["args"] = args
        captured["timeout"] = timeout
        return "ok"

    monkeypatch.setattr(cli_tools, "_run_cli", fake_run_cli)

    result = cli_tools.today_events.invoke({"calendar_id": "team-calendar"})

    assert result == "ok"
    assert captured["args"] == [
        "call",
        "list_calendar_events",
        "--calendarId",
        "team-calendar",
        "--timeMin",
        "2026-05-22T00:00:00+00:00",
        "--timeMax",
        "2026-05-23T00:00:00+00:00",
        "--singleEvents",
        "true",
        "--orderBy",
        "startTime",
    ]
    assert captured["timeout"] == 15


def test_list_events_passes_requested_range_and_options(monkeypatch):
    from graph.calendar import cli_tools

    captured = {}

    def fake_run_cli(args, timeout=15):
        captured["args"] = args
        return "events"

    monkeypatch.setattr(cli_tools, "_run_cli", fake_run_cli)

    result = cli_tools.list_events.invoke(
        {
            "time_min": "2026-05-22T00:00:00Z",
            "time_max": "2026-05-23T00:00:00Z",
            "max_results": 25,
            "calendar_id": "primary",
        }
    )

    assert result == "events"
    assert captured["args"] == [
        "call",
        "list_calendar_events",
        "--calendarId",
        "primary",
        "--timeMin",
        "2026-05-22T00:00:00Z",
        "--timeMax",
        "2026-05-23T00:00:00Z",
        "--maxResults",
        "25",
        "--singleEvents",
        "true",
        "--orderBy",
        "startTime",
    ]


def test_list_calendars_delegates_to_workspace_cli(monkeypatch):
    from graph.calendar import cli_tools

    captured = {}

    def fake_run_cli(args, timeout=15):
        captured["args"] = args
        return "calendars"

    monkeypatch.setattr(cli_tools, "_run_cli", fake_run_cli)

    result = cli_tools.list_calendars.invoke({})

    assert result == "calendars"
    assert captured["args"] == ["call", "list_calendars"]


def test_get_event_delegates_event_and_calendar_identifiers(monkeypatch):
    from graph.calendar import cli_tools

    captured = {}

    def fake_run_cli(args, timeout=15):
        captured["args"] = args
        return "event"

    monkeypatch.setattr(cli_tools, "_run_cli", fake_run_cli)

    result = cli_tools.get_event.invoke(
        {"event_id": "evt-123", "calendar_id": "team-calendar"}
    )

    assert result == "event"
    assert captured["args"] == [
        "call",
        "get_calendar_event",
        "--eventId",
        "evt-123",
        "--calendarId",
        "team-calendar",
    ]


def test_tool_list_delegates_to_workspace_cli_list(monkeypatch):
    from graph.calendar import cli_tools

    captured = {}

    def fake_run_cli(args, timeout=15):
        captured["args"] = args
        return "tools"

    monkeypatch.setattr(cli_tools, "_run_cli", fake_run_cli)

    result = cli_tools.tool_list.invoke({})

    assert result == "tools"
    assert captured["args"] == ["list"]
