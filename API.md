# API Contract (Frontend Integration)

Source of truth: current backend implementation in `backend/main.py`, `backend/routes/*`, `backend/graph/*`, `backend/db/seed.sql` and route tests.

No versioning in API paths yet.

## 1) Global Contract

- Base URL: `http://<backend-host>:8000`
- Auth: none (no token/session auth layer in current implementation)
- Request body format: JSON (`application/json`) for non-stream routes
- Streaming route format: SSE (`text/event-stream`)
- CORS: allows `http://localhost:5173`
- Datetime fields: returned from MySQL rows; frontend should treat as string timestamps (ISO-like or DB-driver stringified)

### Error shape

- Validation error (FastAPI): HTTP `422`, body like:
  - `{"detail":[...]}`
- Manual not-found errors:
  - HTTP `404`, `{"detail":"Session not found"}`
  - HTTP `404`, `{"detail":"Memory entry not found"}`

## 2) Endpoint Index

- `GET /health`
- `GET /providers`
- `POST /chat/stream` (SSE)
- `GET /sessions`
- `GET /sessions/{session_id}`
- `GET /memory/{customer_id}`
- `PUT /memory/{customer_id}`
- `DELETE /memory/{customer_id}/{key}`
- `GET /customers`
- `GET /orders`
- `GET /complaints`

## 3) Endpoints

### `GET /health`

Health check.

Success `200`:

```json
{"status":"ok"}
```

### `GET /providers`

Returns runtime availability + discovered models for both providers.

Success `200`:

```json
{
  "openrouter": {
    "available": true,
    "models": ["google/gemini-2.5-flash", "openai/gpt-4o"]
  },
  "ollama": {
    "available": true,
    "models": ["qwen3:4b", "llama3.2"]
  }
}
```

Notes:

- If provider check fails/unreachable, route still returns `200` with `available:false` and empty `models`.
- Timeout for provider checks: ~5s.

### `POST /chat/stream`

Primary chat endpoint. Returns **Server-Sent Events**.

Request body:

```json
{
  "message": "Where is my order 12345?",
  "customer_id": 1,
  "thread_id": "optional-existing-thread-id",
  "provider": "optional: openrouter|ollama",
  "model": "optional-model-id"
}
```

Request rules:

- Required: `message` (string), `customer_id` (int)
- Optional: `thread_id`, `provider`, `model`
- If `thread_id` omitted, backend generates UUID string
- If `provider` omitted, backend defaults to `openrouter`
- If `model` omitted, backend uses provider default model from env config

Response:

- HTTP status on stream open: `200`
- Content-Type: `text/event-stream`
- Headers include:
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`

SSE frame format:

```text
event: <event_name>
data: <json>

```

#### SSE Event Types and Payloads

`memory_loaded`

```json
{
  "thread_id": "string",
  "memory_context": [
    {"type":"memory","key":"string","value":"string"},
    {"type":"complaint","order_id":2222,"issue":"...","status":"open","created_at":"..."}
  ]
}
```

`planner_start`

```json
{"thread_id":"string"}
```

`planner_result`

```json
{
  "thread_id":"string",
  "content":"assistant reasoning/output text",
  "tool_calls":[
    {"name":"order_lookup","args":{"order_id":12345}}
  ]
}
```

`tool_start`

```json
{"thread_id":"string"}
```

`tool_result`

```json
{
  "thread_id":"string",
  "results":"stringified tool node output"
}
```

Note: `results` is currently emitted as `str(output)`, not normalized JSON contract.

`verifier_result`

```json
{
  "thread_id":"string",
  "valid": true,
  "checks": ["all checks passed"],
  "override_message": null
}
```

`memory_updated`

```json
{"thread_id":"string"}
```

`response_token`

```json
{
  "thread_id":"string",
  "token":"partial token/chunk"
}
```

`response_end`

```json
{
  "thread_id":"string",
  "response":"full assembled ai response"
}
```

`error`

```json
{
  "thread_id":"string",
  "error":"error message"
}
```

Streaming behavior notes:

- Planner/tool loop can repeat multiple times.
- `response_token` can be interleaved while graph is running.
- `response_end` is final success event.
- On runtime failure, stream emits `error` event (stream itself may still be HTTP `200`).

Persistence side effects:

- At stream start:
  - upsert into `sessions(thread_id, customer_id)`
  - insert human message into `session_messages` with role `human`
- At stream end:
  - concatenated AI tokens persisted to `session_messages` with role `ai` (if non-empty)

### `GET /sessions`

List sessions metadata.

Success `200`:

```json
[
  {
    "thread_id":"abc-123",
    "customer_id":1,
    "created_at":"2026-05-01T10:00:00",
    "first_message":"Where is my order?"
  }
]
```

Order: newest first (`created_at DESC`).

### `GET /sessions/{session_id}`

Get ordered message history for one session.

Success `200`:

```json
[
  {"message_id":1,"role":"human","content":"Hello","created_at":"2026-05-01T10:00:00"},
  {"message_id":2,"role":"ai","content":"Hi there","created_at":"2026-05-01T10:00:01"}
]
```

Order: oldest first (`created_at ASC`).

Not found `404`:

```json
{"detail":"Session not found"}
```

### `GET /memory/{customer_id}`

Read long-term memory KV entries for customer.

Success `200`:

```json
[
  {"key":"late_delivery_pattern","value":"...","created_at":"2026-01-01T00:00:00"}
]
```

### `PUT /memory/{customer_id}`

Bulk upsert memory entries.

Request body:

```json
[
  {"key":"preferred_channel","value":"email"},
  {"key":"vip_status","value":"true"}
]
```

Success `200`:

```json
{"updated":2}
```

### `DELETE /memory/{customer_id}/{key}`

Delete one memory key.

Success `200`:

```json
{"deleted":true}
```

Not found `404`:

```json
{"detail":"Memory entry not found"}
```

### `GET /customers`

Returns raw customer rows.

Success `200`:

```json
[
  {"customer_id":1,"name":"Ahmad Rifqi","email":"customer1@example.com","created_at":"..."}
]
```

### `GET /orders`

Returns raw order rows.

Query params:

- `customer_id` (optional int)

Success `200`:

```json
[
  {
    "order_id":12345,
    "customer_id":1,
    "product_name":"Wireless Headphones",
    "status":"pending",
    "order_date":"...",
    "delivery_date":null
  }
]
```

### `GET /complaints`

Returns raw complaint rows.

Query params:

- `customer_id` (optional int)

Success `200`:

```json
[
  {
    "complaint_id":1,
    "customer_id":1,
    "order_id":5678,
    "issue":"Package arrived late",
    "status":"resolved",
    "created_at":"..."
  }
]
```

## 4) Frontend Integration Rules (Practical)

1. Treat `thread_id` from first received event as canonical conversation ID. Reuse it in next `/chat/stream` call.
2. Parse SSE by `event` name; do not assume strict one-pass order except `response_end` or `error` as terminal signals.
3. Build live assistant text from `response_token`; reconcile/finalize with `response_end.response`.
4. Treat `tool_result.results` as opaque debug text, not stable JSON.
5. Handle HTTP `422` for malformed request bodies.
6. Handle `404` for deleted/missing session or memory key.

## 5) Current Non-Goals / Gaps (Important for FE)

- No auth/authorization. `customer_id` is client-supplied and trusted server-side.
- No API versioning (`/v1` absent).
- No pagination on list endpoints.
- No stable schema wrapper for most list routes (raw DB row arrays).
- `error` in SSE is event-level, not guaranteed as non-200 HTTP.
