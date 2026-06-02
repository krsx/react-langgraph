#!/usr/bin/env python3
"""
Re-authenticate Google OAuth credentials for workspace-mcp.

Reads the existing client_id and client_secret from the stored credentials file,
opens a browser OAuth flow, and writes fresh tokens back to the same file so
workspace-mcp (and the seed scripts) can use them immediately.

Usage:
    python3 scripts/reauth_google.py [--email you@gmail.com]
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def main():
    parser = argparse.ArgumentParser(description="Re-authenticate Google OAuth for workspace-mcp")
    parser.add_argument(
        "--email",
        default=os.environ.get("WORKSPACE_USER_EMAIL", ""),
        help="Gmail address (default: $WORKSPACE_USER_EMAIL)",
    )
    args = parser.parse_args()

    if not args.email:
        print("ERROR: provide --email or set WORKSPACE_USER_EMAIL", file=sys.stderr)
        sys.exit(1)

    cred_path = Path.home() / ".google_workspace_mcp" / "credentials" / f"{args.email}.json"
    if not cred_path.exists():
        print(f"ERROR: credentials file not found at {cred_path}", file=sys.stderr)
        sys.exit(1)

    existing = json.loads(cred_path.read_text())
    client_id = existing.get("client_id")
    client_secret = existing.get("client_secret")
    token_uri = existing.get("token_uri", "https://oauth2.googleapis.com/token")

    if not client_id or not client_secret:
        print("ERROR: client_id or client_secret missing from credentials file.", file=sys.stderr)
        sys.exit(1)

    print(f"Re-authenticating {args.email}...")
    print("A browser window will open. Complete the Google sign-in and grant permissions.")
    print()

    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": token_uri,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    # Write back in workspace-mcp format
    updated = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    cred_path.write_text(json.dumps(updated, indent=2))
    print(f"\nFresh credentials written to {cred_path}")
    print("You can now run seed_test_emails.py and seed_calendar_events.py.")


if __name__ == "__main__":
    main()
