# Architecture: Intelligent Customer Service Agent

This document explains three core aspects of the system in depth:
1. [Database–Agent Interaction](#1-databaseagent-interaction)
2. [Agent Loop Wiring](#2-agent-loop-wiring)
3. [Server-Side Event Streaming](#3-server-side-event-streaming)

---

## 1. Database–Agent Interaction

### 1.1 Connection Layer

All database access goes through a single shared connection pool defined in `backend/db/connection.py`:

```python
_pool = MySQLConnectionPool(pool_size=5, host=..., user=..., ...)

def get_connection() -> mysql.connector.MySQLConnection:
    return _get_pool().get_connection()
```

Every function that needs the database calls `get_connection()`, uses it, then closes it in a `finally` block to return it to the pool. The pool size defaults to 5, configurable via `MYSQL_POOL_SIZE`.

### 1.2 When the Agent Reads and Writes the Database

Database interaction happens at four distinct points in the agent lifecycle:

```
HTTP request arrives
        │
        ▼
① _persist_session_start()   ← write: sessions + session_messages tables
        │
        ▼
② memory_loader()            ← read: customer_memory + complaints tables
        │
        ▼
   [agent loop runs]
        │
        ▼
③ tool functions             ← read/write: orders, complaints, customer_memory
        │
        ▼
④ memory_update()            ← write: customer_memory (last_interaction_summary)
        │
        ▼
   _persist_ai_message()     ← write: session_messages table
```

#### ① Session Persistence (`chat.py` → `_persist_session_start`)

Called immediately when a request arrives, before the agent runs:

```python
# INSERT IGNORE so re-sending on an existing thread_id doesn't duplicate the session
cursor.execute("INSERT IGNORE INTO sessions (thread_id, customer_id) VALUES (%s, %s)", ...)
cursor.execute("INSERT INTO session_messages (thread_id, role, content) VALUES (%s, %s, %s)", ...)
```

This guarantees the conversation is recorded even if the agent crashes.

#### ② Long-Term Memory Load (`graph/memory_loader.py`)

The first node in the graph. Runs a single `get_connection()` call that fires two queries:

```python
# Query 1: key-value memory entries (preferences, patterns, summaries)
SELECT `key`, value FROM customer_memory WHERE customer_id = %s

# Query 2: past complaint records
SELECT order_id, issue, status, created_at FROM complaints WHERE customer_id = %s
```

The results are merged into one list and stored as `memory_context` in `AgentState`. This becomes part of the system prompt that the LLM reads at the start of every planner call:

```python
# planner.py — memory_context injected into system prompt
if memory_entries:
    lines.append("\nCustomer History:")
    for e in memory_entries:
        lines.append(f"- {e['key']}: {e['value']}")
```

#### ③ Tool Functions (`graph/tools.py`)

Five tools, each opening their own connection from the pool:

| Tool | DB Operation | Table |
|---|---|---|
| `order_lookup` | `SELECT` by `order_id AND customer_id` | `orders` |
| `customer_profile` | `SELECT` by `customer_id` | `customers` |
| `refund` | `SELECT` to verify, then `UPDATE status = 'refund_requested'` | `orders` |
| `complaint_logger` | `SELECT` to verify order exists, then `INSERT` | `complaints` |
| `memory_tool` | `SELECT` (read) or `INSERT ... ON DUPLICATE KEY UPDATE` (write) | `customer_memory` |

All tools enforce **ownership** — they verify the requested resource belongs to the active `customer_id` from the config before acting:

```python
# Example from refund tool
cursor.execute("SELECT customer_id, status FROM orders WHERE order_id = %s", (order_id,))
row = cursor.fetchone()
if row is None:
    return {"error": f"Order {order_id} not found."}
if row["customer_id"] != customer_id:
    return {"error": f"Order {order_id} does not belong to this customer."}
```

Tools return plain `dict` results — either `{"success": True, ...}` or `{"error": "..."}`. They never raise exceptions for business logic failures; errors are returned as data so the LLM and verifier can reason about them.

#### ④ Memory Update (`graph/memory_update.py`)

The last node before `END`. Always runs after every turn and writes a summary of what happened:

```python
summary = f"[{timestamp}] User: {last_human} | Tools used: {tool_names} | Outcome: {tool_summary}"
cursor.execute(
    "INSERT INTO customer_memory ... ON DUPLICATE KEY UPDATE value = %s",
    (customer_id, "last_interaction_summary", summary, summary),
)
```

This uses `ON DUPLICATE KEY UPDATE` so it always overwrites the previous summary, keeping exactly one `last_interaction_summary` entry per customer.

### 1.3 Database Schema Overview

```
customers ──< orders ──< complaints
     │
     └──< customer_memory
     │
     └──< sessions ──< session_messages
```

- `orders.customer_id` → FK to `customers`
- `complaints.customer_id`, `complaints.order_id` → FK to `customers`, `orders`
- `customer_memory.customer_id` → FK to `customers`; unique on `(customer_id, key)`
- `sessions.customer_id` → FK to `customers`
- `session_messages.thread_id` → FK to `sessions`

---

## 2. Agent Loop Wiring

### 2.1 State: The Shared Memory of the Graph

All nodes read from and write to `AgentState` (defined in `graph/state.py`):

```python
class AgentState(TypedDict):
    messages:       Annotated[list, add_messages]  # full conversation history
    customer_id:    int | None                     # active customer
    memory_context: list[dict] | None              # loaded from DB at turn start
    tool_results:   list[dict] | None              # parsed results from tools
    verification:   dict | None                    # verifier output
```

The `Annotated[list, add_messages]` on `messages` is a LangGraph reducer — instead of replacing the list, each node's returned messages are **appended** to the existing list. This is what makes the conversation history accumulate across the ReAct loop.

### 2.2 Graph Topology

Defined in `graph/graph.py` → `create_builder()`:

```
                    ┌─────────────────┐
                    │  memory_loader  │  (entry point)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
              ┌────►│    planner      │◄──────┐
              │     └────────┬────────┘       │
              │              │                │
              │     tools_condition()          │
              │       /            \           │
              │  tool_calls?    no tool_calls  │
              │      │                │        │
              │ ┌────▼────┐          │        │
              └─┤  tools  │          │        │
                └─────────┘          │        │
                                     │        │
                            ┌────────▼──────┐ │
                            │   verifier    │ │
                            └────────┬──────┘ │
                                     │
                            ┌────────▼──────┐
                            │ memory_update │
                            └────────┬──────┘
                                     │
                                    END
```

The key wiring lines:

```python
builder.add_conditional_edges("planner", tools_condition, {"tools": "tools", END: "verifier"})
builder.add_edge("tools", "planner")
```

`tools_condition` is a LangGraph built-in. It inspects the last message in state:
- If it is an `AIMessage` with `tool_calls` → route to `"tools"`
- If it is an `AIMessage` with no `tool_calls` → route to `END` (which maps to `"verifier"` here)

The `add_edge("tools", "planner")` line creates the **ReAct loop**: after tool execution, control always returns to the planner. The planner then sees the tool results in `messages` and either calls more tools or produces a final response.

### 2.3 Node-by-Node Execution

#### `memory_loader` — Load context before reasoning

```python
def memory_loader(state: AgentState) -> dict:
    # Queries customer_memory and complaints
    # Returns: {"memory_context": [...], "tool_results": None, "verification": None}
```

Resets `tool_results` and `verification` to `None` at the start of each turn so stale values from a previous turn (stored in the SQLite checkpoint) don't bleed through.

#### `planner` — The LLM reasoning node

```python
def planner(state: AgentState, config: RunnableConfig) -> dict:
    system_prompt = build_system_prompt(state.get("memory_context"))
    llm_with_tools = create_llm(provider, model).bind_tools(_TOOLS)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm_with_tools.invoke(messages, config=config)
    return {"messages": [response]}
```

Key points:
- Called on **every iteration** of the loop — the LLM sees the full accumulated `messages` including all previous tool calls and results
- `bind_tools(_TOOLS)` attaches the JSON schemas of all 5 tools to the LLM request so it knows what it can call
- The system prompt includes `memory_context` (customer history, complaints) injected as text
- Returns a single `AIMessage` which is appended to state via the `add_messages` reducer

#### `tools` (ToolNode) — Execute what the LLM chose

LangGraph's built-in `ToolNode` reads the `tool_calls` list from the latest `AIMessage`, dispatches each call to the matching Python function, and appends a `ToolMessage` result per call back into `state["messages"]`.

The `config` (containing `customer_id`, `provider`, `model`) is forwarded to each tool function automatically.

#### `verifier` — Sanity check before responding

```python
def verifier(state: AgentState) -> dict:
    # Collect all ToolMessages
    # Look for {"error": ...} fields or empty list results
    # Check if the LLM already acknowledged the error in its last message
    # If not → inject an override AIMessage with a safe fallback
```

The verifier scans for two failure patterns:
1. **Tool errors**: any `{"error": "..."}` in a tool result
2. **Empty lookups**: any tool result where a list value is `[]`

If issues are found and the LLM's last message does NOT contain acknowledgment keywords (`"not found"`, `"error"`, `"cannot"`, etc.), the verifier injects an `override_message` into state to replace the LLM's response with a safe fallback. This prevents hallucinated success messages when a tool silently failed.

#### `memory_update` — Record what happened

Writes a single `last_interaction_summary` key to `customer_memory`. This key is loaded back by `memory_loader` on the next turn, giving the LLM awareness of the previous interaction.

### 2.4 Short-Term vs Long-Term Memory

| | Short-Term Memory | Long-Term Memory |
|---|---|---|
| **Storage** | SQLite (LangGraph checkpointer) | MySQL (`customer_memory` table) |
| **Scope** | Single session / thread | Persists across all sessions |
| **Contains** | Full `messages` list (all turns in this thread) | Key-value entries: preferences, summaries, patterns |
| **Written by** | LangGraph automatically via `add_messages` | `memory_update` node + `memory_tool` (agent-triggered) |
| **Read by** | LangGraph automatically (restored per `thread_id`) | `memory_loader` node at start of every turn |
| **Key file** | `graph/graph.py` → `SqliteSaver` / `AsyncSqliteSaver` | `graph/memory_loader.py`, `graph/memory_update.py` |

The SQLite checkpointer is keyed by `thread_id`. When the same `thread_id` is sent in subsequent requests, LangGraph restores the full `messages` history — this is how the agent remembers earlier turns in the same conversation.

---

## 3. Server-Side Event Streaming

### 3.1 Why SSE?

The agent loop can run for several seconds (multiple LLM calls, multiple tool executions). Instead of making the client wait for a single JSON response, the server uses **Server-Sent Events (SSE)** to push progress updates token-by-token and node-by-node as they happen.

SSE is a standard HTTP mechanism: the server keeps the connection open and writes `text/event-stream` formatted lines. The client reads them as a stream.

### 3.2 SSE Frame Format

Each event follows this wire format:

```
event: <event_type>\n
data: <json_payload>\n
\n
```

The blank line (`\n\n`) terminates a frame. The `_sse()` helper in `chat.py` produces this:

```python
def _sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
```

### 3.3 Event Sequence per Turn

Every turn produces events in this order:

```
memory_loaded      → LTM entries that were loaded for this customer
planner_start      → planner node began
planner_result     → LLM responded (with or without tool_calls)
tool_start         → tool node began        ┐
tool_result        → tool node finished     ┘ repeats for each ReAct iteration
planner_start      → planner called again   ┐
planner_result     → LLM responded again    ┘
...
response_token     → one token of the final text response (repeats many times)
verifier_result    → verifier check outcome
memory_updated     → memory_update node finished
response_end       → final complete response text
```

`response_token` events are generated by `on_chat_model_stream` — these are the streaming tokens from the LLM, emitted in real time so the frontend can display text as it is generated.

### 3.4 How `_event_stream` Translates Graph Events to SSE

`_event_stream()` in `chat.py` subscribes to `graph.astream_events()` which yields raw LangGraph internal events. Each event has a `kind` (`on_chain_start`, `on_chain_end`, `on_chat_model_stream`) and a `name` (the node name). The function maps these to SSE events:

```python
async for event in graph.astream_events(input_state, config=config, version="v2"):
    name = event.get("name", "")
    kind = event.get("event", "")
    data = event.get("data", {})

    if kind == "on_chain_end" and name == "memory_loader":
        yield _sse("memory_loaded", {...})

    elif kind == "on_chain_start" and name == "planner":
        yield _sse("planner_start", {...})

    elif kind == "on_chain_end" and name == "planner":
        yield _sse("planner_result", {...})   # includes tool_calls list

    elif kind == "on_chain_start" and name == "tools":
        yield _sse("tool_start", {...})

    elif kind == "on_chain_end" and name == "tools":
        yield _sse("tool_result", {...})

    elif kind == "on_chain_end" and name == "verifier":
        yield _sse("verifier_result", {...})

    elif kind == "on_chain_end" and name == "memory_update":
        yield _sse("memory_updated", {...})

    elif kind == "on_chat_model_stream":
        token = chunk.content
        yield _sse("response_token", {"token": token})   # one per token
```

After the loop ends, two final writes happen:

```python
ai_response = "".join(response_tokens)   # reassemble full response
_persist_ai_message(thread_id, ai_response)  # write to session_messages
yield _sse("response_end", {"response": ai_response})
```

Any unhandled exception yields an `error` event instead of crashing the HTTP connection:

```python
except Exception as exc:
    yield _sse("error", {"thread_id": thread_id, "error": str(exc)})
```

### 3.5 FastAPI StreamingResponse

The route handler wraps `_event_stream()` in a `StreamingResponse`:

```python
@router.post("/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering if behind a proxy
        },
    )
```

`StreamingResponse` iterates the async generator and flushes each yielded string to the TCP socket immediately — no buffering.

### 3.6 Client-Side Parsing (`frontend/src/lib/sse.ts`)

The frontend reads the stream using the Fetch API (not `EventSource`, which doesn't support POST):

```
streamChat()
    │  fetch POST /chat/stream
    │  response.body → ReadableStream<Uint8Array>
    ▼
parseSseStream()          ← async generator over the raw byte stream
    │  TextDecoder decodes bytes → string chunks
    ▼
createSseParser().push()  ← accumulates chunks in a buffer
    │  splits on \n\n to extract complete frames
    ▼
parseFrame()              ← extracts event: and data: lines
    ▼
parsePayload()            ← JSON.parse + type-narrows into ChatStreamEvent
    ▼
onEvent(event)            ← callback passed from App.tsx
    ▼
dispatch("stream_event_received")  ← React state update → re-render
```

The buffer in `createSseParser` handles the case where a TCP chunk contains a partial frame — it holds the incomplete data until the next chunk completes it. `flush()` is called after the stream ends to process any remaining bytes in the buffer.

### 3.7 Event Types Reference

| SSE Event | Payload fields | Frontend use |
|---|---|---|
| `memory_loaded` | `memory_context: []` | Agent Process panel |
| `planner_start` | — | Agent Process panel |
| `planner_result` | `content`, `tool_calls: []` | Agent Process panel |
| `tool_start` | — | Agent Process panel |
| `tool_result` | `results` (string) | Agent Process panel |
| `verifier_result` | `valid`, `checks: []`, `override_message` | Agent Process panel |
| `memory_updated` | — | Agent Process panel |
| `response_token` | `token` | Chat bubble (streams text live) |
| `response_end` | `response` (full text) | Chat bubble (finalizes) |
| `error` | `error` (string) | Chat bubble (shows error) |
