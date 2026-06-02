#!/usr/bin/env python3
"""
Re-authenticate Google OAuth credentials for workspace-mcp.

Usage:
    python3 scripts/reauth_google.py --secrets ~/Downloads/client_secret_*.json
    python3 scripts/reauth_google.py --secrets ~/Downloads/client_secret_*.json --email you@gmail.com
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=os.environ.get("WORKSPACE_USER_EMAIL", "consoleagenttest@gmail.com"))
    parser.add_argument("--secrets", required=True, help="Path to client_secret JSON from Cloud Console")
    args = parser.parse_args()

    secrets_path = Path(args.secrets).expanduser().resolve()
    cred_path = Path.home() / ".google_workspace_mcp" / "credentials" / f"{args.email}.json"

    print(f"Secrets file : {secrets_path}")
    print(f"Output file  : {cred_path}")
    print()

    if not secrets_path.exists():
        print(f"ERROR: secrets file not found: {secrets_path}")
        sys.exit(1)

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("ERROR: pip install google-auth-oauthlib")
        sys.exit(1)

    print("Starting OAuth flow — a browser window will open...")
    print("Sign in with:", args.email)
    print()

    flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), scopes=SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    print("OAuth flow complete. Writing credentials...")

    cred_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }

    cred_path.write_text(json.dumps(data, indent=2))
    print(f"Written to: {cred_path}")

    # Verify by reading back
    verify = json.loads(cred_path.read_text())
    print(f"Verified — new expiry : {verify.get('expiry')}")
    print(f"Verified — client_id  : {verify.get('client_id','')[:50]}")
    print()
    print("Done. You can now run:")
    print("  python3 scripts/seed_calendar_events.py")
    print("  python3 scripts/seed_test_emails.py")


if __name__ == "__main__":
    main()
