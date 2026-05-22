#!/usr/bin/env bash

set -euo pipefail

TOKEN_DIR="${HOME}/.workspace-mcp"

# Run Google OAuth setup if tokens are absent or the cache directory is empty.
# workspace-mcp auth opens a browser on the host for one-time consent and
# stores Fernet-encrypted tokens at ~/.workspace-mcp/. Subsequent starts skip
# this block because the token file already exists.
if [[ ! -d "${TOKEN_DIR}" || -z "$(ls -A "${TOKEN_DIR}" 2>/dev/null)" ]]; then
    echo "[entrypoint] Google OAuth tokens not found at ${TOKEN_DIR}."
    echo "[entrypoint] Starting workspace-mcp auth flow — a browser window will open on your host."
    workspace-mcp auth
    echo "[entrypoint] OAuth complete. Tokens cached at ${TOKEN_DIR}."
else
    echo "[entrypoint] Google OAuth tokens found. Skipping auth."
fi

exec uvicorn main:app --host 0.0.0.0 --port 8000
