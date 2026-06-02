#!/usr/bin/env python3
"""
Delete seed calendar events from Google Calendar so you can re-seed cleanly.

Deletes events whose summary matches any of the known seed event names.

Usage:
    python3 scripts/clear_seed_calendar.py [--email you@gmail.com] [--dry-run]
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SEED_NAMES = {
    "Team Standup",
    "Research Meeting",
    "Project Review",
    "Student Advising",
    "Faculty Meeting",
    "PhD Progress Review",
    "Industry Collaboration Meeting",
    "Lab Weekly Meeting",
    "Grant Proposal Discussion",
    "Research Seminar",
    "Team Lunch",
    # Previous seed runs
    "Client Meeting",
    "Evaluation Meet",
    "Meeting with Stakeholder",
    "Team Meeting",
    "Friday All-Hands",
    "1:1 with Manager",
    "Sprint Planning",
    "Client Review",
}


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


def main():
    parser = argparse.ArgumentParser(description="Delete seed calendar events")
    parser.add_argument("--email", default=os.environ.get("WORKSPACE_USER_EMAIL", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.email:
        print("ERROR: provide --email or set WORKSPACE_USER_EMAIL", file=sys.stderr)
        sys.exit(1)

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: pip install google-api-python-client google-auth", file=sys.stderr)
        sys.exit(1)

    creds = load_credentials(args.email)
    service = build("calendar", "v3", credentials=creds)

    # Search the next 14 days
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=1)).isoformat()
    time_max = (now + timedelta(days=14)).isoformat()

    print(f"Scanning calendar for seed events (±14 days)...\n")

    page_token = None
    deleted = 0
    while True:
        resp = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            maxResults=100,
            pageToken=page_token,
        ).execute()

        for event in resp.get("items", []):
            summary = event.get("summary", "")
            if summary in SEED_NAMES:
                start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "?"))
                print(f"  {'[DRY]' if args.dry_run else '[DEL]'}  {summary:35s}  {start}  id={event['id']}")
                if not args.dry_run:
                    service.events().delete(calendarId="primary", eventId=event["id"]).execute()
                    deleted += 1

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    if args.dry_run:
        print("\nDry run complete — remove --dry-run to delete.")
    else:
        print(f"\nDeleted {deleted} seed event(s).")
        print("Now re-seed: python3 scripts/seed_calendar_events.py --offset +07:00")


if __name__ == "__main__":
    main()