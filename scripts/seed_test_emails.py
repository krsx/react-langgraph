#!/usr/bin/env python3
"""
Seed test emails for Refund Email Agent test cases (Testing_project_2.pdf §2).

Inserts synthetic emails directly into the authenticated Gmail inbox using
users.messages.insert — no SMTP required, arbitrary From headers allowed.

Dataset: 8 emails — 2 per category
  A1  alice@customer.com   — REFUND_REQUEST
  A1  frank@customer.com   — REFUND_REQUEST
  A2  bob@customer.com     — RETURN_REQUEST
  A2  grace@customer.com   — RETURN_REQUEST
  A3  carol@customer.com   — COMPLAINT
  A3  henry@customer.com   — COMPLAINT
  A4  promo@newsletter.com — OTHER
  A4  deals@offers.com     — OTHER

Expected agent summary after processing:
  REFUND_REQUEST : 2   (replies sent)
  RETURN_REQUEST : 2   (replies sent)
  COMPLAINT      : 2   (replies sent)
  OTHER          : 2   (skipped — no reply)
  Replies Sent   : 6
  Skipped        : 2

Usage:
    pip install google-api-python-client google-auth
    python scripts/seed_test_emails.py [--email you@gmail.com] [--dry-run]
"""

import argparse
import base64
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path


