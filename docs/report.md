# Intelligent Customer Service Agent — Project Report
## ReAct + LangGraph Implementation

---

## 1. Agentic Architecture

### 1.1 ReAct Paradigm

This system implements the **ReAct (Reason + Act)** paradigm, an agentic AI pattern introduced by Yao et al. (2022) that interleaves reasoning traces with concrete actions. Unlike a simple retrieval-augmented generation (RAG) pipeline that retrieves context once and generates a single response, ReAct allows the agent to dynamically decide what information it needs, retrieve it, observe the result, and revise its plan — repeating this cycle as many times as necessary before producing a final answer.

The key advantage of ReAct in a customer service context is its ability to handle **multi-step transactional requests**. A query like "Refund order 7890 if it has been delivered" cannot be answered with a static lookup — the agent must first retrieve the order status, reason about whether the condition is met, and only then execute the refund. This requires the iterative loop that ReAct provides.

The reasoning step (Reason) is handled by the Large Language Model (LLM). The LLM reads the full conversation history, the customer's long-term memory, and the schemas of all available tools, then decides what to do next. If it determines that a tool call is needed, it emits a structured `tool_calls` field in its response instead of plain text. The action step (Act) executes whichever tool the LLM selected, appends the result back into the conversation, and returns control to the LLM for the next reasoning iteration. This cycle continues until the LLM produces a response with no tool calls, signaling that it has enough information to answer the user.

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│                      REACT LOOP                         │
│                                                         │
│   ┌─────────────┐     tool_calls?     ┌─────────────┐  │
│   │   REASON    │ ──── yes ─────────► │     ACT     │  │
│   │  (Planner)  │                     │  (Tools)    │  │
│   │             │ ◄─── results ─────── │             │  │
│   └──────┬──────┘                     └─────────────┘  │
│          │ no tool_calls                               │
└──────────┼──────────────────────────────────────────────┘
           │
           ▼
    Final Response
```

The loop has a **recursion limit of 10 iterations** (configured in `graph.py`) to prevent infinite loops in cases where the LLM repeatedly calls tools without converging to an answer. In practice, most customer service queries resolve in 1–3 iterations.

### 1.2 LangGraph Agent Flow

The agent is implemented as a **LangGraph StateGraph** — a directed graph where each node is a Python function and edges define the allowed transitions between them. LangGraph manages the execution order, passes shared state between nodes, and persists checkpoints so the conversation can be resumed across HTTP requests.

The graph consists of five nodes executed in the following order:

```
                         ┌──────────────────┐
                         │  User Message    │
                         │  + customer_id   │
                         │  + thread_id     │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  memory_loader   │  Reads customer_memory
                         │                  │  and complaints from MySQL
                         └────────┬─────────┘
                                  │  memory_context injected into system prompt
                         ┌────────▼─────────┐
                    ┌───►│    planner       │  LLM reasons over messages
                    │    │                  │  + memory + tool schemas
                    │    └────────┬─────────┘
                    │             │
                    │    tools_condition()
                    │       /           \
                    │  tool_calls?    no tool_calls
                    │      │                │
                    │ ┌────▼─────┐         │
                    │ │  tools   │         │
                    │ │          │         │
                    │ │order_    │         │
                    │ │lookup    │         │
                    │ │customer_ │         │
                    │ │profile   │         │
                    │ │refund    │         │
                    │ │complaint_│         │
                    │ │logger    │         │
                    │ │memory_   │         │
                    │ │tool      │         │
                    └─┤          │         │
                      └──────────┘         │
                                  ┌────────▼─────────┐
                                  │    verifier      │  Checks tool results
                                  │                  │  for errors/empty data
                                  └────────┬─────────┘
                                           │
                                  ┌────────▼─────────┐
                                  │  memory_update   │  Writes interaction
                                  │                  │  summary to MySQL
                                  └────────┬─────────┘
                                           │
                                  ┌────────▼─────────┐
                                  │  Final Response  │
                                  └──────────────────┘
