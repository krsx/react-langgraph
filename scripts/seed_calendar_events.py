#!/usr/bin/env python3
"""
Seed test calendar events for Calendar Agent test cases (test-cases-extend.md, Set B).

Usage:
    pip install google-api-python-client google-auth
    python scripts/seed_calendar_events.py [--dry-run]

Events created:
  B1, B4  Team Standup         — today 09:00–09:30
  B1, B7  Client Review        — today 14:00–15:00
  B1      1:1 with Manager     — today 17:30–18:00
  B2      Sprint Planning      — tomorrow 10:00–11:00
  B9      Friday All-Hands     — this Friday 15:00–16:00  (RSVP event, imported with external organizer)
"""

import argparse
import json
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def _get_local_offset_str() -> str:
    local_now = datetime.now().astimezone()
    total_seconds = int(local_now.utcoffset().total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    h, m = divmod(abs(total_seconds), 3600)
    return f"{sign}{h:02d}:{m // 60:02d}"


def _dt(d: date, hour: int, minute: int, offset: str) -> str:
    return f"{d.isoformat()}T{hour:02d}:{minute:02d}:00{offset}"


def _this_friday(today: date) -> date:
    days_ahead = (4 - today.weekday()) % 7
    return today + timedelta(days=days_ahead if days_ahead > 0 else 7)


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


def insert_event(service, body: dict) -> str:
    result = service.events().insert(calendarId="primary", body=body).execute()
    return result["id"]


def import_event(service, body: dict) -> str:
    """Use events.import to create an event with an external organizer (needed for RSVP test)."""
    result = service.events().import_(calendarId="primary", body=body).execute()
    return result["id"]


def build_regular_event(summary: str, start_dt: str, end_dt: str) -> dict:
    return {
        "summary": summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
        "status": "confirmed",
    }


def build_rsvp_event(summary: str, start_dt: str, end_dt: str, user_email: str) -> dict:
    """
    Build an event that passes all three checks in _rsvp_event_impl:
      1. attendees list is non-empty
      2. organizer.self is False  (external organizer)
      3. user appears in attendees with self=True

    events.import_ allows setting an external organizer email so the
    authenticated user is NOT flagged as organizer.self = True.
    """
    fake_organizer = "all-hands-organizer@company-internal.com"
    return {
        "summary": summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
        "iCalUID": f"{uuid.uuid4()}@company-internal.com",
        "status": "confirmed",
        "organizer": {"email": fake_organizer},
        "attendees": [
            {"email": fake_organizer, "responseStatus": "accepted", "organizer": True},
            {"email": user_email, "responseStatus": "needsAction"},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Seed test calendar events for Calendar Agent")
    parser.add_argument(
        "--email",
        default=os.environ.get("WORKSPACE_USER_EMAIL", ""),
        help="Authenticated Gmail address (default: $WORKSPACE_USER_EMAIL)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without creating")
    args = parser.parse_args()

    if not args.email:
        print("ERROR: provide --email or set WORKSPACE_USER_EMAIL", file=sys.stderr)
        sys.exit(1)

    offset = _get_local_offset_str()
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    friday = _this_friday(today)

    events = [
        ("insert", "Team Standup",     _dt(today,    9,  0, offset), _dt(today,    9, 30, offset), "B1, B4"),
        ("insert", "Client Review",    _dt(today,   14,  0, offset), _dt(today,   15,  0, offset), "B1, B7"),
        ("insert", "1:1 with Manager", _dt(today,   17, 30, offset), _dt(today,   18,  0, offset), "B1"),
        ("insert", "Sprint Planning",  _dt(tomorrow,10,  0, offset), _dt(tomorrow,11,  0, offset), "B2"),
        ("rsvp",   "Friday All-Hands", _dt(friday,  15,  0, offset), _dt(friday,  16,  0, offset), "B9 (RSVP invitation)"),
    ]

    if args.dry_run:
        print(f"DRY RUN — would create {len(events)} events for {args.email} (offset {offset}):\n")
        for kind, name, start, end, covers in events:
            tag = "[RSVP/import]" if kind == "rsvp" else "[insert]    "
            print(f"  {tag}  {name:22s}  {start}  →  {end}    covers: {covers}")
        return

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: install google-api-python-client: pip install google-api-python-client google-auth", file=sys.stderr)
        sys.exit(1)

    print(f"Loading credentials for {args.email}...")
    creds = load_credentials(args.email)
    service = build("calendar", "v3", credentials=creds)

    print(f"Creating {len(events)} seed events (offset {offset})...\n")
    for kind, name, start, end, covers in events:
        if kind == "rsvp":
            body = build_rsvp_event(name, start, end, args.email)
            event_id = import_event(service, body)
            print(f"  OK  [RSVP/import]  {name:22s}  id={event_id}  covers={covers}")
        else:
            body = build_regular_event(name, start, end)
            event_id = insert_event(service, body)
            print(f"  OK  [insert]       {name:22s}  id={event_id}  covers={covers}")

    print(f"\nDone. {len(events)} events created.")
    print("Friday All-Hands was imported with an external organizer so RSVP (B9) works.")
    print("Team Lunch (B5, B6) is created during the test itself — no seeding needed.")


if __name__ == "__main__":
    main()