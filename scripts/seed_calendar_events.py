#!/usr/bin/env python3
"""
Seed test calendar events for Calendar Agent test cases (Testing_project_2.pdf §1).

Usage:
    pip install google-api-python-client google-auth
    python scripts/seed_calendar_events.py [--dry-run]

Events created (Mon Jun 1 – Fri Jun 5, 2026):
  Mon Jun 1  09:00–10:00  Team Standup
  Mon Jun 1  14:00–15:00  Research Meeting
  Tue Jun 2  10:00–11:00  Project Review
  Tue Jun 2  15:00–16:00  Student Advising
  Wed Jun 3  09:00–10:30  Faculty Meeting
  Wed Jun 3  14:00–15:00  PhD Progress Review
  Thu Jun 4  11:00–12:00  Industry Collaboration Meeting
  Thu Jun 4  15:00–16:00  Lab Weekly Meeting
  Fri Jun 5  09:00–10:00  Grant Proposal Discussion
  Fri Jun 5  15:00–16:00  Research Seminar
"""

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


def _get_local_offset_str() -> str:
    local_now = datetime.now().astimezone()
    total_seconds = int(local_now.utcoffset().total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    h, m = divmod(abs(total_seconds), 3600)
    return f"{sign}{h:02d}:{m // 60:02d}"


def _dt(d: date, hour: int, minute: int, offset: str) -> str:
    return f"{d.isoformat()}T{hour:02d}:{minute:02d}:00{offset}"


def load_credentials(email: str):
    cred_path = Path.home() / ".google_workspace_mcp" / "credentials" / f"{email}.json"
    if not cred_path.exists():
        print(f"ERROR: credentials not found at {cred_path}", file=sys.stderr)
        sys.exit(1)

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    raw = json.loads(cred_path.read_text())
    creds = Credentials(
        token=raw.get("token"),
        refresh_token=raw.get("refresh_token"),
        token_uri=raw.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=raw.get("client_id"),
        client_secret=raw.get("client_secret"),
        scopes=raw.get("scopes"),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def insert_event(service, summary: str, start_dt: str, end_dt: str) -> str:
    body = {
        "summary": summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
        "status": "confirmed",
    }
    result = service.events().insert(calendarId="primary", body=body).execute()
    return result["id"]


def main():
    parser = argparse.ArgumentParser(description="Seed test calendar events for Calendar Agent")
    parser.add_argument(
        "--email",
        default=os.environ.get("WORKSPACE_USER_EMAIL", ""),
        help="Authenticated Gmail address (default: $WORKSPACE_USER_EMAIL)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without creating")
    parser.add_argument(
        "--offset",
        default=None,
        metavar="±HH:MM",
        help="Timezone offset for event times, e.g. +07:00 for ICT (default: system local)",
    )
    args = parser.parse_args()

    if not args.email:
        print("ERROR: provide --email or set WORKSPACE_USER_EMAIL", file=sys.stderr)
        sys.exit(1)

    offset = args.offset if args.offset else _get_local_offset_str()
    print(f"Using timezone offset: {offset}")

    # Week of Jun 1–5, 2026 — derive from today so the script stays correct
    # regardless of when it's run during that week.
    today = datetime.now().date()
    # Find Monday of the current week
    monday = today - timedelta(days=today.weekday())
    tuesday   = monday + timedelta(days=1)
    wednesday = monday + timedelta(days=2)
    thursday  = monday + timedelta(days=3)
    friday    = monday + timedelta(days=4)

    events = [
        # Mon Jun 1
        ("Team Standup",                   _dt(monday,    9,  0, offset), _dt(monday,    10,  0, offset), "B1, B3"),
        ("Research Meeting",               _dt(monday,   14,  0, offset), _dt(monday,    15,  0, offset), "B1, B3"),
        # Tue Jun 2
        ("Project Review",                 _dt(tuesday,  10,  0, offset), _dt(tuesday,   11,  0, offset), "B1, B3"),
        ("Student Advising",               _dt(tuesday,  15,  0, offset), _dt(tuesday,   16,  0, offset), "B1"),
        # Wed Jun 3
        ("Faculty Meeting",                _dt(wednesday, 9,  0, offset), _dt(wednesday, 10, 30, offset), "B1"),
        ("PhD Progress Review",            _dt(wednesday,14,  0, offset), _dt(wednesday, 15,  0, offset), "B1"),
        # Thu Jun 4
        ("Industry Collaboration Meeting", _dt(thursday, 11,  0, offset), _dt(thursday,  12,  0, offset), "B1, B3"),
        ("Lab Weekly Meeting",             _dt(thursday, 15,  0, offset), _dt(thursday,  16,  0, offset), "B1"),
        # Fri Jun 5
        ("Grant Proposal Discussion",      _dt(friday,    9,  0, offset), _dt(friday,    10,  0, offset), "B1, B2, B3"),
        ("Research Seminar",               _dt(friday,   15,  0, offset), _dt(friday,    16,  0, offset), "B1, B2"),
    ]

    if args.dry_run:
        print(f"DRY RUN — would create {len(events)} events for {args.email} (offset {offset}):\n")
        for name, start, end, covers in events:
            print(f"  {name:35s}  {start}  →  {end}    covers: {covers}")
        print(f"\nMonday = {monday}  (week of Jun 1–5)")
        return

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: install google-api-python-client: pip install google-api-python-client google-auth", file=sys.stderr)
        sys.exit(1)

    print(f"Loading credentials for {args.email}...")
    creds = load_credentials(args.email)
    service = build("calendar", "v3", credentials=creds)

    print(f"Creating {len(events)} seed events (week of {monday}, offset {offset})...\n")
    for name, start, end, covers in events:
        event_id = insert_event(service, name, start, end)
        print(f"  OK  {name:35s}  id={event_id}  covers={covers}")

    print(f"\nDone. {len(events)} events created for Mon {monday} – Fri {friday}.")
    print("Team Lunch (B2) will be created by the agent during the test — no seeding needed.")


if __name__ == "__main__":
    main()