```

**Node responsibilities:**

**`memory_loader`** is the entry point of the graph. Before any reasoning begins, it queries the customer's long-term memory and complaint history from MySQL and stores them in `AgentState`. This ensures the LLM has full customer context available from the very first reasoning step. It also resets `tool_results` and `verification` to `None` so that stale values from the previous session turn do not carry over.

**`planner`** is the core reasoning node. It constructs a system prompt that includes the customer's memory context, appends it to the full conversation history, and invokes the LLM with all five tool schemas attached via `bind_tools()`. The LLM then produces one of two possible outputs: an `AIMessage` containing `tool_calls` (meaning it wants to call a tool), or an `AIMessage` containing plain text (meaning it is ready to respond). The planner node is called on every iteration of the ReAct loop, so the LLM always sees the full updated conversation including all tool results from previous iterations.

**`tools`** is a LangGraph built-in `ToolNode`. It reads the `tool_calls` list from the latest `AIMessage`, dispatches each call to the matching Python function in `tools.py`, and appends a `ToolMessage` for each result back into the conversation state. If the LLM called multiple tools in one response, all are executed in this single node invocation.

**`verifier`** runs after the planner exits the loop with a final text response. It scans all `ToolMessage` results in the conversation for error fields or empty results, then checks whether the LLM's final response already acknowledged those errors. If the LLM hallucinated a success message despite a tool failure, the verifier overrides it with a safe fallback. This node acts as a guardrail against incorrect confirmations being shown to the user.

**`memory_update`** is the final node before the graph terminates. It always runs regardless of what happened during the turn. It writes a timestamped summary of the interaction — including which tools were used and what the outcomes were — into the `customer_memory` table. This summary becomes part of the long-term memory loaded at the start of the next turn, giving the agent awareness of recent interaction history.

The **conditional edge** from `planner` uses LangGraph's built-in `tools_condition` function to inspect the latest message. If it contains `tool_calls`, the graph routes to the `tools` node; otherwise it routes to `verifier`. The edge from `tools` back to `planner` closes the ReAct loop. This wiring — two lines in `graph.py` — is what produces the iterative reasoning behavior of the entire agent.

### 1.3 Memory Architecture

Effective customer service requires the agent to remember information at two different timescales. Within a single conversation, the agent must track what was said earlier to resolve references like "cancel it" or "the order I just mentioned." Across multiple conversations over days or weeks, the agent should accumulate knowledge about the customer — their preferences, recurring problems, and interaction history — to deliver personalized responses. This system addresses both requirements with two independent but complementary memory layers.

```
┌─────────────────────────────────────────────────────────────┐
│                    SHORT-TERM MEMORY                        │
│                                                             │
│  Storage : SQLite (LangGraph checkpointer)                  │
│  Scope   : Per session / thread_id                          │
│  Content : Full message history — all turns in the thread   │
│  Managed : Automatically by LangGraph via add_messages      │
│                                                             │
│  "What did we say earlier in this conversation?"            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    LONG-TERM MEMORY                         │
│                                                             │
│  Storage : MySQL — customer_memory table                    │
│  Scope   : Per customer_id (persists across all sessions)   │
│  Content : key-value pairs                                  │
│            - delivery_history_*                             │
│            - late_delivery_pattern                          │
│            - complaint_count                                │
│            - last_interaction_summary                       │
│            - user-defined preferences                       │
│  Written : memory_update node (auto) + memory_tool (agent)  │
│  Read    : memory_loader node at start of every turn        │
│                                                             │
│  "What do I know about this customer across all time?"      │
└─────────────────────────────────────────────────────────────┘
```

**Short-Term Memory (STM)** is managed entirely by LangGraph through its checkpointer mechanism. Every message — human turns, AI responses, and tool results — is appended to the `messages` field in `AgentState` using the `add_messages` reducer. LangGraph automatically persists this list to a SQLite database keyed by `thread_id` after every node execution. When the user sends a follow-up message in the same conversation, the backend passes the same `thread_id` in the graph config, and LangGraph restores the full message history before running the first node. This means the LLM receives the entire conversation context on every call without any manual management. STM enables capabilities like pronoun resolution ("cancel it" after discussing order 12345) and multi-turn reasoning where context from earlier in the conversation informs later decisions.

**Long-Term Memory (LTM)** is stored in the `customer_memory` MySQL table as flexible key-value pairs, scoped to a `customer_id`. Unlike STM, LTM persists across all sessions and is never automatically cleared. It is populated from two sources: the `memory_update` node writes a `last_interaction_summary` after every turn automatically, and the agent can call the `memory_tool` mid-conversation to explicitly store preferences or notes when the user asks. At the start of every turn, the `memory_loader` node reads all LTM entries for the active customer and injects them into the system prompt so the LLM can reference them during reasoning. This enables personalization behaviors such as detecting that a customer has a recurring late delivery problem (`late_delivery_pattern` key) or honoring a stated preference ("I prefer refunds over store credit").

The two layers are designed to work together. STM handles within-session continuity while LTM provides cross-session personalization. A customer who says "my order is late again" in a new session triggers the agent to check LTM for the `late_delivery_pattern` key — and because `memory_update` wrote a summary of the previous session, the agent can acknowledge the repeated issue even though STM for the new session starts empty.

---

## 2. Agentic Implementation

### 2.1 System Design

The system follows a three-tier architecture: a React frontend, a FastAPI backend, and a MySQL database. The backend is the central coordinator — it receives requests from the browser, runs the LangGraph agent, calls the LLM provider, reads and writes to MySQL, and streams results back to the frontend. All services are containerized and orchestrated with Docker Compose, making the full stack reproducible with a single `docker compose up` command.

The frontend is a single-page React 19 application built with Vite. It communicates with the backend exclusively over HTTP — regular JSON requests for data (customers, sessions, memory entries) and a persistent SSE connection for chat streaming. The frontend never talks to MySQL or the LLM directly; all intelligence and data access is handled server-side.

The backend exposes two categories of endpoints. CRUD endpoints (`/customers`, `/orders`, `/complaints`, `/sessions`, `/memory/:id`) serve the Data Explorer and Memory Manager panels with direct MySQL queries. The chat endpoint (`POST /chat/stream`) is the entry point for the agentic workflow — it accepts a message and streams back SSE events as the LangGraph graph executes node by node.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              CLIENT                                      │
│                                                                          │
│   Browser  ──►  React 19 + Vite (port 5173)                             │
│                 │                                                        │
│                 ├── Sidebar        (customer, provider, session select)  │
│                 ├── ChatPanel      (message input, streaming response)   │
│                 └── RightPanel     (Agent Process | Data | Memory tabs)  │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │  HTTP / SSE
                               │  POST /chat/stream
                               │  GET  /providers, /customers, /sessions, ...
┌──────────────────────────────▼───────────────────────────────────────────┐
│                             BACKEND                                      │
│                                                                          │
│   FastAPI (port 8000)                                                    │
│   │                                                                      │
│   ├── /chat/stream    ──► _event_stream()  ──► LangGraph                │
│   ├── /providers      ──► health-check OpenRouter + Ollama               │
│   ├── /customers      ──► MySQL SELECT                                   │
│   ├── /orders         ──► MySQL SELECT                                   │
│   ├── /complaints     ──► MySQL SELECT                                   │
│   ├── /sessions       ──► MySQL SELECT                                   │
│   └── /memory/:id     ──► MySQL SELECT / INSERT / DELETE                 │
│                                                                          │
│   LangGraph StateGraph                                                   │
│   ├── memory_loader   ──► MySQL (customer_memory, complaints)            │
│   ├── planner         ──► LLM API (OpenRouter or Ollama)                 │
│   ├── tools (ToolNode)──► MySQL (orders, customers, complaints, memory)  │
│   ├── verifier        ──► in-memory logic                                │
│   └── memory_update   ──► MySQL (customer_memory)                        │
│                                                                          │
│   Checkpointer: SQLite (checkpoints.db)                                  │
└───────────────┬──────────────────────┬───────────────────────────────────┘
                │                      │
┌───────────────▼──────┐  ┌────────────▼──────────────────────────────────┐
│      MySQL           │  │              LLM PROVIDERS                    │
│      (port 3306)     │  │                                               │
│                      │  │  OpenRouter ──► cloud-hosted models           │
│  customers           │  │  (api.openrouter.ai)  DEFAULT_MODEL env       │
│  orders              │  │                                               │
│  complaints          │  │  Ollama ──► locally-hosted models             │
│  customer_memory     │  │  (port 11434)  OLLAMA_DEFAULT_MODEL env       │
│  sessions            │  │  Verified tool-call models:                   │
│  session_messages    │  │  qwen3:4b, llama3.1:8b, llama3.2:3b           │
└──────────────────────┘  └───────────────────────────────────────────────┘
```