SEEDS = [
    # ── REFUND_REQUEST ─────────────────────────────────────────────────────────
    {
        "from_addr": "alice@customer.com",
        "from_name": "Alice Customer",
        "subject": "I need a refund for my order",
        "body": (
            "Hi,\n\n"
            "I placed order #12345 two weeks ago and I have not received it.\n"
            "I would like to request a full refund to my original payment method.\n\n"
            "Please let me know the next steps.\n\n"
            "Thanks,\nAlice"
        ),
        "classification": "REFUND_REQUEST",
        "covers": "A1",
    },
    {
        "from_addr": "frank@customer.com",
        "from_name": "Frank Miller",
        "subject": "Request refund for damaged item",
        "body": (
            "Hello,\n\n"
            "I received order #54321 last week but the item arrived damaged.\n"
            "The packaging was crushed and the product inside is broken.\n"
            "I am requesting a full refund for this order.\n\n"
            "Please advise on how to proceed.\n\n"
            "Regards,\nFrank"
        ),
        "classification": "REFUND_REQUEST",
        "covers": "A1",
    },
    # ── RETURN_REQUEST ─────────────────────────────────────────────────────────
    {
        "from_addr": "bob@customer.com",
        "from_name": "Bob Shopper",
        "subject": "Return request for recent purchase",
        "body": (
            "Hello,\n\n"
            "I received order #67890 yesterday but it is the wrong size.\n"
            "I'd like to return the item I received and exchange it for a medium.\n"
            "Could you send me a prepaid return label?\n\n"
            "Best,\nBob"
        ),
        "classification": "RETURN_REQUEST",
        "covers": "A2",
    },
    {
        "from_addr": "grace@customer.com",
        "from_name": "Grace Lee",
        "subject": "I want to return my order",
        "body": (
            "Hi,\n\n"
            "I ordered a jacket (order #22222) but the colour is completely different "
            "from what was shown on the website.\n"
            "I would like to return it and receive a full refund or exchange.\n"
            "Please let me know the return process.\n\n"
            "Thank you,\nGrace"
        ),
        "classification": "RETURN_REQUEST",
        "covers": "A2",
    },
    # ── COMPLAINT ──────────────────────────────────────────────────────────────
    {
        "from_addr": "carol@customer.com",
        "from_name": "Carol Unhappy",
        "subject": "Terrible experience — still waiting",
        "body": (
            "To whom it may concern,\n\n"
            "This is completely unacceptable service. I have been waiting three weeks "
            "for my order and no one has responded to my previous two emails.\n"
            "I am extremely disappointed and expect an immediate response.\n\n"
            "Carol"
        ),
        "classification": "COMPLAINT",
        "covers": "A3",
    },
    {
        "from_addr": "henry@customer.com",
        "from_name": "Henry Walsh",
        "subject": "Unacceptable delivery service",
        "body": (
            "Hello,\n\n"
            "I am deeply dissatisfied with the delivery service for my order #33333.\n"
            "The courier left the package in the rain without any notification and "
            "the contents are now completely ruined.\n"
            "This is totally unacceptable and I expect this to be addressed urgently.\n\n"
            "Henry"
        ),
        "classification": "COMPLAINT",
        "covers": "A3",
    },
    # ── OTHER ──────────────────────────────────────────────────────────────────
    {
        "from_addr": "promo@newsletter.com",
        "from_name": "Newsletter Deals",
        "subject": "Exclusive deal just for you!",
        "body": (
            "Hi valued customer,\n\n"
            "Don't miss our BIGGEST SALE of the year — up to 70% off!\n"
            "Use code SAVE70 at checkout. Offer expires midnight tonight.\n\n"
            "Shop now: https://example.com/sale\n\n"
            "Unsubscribe: https://example.com/unsubscribe"
        ),
        "classification": "OTHER",
        "covers": "A4",
    },
    {
        "from_addr": "deals@offers.com",
        "from_name": "Weekly Offers",
        "subject": "Your weekly offers inside",
        "body": (
            "Hello,\n\n"
            "Your personalised weekly deals are ready!\n"
            "Check out this week's top picks curated just for you.\n\n"
            "View offers: https://example.com/weekly\n\n"
            "To unsubscribe reply STOP."
        ),
        "classification": "OTHER",
        "covers": "A4",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _format_date(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def build_raw_message(
    from_addr: str,
    from_name: str,
    to_addr: str,
    subject: str,
    body: str,
    date: datetime | None = None,
) -> str:
    """Return base64url-encoded raw RFC-2822 message."""
    if date is None:
        date = datetime.now(timezone.utc)

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = _format_date(date)
    msg["Message-ID"] = f"<{uuid.uuid4().hex}@seed.test>"

    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def load_credentials(email: str):
    cred_path = Path.home() / ".google_workspace_mcp" / "credentials" / f"{email}.json"
    if not cred_path.exists():
        print(f"ERROR: credentials not found at {cred_path}", file=sys.stderr)
        print("Run workspace-mcp --single-user once on the host to complete OAuth.", file=sys.stderr)
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


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed test emails for Refund Email Agent")
    parser.add_argument(
        "--email",
        default=os.environ.get("WORKSPACE_USER_EMAIL", ""),
        help="Authenticated Gmail address (default: $WORKSPACE_USER_EMAIL)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan without inserting")
    args = parser.parse_args()

    if not args.email:
        print("ERROR: provide --email or set WORKSPACE_USER_EMAIL", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"DRY RUN — would insert {len(SEEDS)} messages to {args.email}:\n")
        for s in SEEDS:
            print(f"  [{s['classification']:16s}]  {s['from_addr']:30s}  {s['subject']}")
        print(f"\nTotal: {len(SEEDS)} emails")
        print("Expected after agent run: 6 replies sent, 2 skipped (OTHER)")
        return

    try:
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: google-api-python-client not installed.", file=sys.stderr)
        print("Run: pip install google-api-python-client google-auth", file=sys.stderr)
        sys.exit(1)

    print(f"Loading credentials for {args.email}...")
    creds = load_credentials(args.email)
    service = build("gmail", "v1", credentials=creds)

    print(f"Inserting {len(SEEDS)} seed messages into {args.email}...\n")

    counts: dict[str, int] = {}
    for seed in SEEDS:
        raw = build_raw_message(
            from_addr=seed["from_addr"],
            from_name=seed["from_name"],
            to_addr=args.email,
            subject=seed["subject"],
            body=seed["body"],
        )
        result = service.users().messages().insert(
            userId="me",
            body={"raw": raw, "labelIds": ["INBOX", "UNREAD"]},
        ).execute()
        gid = result["id"]
        counts[seed["classification"]] = counts.get(seed["classification"], 0) + 1
        print(f"  OK  [{seed['classification']:16s}]  {seed['from_addr']:30s}  gmail_id={gid}")

    print(f"\nDone. {len(SEEDS)} messages inserted as UNREAD in INBOX.")
    print("\nCategory breakdown:")
    for cat, n in counts.items():
        print(f"  {cat:16s}: {n}")
    print("\nExpected agent summary:")
    print("  Replies Sent : 6  (REFUND_REQUEST + RETURN_REQUEST + COMPLAINT)")
    print("  Skipped      : 2  (OTHER — no reply sent)")


if __name__ == "__main__":
    main()