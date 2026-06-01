#!/usr/bin/env python3
"""
Seed test emails for Refund Email Agent test cases (Report 2 / test-cases-extend.md, Set A).

Inserts synthetic emails directly into the authenticated Gmail inbox using
users.messages.insert — no SMTP required, arbitrary From headers allowed.

Coverage:
  A3  msg_refund_001    alice — REFUND_REQUEST (plain email)
  A4  msg_return_001    bob   — RETURN_REQUEST (plain email)
  A5  msg_complaint_001 carol — COMPLAINT      (plain email)
  A6  msg_promo_001     promo — OTHER           (plain email)
  A8  msg_ambiguous_001 dave  — AMBIGUOUS       (plain email → agent drafts, not sends)
  A7  msg_thread_parent eve   — REFUND_REQUEST  (first message in thread)
  A7  msg_thread_001    eve   — REFUND_REQUEST  (follow-up in same thread → tests in-thread reply)
  A9                          — batch loop: alice + bob + carol + eve(thread child) = 4 actionable
  A10                         — summary report: produced after batch completes (no extra seed)
  A11 msg_thread_parent + msg_thread_001 together as one thread → get_gmail_thread returns both

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
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from pathlib import Path


# ── Plain (single-message) seeds ──────────────────────────────────────────────

FLAT_SEEDS = [
    {
        "id": "msg_refund_001",
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
        "covers": "A3, A7, A9",
    },
    {
        "id": "msg_return_001",
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
        "covers": "A4, A7, A9",
    },
    {
        "id": "msg_complaint_001",
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
        "covers": "A5, A7, A9",
    },
    {
        "id": "msg_promo_001",
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
        "covers": "A6",
    },
    {
        "id": "msg_ambiguous_001",
        "from_addr": "dave@customer.com",
        "from_name": "Dave Uncertain",
        "subject": "Refund? Or maybe store credit?",
        "body": (
            "Hi there,\n\n"
            "I'm not totally sure what I want — I was thinking about a refund for "
            "order #11111, but actually store credit might work too if the refund "
            "takes too long. Or maybe I should just exchange it for something else?\n"
            "I'm also a bit annoyed at the delivery delay, so there's that too.\n"
            "Can you help me figure out the best option?\n\n"
            "Thanks,\nDave"
        ),
        "classification": "AMBIGUOUS",
        "covers": "A8 (agent should create_gmail_draft, not send_gmail_message)",
    },
]


# ── Thread seed — two messages that form one conversation ──────────────────────
# Parent is inserted first; its thread_id is then used for the child.
# Together they cover A7 (agent replies in-thread) and A11 (get_gmail_thread
# returns the full conversation history).

THREAD_SEED = {
    "parent": {
        "id": "msg_thread_parent",
        "from_addr": "eve@customer.com",
        "from_name": "Eve Returning",
        "subject": "Refund for order #99999 — not received",
        "body": (
            "Hi,\n\n"
            "I placed order #99999 on the 1st of this month and it still hasn't "
            "arrived. The tracking page shows 'in transit' for the past 10 days "
            "with no movement.\n"
            "I would like to request a refund if the item cannot be delivered "
            "within the next two business days.\n\n"
            "Thanks,\nEve"
        ),
        "classification": "REFUND_REQUEST",
        "covers": "A7 (parent message establishes thread), A11",
    },
    "child": {
        "id": "msg_thread_001",
        "from_addr": "eve@customer.com",
        "from_name": "Eve Returning",
        "subject": "Re: Refund for order #99999 — not received",
        "body": (
            "Hi,\n\n"
            "Just following up on my earlier message. I still haven't heard back "
            "about my refund request for order #99999. It has now been over a week "
            "and I need this resolved before the end of the month.\n\n"
            "Please provide an update at your earliest convenience.\n\n"
            "Thanks,\nEve"
        ),
        "classification": "REFUND_REQUEST",
        "covers": "A7 (agent must reply with parent thread_id), A9, A11",
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_message_id(domain: str = "seed.test") -> str:
    return f"<{uuid.uuid4().hex}@{domain}>"


def _format_date(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def build_raw_message(
    from_addr: str,
    from_name: str,
    to_addr: str,
    subject: str,
    body: str,
    message_id: str | None = None,
    in_reply_to: str | None = None,
    references: str | None = None,
    date: datetime | None = None,
) -> tuple[str, str]:
    """Return (raw_b64, message_id) for a single message."""
    if message_id is None:
        message_id = _make_message_id()
    if date is None:
        date = datetime.now(timezone.utc)

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = _format_date(date)
    msg["Message-ID"] = message_id
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
    if references:
        msg["References"] = references

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return raw, message_id


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


# ── Insertion helpers ──────────────────────────────────────────────────────────

def insert_flat(service, to_addr: str, seed: dict) -> str:
    raw, _ = build_raw_message(
        from_addr=seed["from_addr"],
        from_name=seed["from_name"],
        to_addr=to_addr,
        subject=seed["subject"],
        body=seed["body"],
    )
    result = service.users().messages().insert(
        userId="me",
        body={"raw": raw, "labelIds": ["INBOX", "UNREAD"]},
    ).execute()
    return result["id"]


def insert_thread(service, to_addr: str, thread: dict) -> tuple[str, str, str]:
    """Insert parent then child into the same thread.

    Returns (parent_gmail_id, child_gmail_id, thread_id).
    """
    parent = thread["parent"]
    child = thread["child"]

    # Parent — establish the thread
    parent_msg_id = _make_message_id()
    parent_date = datetime.now(timezone.utc) - timedelta(days=3)
    parent_raw, _ = build_raw_message(
        from_addr=parent["from_addr"],
        from_name=parent["from_name"],
        to_addr=to_addr,
        subject=parent["subject"],
        body=parent["body"],
        message_id=parent_msg_id,
        date=parent_date,
    )
    parent_result = service.users().messages().insert(
        userId="me",
        body={"raw": parent_raw, "labelIds": ["INBOX", "UNREAD"]},
    ).execute()
    parent_gmail_id = parent_result["id"]
    thread_id = parent_result["threadId"]

    # Child — reply into the same thread
    child_date = datetime.now(timezone.utc)
    child_raw, _ = build_raw_message(
        from_addr=child["from_addr"],
        from_name=child["from_name"],
        to_addr=to_addr,
        subject=child["subject"],
        body=child["body"],
        in_reply_to=parent_msg_id,
        references=parent_msg_id,
        date=child_date,
    )
    child_result = service.users().messages().insert(
        userId="me",
        body={"raw": child_raw, "threadId": thread_id, "labelIds": ["INBOX", "UNREAD"]},
    ).execute()
    child_gmail_id = child_result["id"]

    return parent_gmail_id, child_gmail_id, thread_id


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

    total = len(FLAT_SEEDS) + 2  # 5 flat + 2 thread messages

    if args.dry_run:
        print(f"DRY RUN — would insert {total} messages to {args.email}:\n")
        print("  Flat emails (single-message):")
        for s in FLAT_SEEDS:
            print(f"    [{s['classification']:16s}]  {s['from_addr']:30s}  {s['subject']}")
        print("\n  Thread emails (2-message conversation — covers A7 + A11):")
        for key in ("parent", "child"):
            m = THREAD_SEED[key]
            print(f"    [{m['classification']:16s}]  {m['from_addr']:30s}  {m['subject']}")
            print(f"       covers: {m['covers']}")
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

    print(f"Inserting {total} seed messages into {args.email}...\n")

    # Insert flat emails
    for seed in FLAT_SEEDS:
        gid = insert_flat(service, args.email, seed)
        print(f"  OK  {seed['id']:22s}  gmail_id={gid:20s}  [{seed['classification']}]")

    # Insert threaded emails
    print()
    parent_gid, child_gid, thread_id = insert_thread(service, args.email, THREAD_SEED)
    print(f"  OK  {THREAD_SEED['parent']['id']:22s}  gmail_id={parent_gid:20s}  [REFUND_REQUEST]  (thread parent, 3 days ago)")
    print(f"  OK  {THREAD_SEED['child']['id']:22s}  gmail_id={child_gid:20s}  [REFUND_REQUEST]  (thread child,  threadId={thread_id})")

    print(f"\nDone. {total} messages inserted as UNREAD in INBOX.")
    print()
    print("Test coverage:")
    print("  A3  alice — REFUND_REQUEST classification")
    print("  A4  bob   — RETURN_REQUEST classification")
    print("  A5  carol — COMPLAINT classification")
    print("  A6  promo — OTHER (agent must skip, no reply sent)")
    print("  A7  eve thread child — agent reply must use thread_id above (not start new thread)")
    print("  A8  dave  — AMBIGUOUS (agent must call create_gmail_draft, not send_gmail_message)")
    print("  A9  alice + bob + carol + eve(child) = 4 actionable emails — multi-step ReAct loop")
    print("  A10 auto mode summary — produced after A9 completes (no extra seed needed)")
    print("  A11 eve thread — get_gmail_thread returns 2-message history + agent reply = 3 messages")


if __name__ == "__main__":
    main()