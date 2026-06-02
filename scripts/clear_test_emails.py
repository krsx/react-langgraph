#!/usr/bin/env python3
"""
Delete all seed test emails from the Gmail inbox so you can start fresh.

Searches for messages from the known seed sender addresses and trashes them.

Usage:
    python3 scripts/clear_test_emails.py [--email you@gmail.com] [--dry-run]
"""

import argparse
import json
import os
import sys
from pathlib import Path

SEED_SENDERS = [
    "alice@customer.com",
    "frank@customer.com",
    "bob@customer.com",
    "grace@customer.com",
    "carol@customer.com",
    "henry@customer.com",
    "eve@customer.com",
    "dave@customer.com",
    "promo@newsletter.com",
    "deals@offers.com",
]


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
    parser = argparse.ArgumentParser(description="Delete seed test emails from Gmail inbox")
    parser.add_argument("--email", default=os.environ.get("WORKSPACE_USER_EMAIL", ""))
    parser.add_argument("--dry-run", action="store_true", help="List what would be deleted without deleting")
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
    service = build("gmail", "v1", credentials=creds)

    query = " OR ".join(f"from:{s}" for s in SEED_SENDERS)
    print(f"Searching: {query}\n")

    results = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
    messages = results.get("messages", [])

    if not messages:
        print("No seed emails found — inbox is already clean.")
        return

    print(f"Found {len(messages)} seed message(s){'  [DRY RUN]' if args.dry_run else ''}:\n")

    for msg in messages:
        mid = msg["id"]
        detail = service.users().messages().get(userId="me", id=mid, format="metadata",
            metadataHeaders=["From", "Subject"]).execute()
        headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
        print(f"  {mid}  From: {headers.get('From','?'):35s}  Subject: {headers.get('Subject','?')}")
        if not args.dry_run:
            service.users().messages().trash(userId="me", id=mid).execute()

    if args.dry_run:
        print(f"\nDRY RUN — would trash {len(messages)} messages. Remove --dry-run to delete.")
    else:
        print(f"\nTrashed {len(messages)} messages. Inbox is clean.")
        print("Now re-seed: python3 scripts/seed_test_emails.py")


if __name__ == "__main__":
    main()