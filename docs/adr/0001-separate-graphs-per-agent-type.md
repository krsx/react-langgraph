# ADR 0001: Separate LangGraph Graphs Per Agent Type

## Status

Accepted

## Context

The application is expanding from one agent (Customer Service) to three (Customer Service, Refund Email, Calendar). Each agent has a different tool set, system prompt, and graph topology:

- **Customer Service**: memory_loader -> planner -> [tools loop] -> verifier -> memory_update. Tools are MySQL-backed, customer-scoped.
- **Refund Email**: planner -> [tools loop] -> verifier. Tools are Gmail MCP calls, no customer scoping.
- **Calendar**: planner -> [tools loop] -> verifier. Tools are Calendar MCP + workspace-cli, no customer scoping.

We considered two alternatives: (A) three separate compiled `StateGraph` instances, one per agent type, routed at the `/chat/stream` endpoint; or (B) one configurable graph with conditional nodes that branch on `agent_type` in the runtime config.

## Decision

**Separate graphs (Option A).** Each agent type has its own `StateGraph` definition in its own subdirectory under `backend/graph/`. Shared components (AgentState, verifier) live in `backend/graph/shared/`. The streaming endpoint selects the graph via `agent_type` in the request.

## Consequences

- Each agent's graph is self-contained and independently testable.
- Adding a fourth agent type means adding a new subdirectory, not modifying existing graph logic.
- The ReAct loop pattern (planner -> tools -> should_continue) is duplicated across graphs rather than shared as a reusable subgraph. Acceptable at three agents; worth revisiting if the count grows significantly.
- The SSE event handler in `chat.py` must handle the union of events from all graph types (some events like `memory_loaded` only fire for Customer Service).
