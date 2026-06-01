"""Seed Google Calendar events and Gmail test emails for testing."""

import base64
import json
import os
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
]

TOKEN_PATH = Path(__file__).parent / "token.json"


def get_credentials() -> Credentials:
    creds = None

    if TOKEN_PATH.exists():
        data = json.loads(TOKEN_PATH.read_text())
        creds = Credentials.from_authorized_user_info(data, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        client_config = {
            "installed": {
                "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
                "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    return creds


CALENDAR_EVENTS = [
    ("2026-06-01T09:00:00", "2026-06-01T10:00:00", "Team Standup"),
    ("2026-06-01T14:00:00", "2026-06-01T15:00:00", "Research Meeting"),
    ("2026-06-02T10:00:00", "2026-06-02T11:00:00", "Project Review"),
    ("2026-06-02T15:00:00", "2026-06-02T16:00:00", "Student Advising"),
    ("2026-06-03T09:00:00", "2026-06-03T10:30:00", "Faculty Meeting"),
    ("2026-06-03T14:00:00", "2026-06-03T15:00:00", "PhD Progress Review"),
    ("2026-06-04T11:00:00", "2026-06-04T12:00:00", "Industry Collaboration Meeting"),
    ("2026-06-04T15:00:00", "2026-06-04T16:00:00", "Lab Weekly Meeting"),
    ("2026-06-05T09:00:00", "2026-06-05T10:00:00", "Grant Proposal Discussion"),
    ("2026-06-05T15:00:00", "2026-06-05T16:00:00", "Research Seminar"),
]

CALENDAR_TITLES = {title for _, _, title in CALENDAR_EVENTS}

TIMEZONE = "Asia/Taipei"


def cleanup_calendar_events(service) -> list[str]:
    time_min = "2026-06-01T00:00:00+08:00"
    time_max = "2026-06-05T23:59:59+08:00"

    result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
    ).execute()

    deleted = []
    for event in result.get("items", []):
        if event.get("summary") in CALENDAR_TITLES:
            service.events().delete(
                calendarId="primary",
                eventId=event["id"],
            ).execute()
            deleted.append(event["summary"])
            print(f"  Deleted calendar event: {event['summary']}")

    return deleted


def seed_calendar_events(service) -> list[str]:
    created = []
    for start, end, summary in CALENDAR_EVENTS:
        body = {
            "summary": summary,
            "start": {"dateTime": start, "timeZone": TIMEZONE},
            "end": {"dateTime": end, "timeZone": TIMEZONE},
        }
        service.events().insert(calendarId="primary", body=body).execute()
        created.append(summary)
        print(f"  Created calendar event: {summary}")

    return created


TEST_SEED_LABEL = "TEST_SEED"


def ensure_test_seed_label(service) -> str:
    results = service.users().labels().list(userId="me").execute()
    for label in results.get("labels", []):
        if label["name"] == TEST_SEED_LABEL:
            return label["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": TEST_SEED_LABEL,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    print(f"  Created Gmail label: {TEST_SEED_LABEL}")
    return created["id"]


def cleanup_emails(service, label_id: str) -> int:
    result = service.users().messages().list(
        userId="me",
        labelIds=[label_id],
    ).execute()

    messages = result.get("messages", [])
    for msg in messages:
        service.users().messages().delete(userId="me", id=msg["id"]).execute()
        print(f"  Deleted email: {msg['id']}")

    return len(messages)


TEST_EMAILS = [
    (
        "alice@customer.com",
        "I need a refund for my order",
        "I placed an order last week and the product arrived damaged beyond use. "
        "I would like to request a full refund as soon as possible. "
        "Please let me know what information you need from me to process this.",
    ),
    (
        "frank@customer.com",
        "Requesting refund for damaged product",
        "The item I received was completely broken when I opened the package. "
        "This is unacceptable and I need my money back immediately. "
        "My order number is #4521 and I paid via credit card.",
    ),
    (
        "bob@customer.com",
        "I'd like to return my recent purchase",
        "I bought a jacket last Tuesday but it doesn't fit properly. "
        "Could you please provide me with the return shipping label and instructions? "
        "I would like to exchange it for a different size if possible.",
    ),
    (
        "grace@customer.com",
        "Return request for Order #7821",
        "I need to return the shoes I ordered under Order #7821. "
        "They are the wrong color compared to what was shown on the website. "
        "Please send me the return instructions and a prepaid shipping label.",
    ),
    (
        "carol@customer.com",
        "This is completely unacceptable service",
        "I have been waiting three weeks for my order and nobody has responded to my emails. "
        "Your customer service is terrible and I am extremely frustrated. "
        "I demand someone contacts me today to resolve this issue.",
    ),
    (
        "henry@customer.com",
        "Very disappointed with your support",
        "I called your support line four times and was put on hold for over an hour each time. "
        "This level of service is disgraceful and I am considering filing a formal complaint. "
        "I expected much better from your company.",
    ),
    (
        "promo@newsletter.com",
        "Exclusive deal just for you!",
        "Don't miss out on our biggest sale of the year with up to 70% off select items. "
        "Use code SUMMER2026 at checkout for an extra 10% discount. "
        "This offer expires at midnight so act fast!",
    ),
    (
        "info@updates.com",
        "Your weekly newsletter is here",
        "Here is your weekly roundup of the latest industry news and trends. "
        "This week we cover emerging technologies and market insights. "
        "Click through to read the full articles on our website.",
    ),
]


def seed_emails(service, label_id: str) -> list[str]:
    created = []
    for from_addr, subject, body in TEST_EMAILS:
        msg = MIMEText(body)
        msg["From"] = from_addr
        msg["To"] = "me"
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        service.users().messages().insert(
            userId="me",
            body={
                "raw": raw,
                "labelIds": ["INBOX", "UNREAD", label_id],
            },
        ).execute()
        created.append(subject)
        print(f"  Inserted email: {subject}")

    return created


def main():
    creds = get_credentials()

    cal_service = build("calendar", "v3", credentials=creds)
    gmail_service = build("gmail", "v1", credentials=creds)

    print("Cleaning up calendar events...")
    cleanup_calendar_events(cal_service)

    print("Seeding calendar events...")
    seed_calendar_events(cal_service)

    print("Ensuring TEST_SEED label...")
    label_id = ensure_test_seed_label(gmail_service)

    print("Cleaning up test emails...")
    cleanup_emails(gmail_service, label_id)

    print("Seeding test emails...")
    seed_emails(gmail_service, label_id)

    print("Done!")


if __name__ == "__main__":
    main()
