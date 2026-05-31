# Fresh Environment Setup

## Prerequisites

| Tool | Purpose |
|------|---------|
| Docker + Docker Compose | Run the full stack |
| `workspace-mcp` (host machine) | One-time Google OAuth flow |
| OpenRouter account | LLM calls via API key |
| Google Cloud project | OAuth credentials for Gmail/Calendar agents |

Install `workspace-mcp` on the host (not in Docker):

```bash
pip install workspace-mcp
```

---

## 1. Environment Variables

```bash
cp .env.example .env
```

Fill in the required values:

```bash
# LLM — get key from https://openrouter.ai/
OPENROUTER_API_KEY=sk-or-...
DEFAULT_MODEL=google/gemini-2.5-flash

# MySQL — can keep defaults for local dev
MYSQL_PASSWORD=changeme

# Google Workspace (required only for Calendar/Refund Email agents)
GOOGLE_OAUTH_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-...
WORKSPACE_USER_EMAIL=you@gmail.com
```

**Required variables** (backend refuses to start without these):
`OPENROUTER_API_KEY`, `DEFAULT_MODEL`, `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`

---

## 2. Google OAuth — One-Time Setup

This is only needed for the Calendar and Refund Email agents. The OAuth flow requires a browser, so it must run on the **host machine** (not in Docker).

**Step 2a — Create OAuth credentials in Google Cloud Console:**
1. Go to APIs & Services → Credentials → Create OAuth 2.0 Client ID
2. Application type: **Desktop app**
3. Enable APIs: Gmail API, Google Calendar API
4. Copy client ID and secret to `.env`

**Step 2b — Run the auth script:**

```bash
./scripts/workspace-mcp-auth.sh
```

This opens a browser for Google consent. Complete the flow, then press `Ctrl+C`. Credentials are cached at:

```
~/.google_workspace_mcp/credentials/
```

Docker Compose mounts this directory automatically — no repeated auth needed.

To force re-authentication:

```bash
./scripts/workspace-mcp-auth.sh --force
```

---

## 3. Start the Stack

```bash
docker compose up
```

Services started:
- `mysql:3306` — seeded from `backend/db/`
- `backend:8000` — FastAPI + LangGraph
- `frontend:5173` — React + Vite

Wait for `mysql` to pass its healthcheck before the backend accepts connections.

**Without Google Workspace:** leave `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` blank. The backend starts normally; Calendar and Refund Email agents simply have no MCP tools available.

---

## 4. Verify

```bash
# Backend health
curl http://localhost:8000/providers

# Frontend
open http://localhost:5173
```

---

## Local Development (no Docker)

```bash
# Backend — requires a running MySQL instance pointed to by .env
cd backend && uv run uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

Run non-integration tests (no MySQL required):

```bash
cd backend && uv run pytest -m "not integration" -v
```

---

## How MCP Tools Are Loaded

At startup `McpClientManager` reads `WORKSPACE_MCP_COMMAND` (defaults to `workspace-mcp`) and launches it as a **stdio subprocess** inside the container. Tools are filtered per agent type:

| Agent | MCP tools exposed |
|-------|------------------|
| `refund_email` | Gmail tools |
| `calendar` | Calendar tools |
| `customer_service` | None (uses DB tools only) |

If `WORKSPACE_MCP_COMMAND` is unset, the manager starts with no MCP tools — the rest of the app is unaffected.