The backend supports two interchangeable LLM providers. **OpenRouter** routes requests to cloud-hosted models via a compatible OpenAI API endpoint — it requires an API key but delivers fast inference on powerful cloud GPUs. **Ollama** runs models locally inside the Docker network — no API key is required, but inference speed depends entirely on host hardware. The provider is selected per-request by the frontend dropdown, and the backend's `llm_factory.py` instantiates the appropriate LangChain client (`ChatOpenAI` for OpenRouter, `ChatOllama` for Ollama). Both clients expose the same `bind_tools()` and `invoke()` interface, so the rest of the agent code is fully provider-agnostic. One critical constraint applies to Ollama: the selected model must support structured tool calling. Models that do not emit `tool_calls` in their response will cause the agent to loop without taking any action.

MySQL stores all persistent application data across six tables. The `customers`, `orders`, and `complaints` tables hold the core business domain. The `customer_memory` table holds long-term memory as key-value pairs per customer. The `sessions` and `session_messages` tables record every conversation and message for the session history sidebar. All database access is pooled through a shared `MySQLConnectionPool` (default size 5) defined in `db/connection.py`, with each function acquiring a connection, using it, and returning it to the pool in a `finally` block.

### 2.2 Server-Side Event Streaming (SSE)

Rather than waiting for the entire agent workflow to complete before returning a response, the backend uses **Server-Sent Events (SSE)** to push progress to the client in real time. This design choice is essential for user experience: the LangGraph graph may run for several seconds across multiple LLM calls and tool executions, and streaming allows the user to see the agent's reasoning as it unfolds rather than staring at a blank screen.

SSE is a standard HTTP mechanism where the server holds the connection open and writes newline-delimited text frames. The client reads them incrementally as they arrive. Unlike WebSockets, SSE is unidirectional (server to client only) and works over plain HTTP — no upgrade handshake required. FastAPI's `StreamingResponse` is used to wrap the async generator that yields SSE frames, and the `X-Accel-Buffering: no` response header ensures that any reverse proxy (such as nginx) does not buffer the frames before forwarding them.

The chat endpoint returns a `StreamingResponse` that iterates `_event_stream()`, an async generator in `routes/chat.py`. Inside that generator, `graph.astream_events()` yields raw LangGraph internal lifecycle events as each node starts and finishes. The generator filters these events by their `kind` (e.g. `on_chain_end`, `on_chat_model_stream`) and `name` (the node name), then maps each relevant event to a typed SSE frame using the `_sse()` helper. Each event is emitted as the corresponding graph node completes.

```
Backend _event_stream()                     Frontend parseSseStream()
─────────────────────────────               ──────────────────────────
graph.astream_events()
  │
  ├── on_chain_end / memory_loader    ──►   memory_loaded
  │
  ├── on_chain_start / planner        ──►   planner_start
  ├── on_chain_end / planner          ──►   planner_result  (+ tool_calls list)
  │
  ├── on_chain_start / tools          ──►   tool_start
  ├── on_chain_end / tools            ──►   tool_result
  │   [planner + tools repeat per ReAct iteration]
  │
  ├── on_chat_model_stream (per token) ──►  response_token  → text streams live
  │
  ├── on_chain_end / verifier         ──►   verifier_result
  ├── on_chain_end / memory_update    ──►   memory_updated
  │
  └── (after loop ends)               ──►   response_end    → final text
```

Wire format per event:
```
event: planner_result\n
data: {"thread_id": "...", "content": "...", "tool_calls": [...]}\n
\n
```

### 2.3 Tool Design

Tools are the mechanism through which the agent interacts with the real world. Each tool is a Python function decorated with LangChain's `@tool` decorator, which automatically extracts the function name, docstring, and parameter type annotations to build a JSON schema. This schema is attached to the LLM via `bind_tools()` in the planner node, giving the LLM a structured description of what each tool does and what arguments it expects. When the LLM decides to call a tool, it emits a `tool_calls` list in its response containing the tool name and the arguments it chose — it never calls the tool directly. LangGraph's `ToolNode` reads that list and dispatches the actual Python function calls.

