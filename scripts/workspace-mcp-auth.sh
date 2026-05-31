#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CREDS_DIR="${HOME}/.google_workspace_mcp/credentials"

usage() {
    echo "Usage: $0 [--force]"
    echo ""
    echo "Run the one-time Google OAuth flow for workspace-mcp."
    echo "Cached credentials are stored at: ${CREDS_DIR}"
    echo ""
    echo "Options:"
    echo "  --force    Re-authenticate even if credentials already exist"
    echo ""
    echo "Prerequisites:"
    echo "  - workspace-mcp installed (pip install workspace-mcp)"
    echo "  - GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env"
    exit 1
}

FORCE=false
for arg in "$@"; do
    case "${arg}" in
        --force) FORCE=true ;;
        -h|--help) usage ;;
        *) echo "Unknown option: ${arg}"; usage ;;
    esac
done

if ! command -v workspace-mcp &>/dev/null; then
    echo "ERROR: workspace-mcp is not installed."
    echo "Install with: pip install workspace-mcp"
    exit 1
fi

if [[ -f "${REPO_ROOT}/.env" ]]; then
    set -a
    source "${REPO_ROOT}/.env"
    set +a
fi

if [[ -z "${GOOGLE_OAUTH_CLIENT_ID:-}" ]]; then
    echo "ERROR: GOOGLE_OAUTH_CLIENT_ID is not set."
    echo "Set it in ${REPO_ROOT}/.env or export it in your shell."
    exit 1
fi

if [[ -z "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]]; then
    echo "ERROR: GOOGLE_OAUTH_CLIENT_SECRET is not set."
    echo "Set it in ${REPO_ROOT}/.env or export it in your shell."
    exit 1
fi

if [[ "${FORCE}" == "false" ]] && [[ -d "${CREDS_DIR}" ]]; then
    if find "${CREDS_DIR}" -maxdepth 2 -type f \
        \( -name "*.pickle" -o -name "*.json" -o -name "*token*" -o -name "*oauth*" \) \
        -size +0c -print -quit | grep -q .; then
        echo "Credentials already exist at ${CREDS_DIR}"
        echo "Use --force to re-authenticate."
        exit 0
    fi
fi

echo "Starting workspace-mcp OAuth flow..."
echo "A browser window will open for Google consent."
echo "Complete the OAuth flow, then press Ctrl+C to stop the server."
echo ""

export OAUTHLIB_INSECURE_TRANSPORT=1
export GOOGLE_OAUTH_CLIENT_ID
export GOOGLE_OAUTH_CLIENT_SECRET
export WORKSPACE_MCP_PORT=8888

workspace-mcp --single-user --tool-tier core --permissions gmail:send calendar:full

echo ""
echo "OAuth flow complete. Credentials cached at ${CREDS_DIR}"
echo "These will be mounted into the Docker container automatically."
