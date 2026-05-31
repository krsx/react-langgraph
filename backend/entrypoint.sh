#!/usr/bin/env bash

set -euo pipefail

# workspace-mcp >= current stores credentials at ~/.google_workspace_mcp/credentials
# (not ~/.workspace-mcp). The 'auth' subcommand was removed; authentication now
# happens inline when the server handles its first request. We check here only to
# give an early, actionable warning when the volume is unpopulated.
CREDS_DIR="${HOME}/.google_workspace_mcp/credentials"

has_valid_credentials() {
    local dir="${1}"
    [[ -d "${dir}" ]] || return 1

    find "${dir}" -maxdepth 2 -type f \
        \( -name "*.pickle" -o -name "*.json" -o -name "*token*" -o -name "*oauth*" \) \
        -size +0c -print -quit | grep -q .
}

if ! has_valid_credentials "${CREDS_DIR}"; then
    echo "[entrypoint] WARNING: No workspace-mcp credentials found at ${CREDS_DIR}."
    echo "[entrypoint] Google Workspace tools (Gmail, Calendar) will be unavailable until"
    echo "[entrypoint] credentials are mounted at that path and the container is restarted."
else
    echo "[entrypoint] workspace-mcp credentials found at ${CREDS_DIR}."
fi

exec "$@"
