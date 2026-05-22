# AGENTS.md

This file provides guidance to AI Agent when working with code in this repository.

## Project Specification

Project initial specification can be found in `docs/project-spec.md` and its extendsion in `docs/project-spec-extend.md`. This is our core focumentation to build the application.


## Project Status

This repository is an active full-stack React + LangGraph application with a routed frontend in `frontend/` and a FastAPI + LangGraph backend in `backend/`.

## Installed Skills

The following skills are available via the `Skill` tool (defined in `skills-lock.json`, sourced from `mattpocock/skills`):

- `prototype` — rapid prototyping workflow
- `tdd` — test-driven development
- `diagnose` — debugging/diagnosis workflow
- `to-prd` — convert ideas to a product requirements document
- `to-issues` — convert a PRD to tracked issues
- `triage` — triage and prioritize issues
- `improve-codebase-architecture` — architectural improvement workflow
- `zoom-out` — high-level codebase review
- `caveman`, `grill-me`, `grill-with-docs`, `write-a-skill` — productivity skills

## Agent skills

### Issue tracker

Issues live in GitHub Issues (uses the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## Development Commands

```bash
# Frontend verification
cd frontend && npm test
cd frontend && npx tsc --noEmit
cd frontend && npm run build

# Run non-integration tests (no MySQL required)
cd backend && uv run pytest -m "not integration" -v

# Run all tests (requires MySQL)
cd backend && uv run pytest -v

# Start backend dev server
cd backend && uv run uvicorn main:app --reload --port 8000

# Start full stack (MySQL + Ollama + backend)
docker compose up
```

## Architecture

Frontend: React 19 + React Router + TanStack Query (`frontend/`)

```
frontend/
├── src/App.tsx                 # QueryClientProvider + RouterProvider bootstrap
├── src/routes.tsx              # Top-level route tree; wraps Layout with ChatProvider
├── src/routes/
│   ├── layout.tsx              # Shell layout with shadcn sidebar + session history
│   ├── chat.tsx                # Chat page with ChatHeader, ConversationArea, AgentProcessPanel
│   ├── data.tsx                # Data Explorer CRUD page
│   └── memory.tsx              # Memory Manager page
├── src/lib/chat-context.tsx    # Scoped local conversation state and streaming actions
├── src/lib/conversation.ts     # Shared conversation view/turn types for live chat flow
├── src/lib/api.ts              # Frontend API client helpers
└── src/components/
    ├── chat/                   # ChatHeader and ConversationArea
    ├── process/                # Agent Process timeline
    └── ui/                     # shadcn primitives used by live routes
```

Key frontend rules:

- TanStack Query owns server state such as customers, providers, sessions, CRUD data, and memory entries.
- `ChatProvider` owns only writable chat/session UI state and streaming transitions for the live `/chat` flow.
- The routed shell in `layout.tsx` is the source of truth for navigation and session history.
- Verify frontend changes with `npm test`, `npx tsc --noEmit`, and `npm run build`.

Backend: FastAPI + LangGraph (Python 3.10, `backend/`)

```
backend/
├── main.py              # FastAPI app, routers registered here
├── config.py            # Env-based Config dataclass
├── llm_factory.py       # create_llm(provider, model) — OpenRouter or Ollama
├── graph/
│   ├── graph.py         # LangGraph StateGraph compiled with SqliteSaver checkpointer
│   ├── state.py         # AgentState TypedDict
│   ├── planner.py       # ReAct LLM node — reads provider/model from RunnableConfig
│   ├── verifier.py      # Post-response quality check node
│   ├── memory_loader.py # Loads customer memory from DB at start of turn
│   ├── memory_update.py # Persists new memory after response
│   └── tools.py         # order_lookup, customer_profile, refund, complaint_logger, memory_tool
└── routes/
    ├── chat.py          # POST /chat/stream — SSE streaming, forwards provider/model to graph
    ├── providers.py     # GET /providers — health check for OpenRouter + Ollama
    ├── sessions.py      # GET /sessions, GET /sessions/:id
    ├── data.py          # GET /customers, /orders, /complaints
    └── memory.py        # GET/PUT/DELETE /memory/:customer_id
```

## LLM Providers

Two providers are supported; selected per-request via `provider` field in `/chat/stream` body.

| Provider | Class | Base URL | Default model |
|---|---|---|---|
| `openrouter` (default) | `ChatOpenAI` | `https://openrouter.ai/api/v1` | `DEFAULT_MODEL` env |
| `ollama` | `ChatOllama` | `OLLAMA_BASE_URL` env | `OLLAMA_DEFAULT_MODEL` env |

**Constraint**: Ollama models **must** support tool calling for the agent to function. The planner uses `bind_tools()` and will fail at invocation time with models that don't support it.

Verified tool-calling Ollama models: `qwen3:4b`, `qwen3:8b`, `llama3.1:8b`, `llama3.2:3b`, `mistral-nemo`, `firefunction-v2`

Not supported: most base/instruct-only models (e.g. `phi3`, `gemma2`, `tinyllama`)