All five tools share a common security principle: **no tool acts on a resource without first verifying it belongs to the active customer**. The `customer_id` is passed through the LangGraph `RunnableConfig` (not through the user's message) so the LLM cannot manipulate it. This prevents a customer from querying or modifying another customer's orders, complaints, or memory by including a different ID in their message. Tools return plain dictionaries — either a success payload or an `{"error": "..."}` field — rather than raising exceptions for business logic failures. This allows the LLM and the verifier node to read the error and reason about it gracefully.

| Tool | Purpose | DB Operation |
|---|---|---|
| `order_lookup` | Retrieve order details | `SELECT` from `orders` WHERE `customer_id` matches |
| `customer_profile` | Retrieve customer info | `SELECT` from `customers` |
| `refund` | Initiate a refund | `SELECT` to verify delivered, then `UPDATE` status |
| `complaint_logger` | File a complaint | `SELECT` to verify order exists, then `INSERT` into `complaints` |
| `memory_tool` | Read/write long-term memory | `SELECT` or `INSERT ... ON DUPLICATE KEY UPDATE` on `customer_memory` |

**`order_lookup`** is the most frequently called tool. It retrieves order details by combining the user-provided `order_id` with the config-injected `customer_id` in a single `WHERE` clause, so a non-existent order and a valid order belonging to a different customer produce the same `not found` response — no information is leaked.

**`refund`** performs two sequential database operations. First it selects the order to verify existence, ownership, and that the status is `delivered`. Only if all three conditions pass does it execute the `UPDATE`. This multi-step validation prevents refunds on pending or already-refunded orders, and prevents cross-customer refund attempts.

**`complaint_logger`** was initially written to INSERT directly without validation, which caused a MySQL foreign key constraint error when the LLM tried to log a complaint for a non-existent order. The tool now performs an existence and ownership check before the INSERT, and its docstring instructs the LLM to call `order_lookup` first before asking the user for the complaint issue — this prevents the agent from prompting the user to describe their problem before knowing whether the order is valid.

**`memory_tool`** is the only tool that operates on the `customer_memory` table at the agent's explicit discretion. When `action='read'`, it returns all memory entries for the customer, optionally filtered by key. When `action='write'`, it uses `INSERT ... ON DUPLICATE KEY UPDATE` to upsert a key-value pair, ensuring the table stays normalized with one row per key per customer. This tool enables the agent to honor requests like "remember that I prefer refunds" by explicitly writing a preference entry that will be loaded by `memory_loader` in all future sessions.

### 2.4 Infrastructure (Docker Compose)

The entire stack runs inside Docker Compose, which provides a reproducible environment where all four services start, connect, and shut down together. The services are wired with explicit `depends_on` conditions so they start in the correct order: MySQL must pass its healthcheck before the backend starts, and the backend must be running before the frontend starts. This prevents the backend from trying to connect to MySQL while it is still initializing, which would cause a startup crash.

#### Container Diagram

```
  ┌──────────────┐
  │ Host Browser │
  └──────┬───────┘
         │ :5173
         ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  HOST MACHINE — Docker Network (bridge)                             │
  │                                                                     │
  │  ┌─────────────────────┐      ┌─────────────────────────────────┐  │
  │  │  frontend           │      │  backend                        │  │
  │  │───────────────────  │      │─────────────────────────────    │  │
  │  │  React 19 + Vite    │─────►│  FastAPI (Python 3.11)          │  │
  │  │  port: 5173         │  HTTP│  port: 8000                     │  │
  │  │                     │◄─────│                                 │  │
  │  │  volume:            │  SSE │  /chat/stream  → LangGraph      │  │
  │  │  ./frontend → /app  │      │  /providers    → health check   │  │
  │  └─────────────────────┘      │  /customers    → MySQL          │  │
  │                               │  /orders       → MySQL          │  │
  │                               │  /complaints   → MySQL          │  │
  │                               │  /sessions     → MySQL          │  │
  │                               │  /memory/:id   → MySQL          │  │
  │                               │                                 │  │
  │                               │  volume: ./backend → /app       │  │
  │                               │  checkpoints.db (SQLite)        │  │
  │                               └──────────┬──────────┬───────────┘  │
  │                                    :3306 │    :11434 │              │
  │                                          │           │              │
  │                             ┌────────────▼──┐  ┌─────▼──────────┐  │
  │                             │  mysql        │  │  ollama        │  │
  │                             │─────────────  │  │──────────────  │  │
  │                             │  mysql:8      │  │  ollama/ollama │  │
  │                             │  port: 3306   │  │  port: 11434   │  │
  │                             │               │  │                │  │
  │                             │  customers    │  │  auto-pulls    │  │
  │                             │  orders       │  │  model on start│  │
  │                             │  complaints   │  │                │  │
  │                             │  cust_memory  │  │  volume:       │  │
  │                             │  sessions     │  │  ollama_data   │  │
  │                             │  session_msgs │  │  (model files) │  │
  │                             │               │  └────────────────┘  │
  │                             │  volume:      │                      │
  │                             │  mysql_data   │                      │
  │                             └───────────────┘                      │
  └─────────────────────────────────────────────────────────────────────┘
```

#### Startup Order

```
docker compose up
     │
     ├── mysql          image: mysql:8         port 3306
     │   └── seed.sql runs on first start (customers, orders, complaints, memory)
     │
     ├── ollama         image: ollama/ollama   port 11434
     │   └── entrypoint: serve + auto-pull OLLAMA_DEFAULT_MODEL on startup
     │
     ├── backend        build: ./backend       port 8000
     │   ├── depends on: mysql (healthy), ollama (started)
     │   └── bind-mount: ./backend → /app  (hot-reload via --reload)
     │
     └── frontend       build: ./frontend      port 5173
         ├── depends on: backend (started)
         └── bind-mount: ./frontend → /app  (Vite HMR)
```

**MySQL** uses the official `mysql:8` image. On first startup, any `.sql` files placed in `/docker-entrypoint-initdb.d/` inside the container are executed automatically. The entire `backend/db/` directory is mounted to that path, so `seed.sql` runs on the very first `docker compose up` and populates all six tables with the test data required to run the 11 test cases. This initialization only happens when the data volume (`mysql_data`) is empty — subsequent restarts reuse the persisted volume and skip the seed script. To reset to a clean state, the volume must be explicitly removed with `docker compose down -v`.

**Ollama** uses a custom entrypoint instead of the default one. The default `ollama/ollama` image simply starts the server but does not pull any models. The custom entrypoint runs `ollama serve` in the background, then polls `ollama list` in a loop until the server is ready, then pulls the model specified by the `OLLAMA_DEFAULT_MODEL` environment variable. Once the pull completes, the `wait` command keeps the container alive by waiting on the background server process. Because the model files are stored in the `ollama_data` volume, the pull is skipped on subsequent restarts if the model is already present — only the first startup incurs the download time.

**Backend and Frontend** both use bind mounts to map the local source code directories directly into the running containers (`./backend → /app` and `./frontend → /app`). This means any file saved on the host is immediately visible inside the container. The backend runs Uvicorn with `--reload`, which watches for file changes and restarts the Python process automatically. The frontend runs Vite's development server, which has built-in Hot Module Replacement (HMR) that pushes changes to the browser without a full page reload. Together, these mounts eliminate the need to rebuild Docker images during development — code changes take effect in seconds.

### 2.5 Database Schema

The database schema is designed around the customer as the central entity. Every table except `customers` itself holds a `customer_id` foreign key, ensuring that all data — orders, complaints, memory, and conversation history — is always scoped to a specific customer. This design directly supports the ownership enforcement in the tool layer, where every query includes a `customer_id` condition to prevent cross-customer data access.

```
customers
  │  customer_id (PK)
  │  name, email, created_at
  │
  ├──< orders
  │      order_id (PK)
  │      customer_id (FK → customers)
  │      product_name, status, order_date, delivery_date
  │
  ├──< complaints
  │      complaint_id (PK, AUTO_INCREMENT)
  │      customer_id (FK → customers)
  │      order_id    (FK → orders)
  │      issue, status, created_at
  │
  ├──< customer_memory
  │      id (PK, AUTO_INCREMENT)
  │      customer_id (FK → customers)
  │      key, value, created_at
  │      UNIQUE (customer_id, key)
  │
  └──< sessions
         thread_id (PK)
         customer_id (FK → customers)
         created_at, ended_at
         │
         └──< session_messages
                message_id (PK, AUTO_INCREMENT)
                thread_id (FK → sessions)
                role, content, created_at
```

**`orders`** holds the core transactional data. The `status` column drives the agent's business logic — the refund tool checks for `delivered` before proceeding, and complaint_logger verifies the order exists before inserting. The `delivery_date` column is nullable, as orders that have not yet been delivered have no delivery date.

**`complaints`** carries a foreign key to both `customers` and `orders`. The double FK means a complaint can only be filed for an order that exists in the `orders` table. This is enforced at the database level — attempting to insert a complaint for a non-existent `order_id` will raise a constraint violation (MySQL error 1452), which is why the `complaint_logger` tool verifies the order exists via a `SELECT` before attempting the `INSERT`.

**`customer_memory`** has a composite unique key on `(customer_id, key)`. This is what makes the `INSERT ... ON DUPLICATE KEY UPDATE` pattern work — there can be at most one value per key per customer, so writing the same key twice updates the existing row rather than inserting a duplicate. This table serves as the agent's persistent scratchpad: automatically written by `memory_update` after every turn and explicitly written by the `memory_tool` when the user asks the agent to remember something.

**`sessions`** and **`session_messages`** record the full conversation history for display in the sidebar's session history panel. A session is created with `INSERT IGNORE` when the first message of a thread arrives — `INSERT IGNORE` means sending a follow-up message on an existing `thread_id` silently skips the session row creation without causing an error. Each human and AI message is inserted as a separate row in `session_messages` with a `role` field (`human` or `ai`), allowing the session detail view to reconstruct the full conversation transcript in order.

---

## 3. Test Cases and Results

The test suite is derived from the Minimal Test Score List defined in the project specification (Section 9). Each of the 11 test cases targets a single distinct capability of the agent — from basic intent parsing through to multi-step reasoning, memory persistence, and hallucination prevention. The tests are designed so that each can be run independently in a fresh conversation, with the exception of Test 7 (Short-Term Memory) which requires Test 1 to be run first in the same session so that order 12345 is present in the conversation history.

All test cases are run against **Customer 1: Ahmad Rifqi (`customer_id = 1`)** using the seed data pre-loaded into MySQL by `backend/db/seed.sql`. The seed data was deliberately constructed to match the order IDs and statuses referenced in the project specification test cases — each order in the seed is annotated with a comment indicating which test it supports. A parallel set of 11 equivalent test cases using different order IDs for Customer 2 (Jane Doe) is documented in `docs/test-cases.md`, providing an independent verification pass against the same functional areas.

### 3.1 Seed Data Reference

The following seed data is pre-loaded into the `orders` table for Customer 1. Each row is assigned to a specific test case based on its status — orders with status `pending` or `processing` test lookup and tracking scenarios, while `delivered` orders are required for refund and complaint eligibility. Order 0000 is intentionally absent from the database to serve as the invalid order used in the verifier test.

| Order ID | Product | Status | Delivery Date | Covers Test |
|---|---|---|---|---|
| 12345 | Wireless Headphones | pending | — | TC-1 (Intent Parsing), TC-7 (STM) |
| 1001 | Mechanical Keyboard | processing | — | TC-2 (Order Lookup) |
| 5678 | USB-C Hub | delivered | 2026-03-15 | TC-4 (Refund) |
| 2222 | Laptop Stand | delivered | 2026-03-25 | TC-5 (Complaint) |
| 7890 | Monitor Arm | delivered | 2026-03-07 | TC-6 (Multi-step) |
| 0000 | (absent — not in DB) | — | — | TC-11 (Verifier) |

In addition to orders, the seed pre-loads four `customer_memory` entries for Customer 1: `delivery_history_1001`, `delivery_history_12345`, `late_delivery_pattern`, and `complaint_count`. These entries are read by the `memory_loader` node and injected into the system prompt, making them available to the LLM for TC-8 (LTM Read) and TC-10 (Personalization) without requiring a prior conversation to have generated them.

### 3.2 Test Case Descriptions

Each test case targets one specific function of the agent. The following descriptions explain what each test is intended to verify and what the expected agent behavior is at both the LLM and database level.

**TC-1 — Intent Parsing:** Tests whether the agent can correctly extract structured information from a natural language query. The query "Where is my order 12345?" contains no explicit command verb — the agent must infer that the user intends to track an order, identify the entity (order_id = 12345), call `order_lookup`, and return the current status. This tests the LLM's ability to map free-form language to a tool invocation without explicit instruction.

**TC-2 — OrderLookupTool:** Tests the `order_lookup` tool directly. The query "Check status of order 1001" is more explicit than TC-1 and should produce a clean single-tool call. The expected response includes the product name (Mechanical Keyboard) and status (processing), confirming that the tool query reached MySQL and the result was interpreted correctly.

**TC-3 — CustomerProfileTool:** Tests the `customer_profile` tool, which takes no arguments beyond the implicitly available `customer_id`. The query "Show my profile" should trigger a call to `customer_profile`, and the response should include the customer's name and email address as stored in the `customers` table.

**TC-4 — RefundTool:** Tests the refund workflow end-to-end. Order 5678 (USB-C Hub) has status `delivered`, which is the only status eligible for a refund. The agent should call `order_lookup` to verify the order, then call `refund` to update the status to `refund_requested`. The database state change can be confirmed via the Data Explorer panel after the interaction.

**TC-5 — ComplaintLoggerTool:** Tests the complaint filing workflow. The agent should recognize the complaint intent, verify that order 2222 exists and belongs to the customer via `order_lookup`, ask the user to describe their issue, and then call `complaint_logger` with the provided issue text to insert a new row into the `complaints` table. A new complaint record should appear in the database afterward.

**TC-6 — Multi-step Reasoning:** Tests the agent's ability to chain two tool calls with conditional logic. The query "Refund order 7890 if delivered" requires the agent to first call `order_lookup`, check that the returned status is `delivered`, and only then call `refund`. This verifies that the LLM can perform conditional reasoning over tool results within the ReAct loop rather than executing both tools blindly.

**TC-7 — Short-Term Memory (STM):** Tests the LangGraph checkpointer's conversation history. This test must be run in the same session as TC-1 — after asking "Where is my order 12345?", the user sends "Cancel it" without specifying the order. The LLM must resolve "it" by referencing the prior turn in the `messages` history and apply the cancellation to order 12345. This verifies that STM is correctly restored across turns within the same `thread_id`.

**TC-8 — Long-Term Memory (Read):** Tests that the agent can retrieve and report information from the `customer_memory` table. The query "What issues have I had before?" should trigger a `memory_tool` call with `action='read'`, or alternatively the agent may answer directly from the `memory_context` already injected into the system prompt by `memory_loader`. The response should reference the seeded delivery history entries and complaint count.

**TC-9 — Long-Term Memory (Write):** Tests that the agent can persist a user-stated preference to the `customer_memory` table. The query "Remember I prefer refunds over store credit" should trigger a `memory_tool` call with `action='write'`, inserting or updating a preference key. The entry should be visible in the Memory Manager panel and should be loaded by `memory_loader` in subsequent sessions.

**TC-10 — Personalization:** Tests that the agent uses long-term memory to personalize its response. The query "My order is late again" provides no order ID and no new information — the word "again" implies a recurring pattern. The agent should detect the `late_delivery_pattern` entry in the system prompt (injected by `memory_loader` from the seeded data) and acknowledge the repeated issue with an empathetic response that references the customer's history.

**TC-11 — Verifier:** Tests the hallucination prevention mechanism. Order 0000 does not exist in the database. Requesting a refund for it should cause `refund` to return `{"error": "Order 0000 not found."}`. The verifier then checks whether the LLM's response acknowledges the failure. If the LLM correctly says the order was not found, the verifier passes it through. If the LLM incorrectly confirms a successful refund, the verifier injects an override message. Either way, the user must not receive a false confirmation.

### 3.3 Test Results

| # | Function | Test Query | Expected Behavior | Result |
|---|---|---|---|---|
| 1 | Intent Parsing | Where is my order 12345? | Identify intent = tracking, call order_lookup(12345), return pending status | **PASS** — agent correctly identified tracking intent, retrieved order 12345 (Wireless Headphones, pending, no delivery date) |
| 2 | OrderLookupTool | Check status of order 1001 | Call order_lookup(1001), return processing status for Mechanical Keyboard | **PASS** — agent returned status = processing with no delivery date for order 1001 |
| 3 | CustomerProfileTool | Show my profile | Call customer_profile(), return Ahmad Rifqi name and email | **PASS** — agent returned customer_id = 1, name = Ahmad Rifqi, email = customer1@example.com, account created date |
| 4 | RefundTool | Refund order 5678 | Verify delivered, call refund(5678), status updated to refund_requested | **PASS** — agent initiated refund for order 5678 and informed user to expect credit within 3–5 business days |
| 5 | ComplaintLoggerTool | I want to complain about order 2222 | Verify order exists, collect issue, call complaint_logger(2222, issue) | **PARTIAL** — complaint was logged (complaint ID = 5 confirmed), but agent asked for issue details *after* logging rather than before; complaint record updated on follow-up turn |
| 6 | Multi-step Reasoning | Refund order 7890 if delivered | Call order_lookup → confirm delivered → call refund(7890) | **PASS** — agent called order_lookup, confirmed the delivered status, and submitted refund request for order 7890 |
| 7 | Short-Term Memory | Cancel order 12345, I don't want to wait longer | Resolve order from session context, attempt cancellation | **PARTIAL** — agent correctly referenced the shipping delay from session/LTM context, but could not cancel the order as no cancellation tool exists; redirected user to file a complaint instead |
| 8 | Long-Term Memory (Read) | What issues have I had before? | Retrieve and report delivery_history and complaint_count from customer_memory | **PARTIAL** — first response claimed it could not retrieve a comprehensive list; on follow-up ("Yes give me those complaint histories") agent correctly reported all delivery history entries and complaint records from long-term memory |
| 9 | Long-Term Memory (Write) | Please remember I prefer refunds | Call memory_tool(write), persist preference to customer_memory | **PASS** — agent acknowledged the preference and noted it; memory_tool upserted the preference entry to customer_memory |
| 10 | Personalization | My order is late again | Detect late_delivery_pattern in LTM, acknowledge repeated issue | **PASS** — agent referenced prior delivery delays from customer history (order 1001 late in March 2026, order 12345 warehouse backlog) when discussing issues, demonstrating awareness of repeated patterns |
| 11 | Verifier | Refund order 0000 | order_lookup returns error, no false confirmation issued | **PASS** — agent responded "I cannot refund order 0000. I can only refund valid orders that are delivered." No false success confirmation was issued |

#### Observations

**TC-4 re-run note:** When "Refund order 5678" was sent a second time later in the session, the agent correctly rejected it — because the refund had already been processed and the order status was no longer `delivered`. The tool returned an ineligibility error, which the agent reported accurately. This demonstrates that the refund tool's status check is functioning correctly.

**TC-5 behavior:** The complaint was logged before the issue description was collected, resulting in an empty `issue` field on the first insert. The agent then updated the record on the follow-up turn. This reveals a sequencing issue in the complaint workflow — the tool should collect the issue description before calling `complaint_logger`, which is addressed by the docstring instruction added to the tool.

**TC-7 limitation:** The short-term memory test exposed that the agent lacks a cancellation tool. The agent correctly identified the order from context and referenced the relevant history, but could only redirect the user to a complaint rather than executing a cancellation. Adding a `cancel_order` tool would close this gap.

**TC-8 behavior:** The agent's initial reluctance to report complaint history ("I cannot retrieve a comprehensive list") despite having the data in its system prompt indicates that the LLM did not fully utilize the injected `memory_context` on the first response. It succeeded on the follow-up, suggesting that the system prompt formatting or the LLM's instruction-following could be strengthened for memory retrieval queries.

**TC-6 bonus verification:** After TC-6 processed the refund for order 7890, a follow-up "refund order 7890" correctly returned "You've previously requested a refund for order 7890. The request was successful." — confirming that the status update persisted in MySQL and the agent reads live data rather than cached state.

**Non-seeded order test (order 6769):** An additional test with a non-existent order confirmed correct behavior — the agent looked up the order first, received a not-found error, and informed the user it could not be found without asking for further details.

---

## 4. Features

### 4.1 Multi-Provider LLM Support

The agent supports two interchangeable LLM backends selectable at runtime through the provider dropdown in the sidebar. The selection is sent as a field in every chat request, meaning the user can switch providers at any time without restarting the application.

**OpenRouter** connects to a cloud-hosted inference service that exposes an OpenAI-compatible API. The backend instantiates a `ChatOpenAI` client pointed at `https://openrouter.ai/api/v1` using the `OPENROUTER_API_KEY` environment variable. OpenRouter acts as a gateway to a wide catalog of models — the specific model used is controlled by the `DEFAULT_MODEL` environment variable. This provider offers fast response times because inference runs on dedicated cloud hardware, making it the practical choice for development, testing, and demonstrations.

**Ollama** runs a model locally inside the Docker network. The backend instantiates a `ChatOllama` client pointed at `http://ollama:11434`, the internal Docker hostname of the Ollama container. The model used is controlled by `OLLAMA_DEFAULT_MODEL`. Because inference runs on the host machine's CPU (or GPU if configured), response latency is significantly higher than OpenRouter — a 4-billion parameter model on CPU typically generates 3–10 tokens per second. The tradeoff is complete data privacy and no dependency on external API keys or internet connectivity, which makes Ollama suitable for air-gapped or sensitive environments.

Both providers are abstracted behind LangChain's common `BaseChatModel` interface. The `llm_factory.py` module is the only place where the provider distinction exists — the rest of the agent, including the planner node and all tools, has no knowledge of which backend is in use. Switching providers starts a fresh conversation because the model and its context window are inherently different, so the session state is reset on provider change.

### 4.2 ReAct Agent with Tool Calling

Rather than generating a response purely from the LLM's parametric knowledge, the agent uses the ReAct paradigm to ground its answers in real data retrieved from MySQL. The LLM is given the schema of five tools via `bind_tools()` and decides which — if any — to call based on the user's intent. This makes the agent's responses accurate and current, not hallucinated.

The five tools cover the complete set of customer service operations that a human agent would perform:

- **Order lookup** — retrieves the current status, product name, order date, and delivery date for a specific order. This is the most frequently called tool, used both as a direct answer to status queries and as a prerequisite verification step before refunds or complaints.
- **Customer profile** — fetches the customer's name and email from the `customers` table. Used when the customer asks about their account details or when the agent needs to address the customer by name.
- **Refund initiation** — validates that the order exists, belongs to the customer, and has a status of `delivered` before executing an `UPDATE` that sets the status to `refund_requested`. Orders that are still pending or processing are explicitly rejected with an informative error.
- **Complaint filing** — verifies the order exists and belongs to the customer, then inserts a new row into the `complaints` table. The agent is instructed via the tool docstring to call `order_lookup` before asking for the issue description, preventing the agent from prompting the user for details about a non-existent order.
- **Memory read/write** — gives the agent explicit control over the `customer_memory` table. The agent calls this tool with `action='write'` when the user states a preference (e.g. "remember I prefer store credit") and with `action='read'` to look up specific stored information on demand.

The ReAct loop terminates when the LLM produces a response with no `tool_calls`. The loop is capped at 10 iterations to prevent runaway chains in edge cases where the LLM cannot converge.

### 4.3 Dual-Layer Memory

Memory is one of the defining features that distinguishes this agent from a stateless question-answering system. The agent maintains awareness across both individual conversation turns and long stretches of time through two independent memory mechanisms that complement each other.

**Short-Term Memory (STM)** is implemented through LangGraph's checkpointer, which persists the full `messages` list (all human turns, AI responses, and tool results) to a SQLite database after every node execution, keyed by `thread_id`. When the user sends a follow-up message in the same conversation, the graph is resumed from its last checkpoint and the LLM receives the full history. This is what enables the agent to correctly handle ambiguous references like "cancel it" or "what about that order?" without the user having to repeat context. STM is entirely automatic — no application code manages it beyond configuring the checkpointer.

**Long-Term Memory (LTM)** is stored in the `customer_memory` MySQL table as key-value pairs scoped to a `customer_id`. Unlike STM, LTM survives session boundaries and accumulates over time. It is written from two sources: the `memory_update` node automatically records a timestamped `last_interaction_summary` after every turn capturing what happened (which tools were used, what the outcomes were), and the agent can write arbitrary entries via `memory_tool` when the user explicitly asks it to remember something. At the start of every turn, `memory_loader` reads all LTM entries and injects them into the system prompt, so the LLM is aware of the customer's history from the very first token of its response. LTM enables personalization behaviors such as recognizing a repeated late delivery complaint, recalling a customer's stated refund preference, or noting patterns across past interactions.

### 4.4 Response Verification

LLMs can occasionally produce incorrect or overconfident responses — for example, confirming that a refund was successfully processed even when the underlying tool returned an error. The verifier node is a lightweight safeguard that runs after every complete agent response to catch this class of failure before it reaches the user.

The verifier inspects all `ToolMessage` results accumulated during the turn and looks for two failure patterns. First, it checks for any `{"error": "..."}` field in a tool result, which indicates the tool explicitly reported a failure (such as an order not found or an ownership check that failed). Second, it checks for tool results where a data field contains an empty list, which may indicate a lookup that returned no matching records. If either pattern is detected, the verifier then checks the LLM's final response for acknowledgment keywords — phrases like "not found", "cannot", "unable", "does not exist", and similar. If the LLM already acknowledged the failure in its response, the verifier passes it through unchanged. If the LLM's response does not acknowledge the failure — indicating a potential hallucination — the verifier injects a safe override message: "I could not complete that request: [error details]." This override replaces the LLM's response in the state before it is sent to the user, ensuring that the user always receives an honest response even when the LLM misbehaves.

### 4.5 Real-Time Streaming UI

Because the agent workflow can span multiple LLM calls and database queries, waiting for the full response before showing anything to the user would create a poor experience with several seconds of silence. The frontend addresses this by consuming the SSE event stream from the backend and updating the UI incrementally as each event arrives.

LLM response tokens are streamed directly into the chat bubble character by character as they are generated. This means the user starts reading the response while the LLM is still producing it, significantly reducing the perceived latency. Alongside the chat bubble, the Agent Process panel in the right sidebar displays a live timeline of every step the agent took during the turn: which memory entries were loaded, when the planner started reasoning, which tools were called and what they returned, the verification outcome, and when memory was updated. This transparency panel serves both as a debugging tool for developers and as an educational view that makes the agent's reasoning process observable. Each event type in the timeline is rendered differently — tool calls show the arguments, tool results show the database response, and the verifier result shows whether the checks passed or an override was applied.

### 4.6 Session History

Every conversation is automatically persisted to MySQL as it happens. Each distinct chat thread (identified by a `thread_id` UUID) is stored as a row in the `sessions` table, and each individual message — both from the user and from the agent — is stored as a row in `session_messages` with a `role` field indicating whether it is a `human` or `ai` message.

The sidebar displays the list of past sessions for the currently selected customer, fetched from `GET /sessions`. Clicking a session loads its full transcript via `GET /sessions/:thread_id` and switches the chat panel into a read-only history view. In history mode, the composer (input box and send button) is disabled so the user cannot accidentally send messages into a replayed session. The history view renders the transcript using the same message bubble components as the live chat, providing a consistent visual experience. Sessions are created with `INSERT IGNORE` so that sending multiple messages in the same thread does not create duplicate session rows.

### 4.7 Data Explorer

The Data Explorer is a panel in the right sidebar that provides a transparent, read-only view into the live state of the database for the active customer. It shows three sections simultaneously: the full list of all customers in the system, the orders belonging to the currently selected customer, and the complaints filed by that customer.

This panel exists primarily for verification purposes during testing and demonstration. When a test case calls `RefundTool` on order 5678, the expected outcome is that the order's status changes to `refund_requested` in the database. Without the Data Explorer, confirming this would require querying the database directly. With it, the tester can click "Refresh" after the agent responds and immediately see the updated status in the Orders section. Similarly, after filing a complaint through the agent, the new complaint record appears in the Complaints section. The panel loads its data on mount and on every customer switch, with a manual Refresh button for on-demand updates. All three data sections are fetched in parallel via `Promise.all` to minimize load time.

### 4.8 Memory Manager

The Memory Manager is a CRUD interface for the `customer_memory` table, providing direct access to the long-term memory entries that the agent reads and writes. It allows users to view all current memory entries for the active customer, add new key-value pairs, edit the value of existing entries inline, and delete entries individually.

This panel serves two practical purposes. During a demonstration or test run, it allows the operator to pre-seed specific memory entries before a conversation — for example, writing a `late_delivery_pattern` entry before running test case 10 (Personalization) to ensure the agent detects the repeated issue pattern from the very first turn. This removes the dependency on having a prior conversation history to trigger the behavior. During development, it allows developers to inspect what the `memory_update` node wrote after each turn and to clean up or correct stale entries without needing database access.

The panel tracks unsaved edits with a dirty state flag. If the user has an unsaved edit in the Memory Manager and tries to switch to a different customer, a confirmation dialog warns them that their unsaved changes will be discarded. This prevents accidental data loss during multi-customer testing sessions.