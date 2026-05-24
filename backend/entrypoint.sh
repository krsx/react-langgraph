#!/usr/bin/env bash

set -euo pipefail

TOKEN_DIR="${HOME}/.workspace-mcp"

has_valid_oauth_cache() {
    local cache_dir="${1}"
    [[ -d "${cache_dir}" ]] || return 1

    # Treat cache as valid only when token-like artifacts exist and are non-empty.
    # This avoids skipping auth for clearly uninitialized directories.
    find "${cache_dir}" -maxdepth 2 -type f \
        \( -name "*.enc" -o -name "*.json" -o -name "*token*" -o -name "*oauth*" \) \
        -size +0c -print -quit | grep -q .
}

# Run Google OAuth setup if token cache is missing or clearly uninitialized.
# workspace-mcp auth opens a browser on the host for one-time consent and
# stores Fernet-encrypted tokens at ~/.workspace-mcp/. Subsequent starts skip
# this block when token-like artifacts already exist.
if ! has_valid_oauth_cache "${TOKEN_DIR}"; then
    echo "[entrypoint] Google OAuth tokens not found at ${TOKEN_DIR}."
    echo "[entrypoint] Starting workspace-mcp auth flow — a browser window will open on your host."
    workspace-mcp auth
    echo "[entrypoint] OAuth complete. Tokens cached at ${TOKEN_DIR}."
else
    echo "[entrypoint] Google OAuth tokens found. Skipping auth."
fi

exec "$@"
