# API Contract (Current Backend Implementation)

Source of truth: `backend/main.py`, `backend/routes/*`, `backend/llm_factory.py`, `backend/db/seed.sql`, and backend route tests.

This document reflects the implementation after issue `#18`, issue `#19`, and issue `#27`.

No API versioning is implemented in the path structure.

## 1) Global Contract

- Base URL: `http://<backend-host>:8000`
- Auth: none
- Standard request/response format: JSON
- Streaming format: Server-Sent Events (`text/event-stream`)
- CORS: allows `http://localhost:5173`
- Datetime fields come from MySQL rows and should be treated as timestamp strings by the frontend

### Error Shapes

- FastAPI validation errors: HTTP `422`

```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

- Manual `404` responses:

```json
{"detail":"Session not found"}
```

```json
{"detail":"Memory entry not found"}
```

```json
{"detail":"Customer not found"}
```

```json
{"detail":"Order not found"}
```

```json
{"detail":"Complaint not found"}
```

- Manual `400` for empty update payloads:

```json
{"detail":"No fields to update"}
```

- Chat runtime failures are emitted as SSE `error` events and may still return HTTP `200`.

## 2) Endpoint Index

- `GET /health`
- `GET /providers`
- `POST /chat/stream`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `GET /memory/{customer_id}`
- `PUT /memory/{customer_id}`
- `DELETE /memory/{customer_id}/{key}`
- `GET /customers`
- `POST /customers`
- `PUT /customers/{customer_id}`
- `DELETE /customers/{customer_id}`
- `GET /orders`
- `POST /orders`
- `PUT /orders/{order_id}`
- `DELETE /orders/{order_id}`
- `GET /complaints`
- `POST /complaints`
- `PUT /complaints/{complaint_id}`
- `DELETE /complaints/{complaint_id}`

## 3) Endpoints

### `GET /health`

Health check.

Success `200`:

```json
{"status":"ok"}
```

### `GET /providers`

Returns provider availability filtered to the configured default model for each provider.

Success `200`:

```json
{
  "openrouter": {
    "available": true,
    "models": ["google/gemini-2.5-flash"],
    "default_model": "google/gemini-2.5-flash"
  },
  "ollama": {
    "available": true,
    "models": ["qwen3:4b"],
    "default_model": "qwen3:4b"
  }
}
```

Notes:

- The route does not return every discovered model.
- Each provider is reported as available only when:
  - the provider is reachable, and
  - the configured default model is present in that provider's discovered model list
- If a provider is unreachable or the configured default model is missing, the response is still `200` and that provider becomes:

```json
{
  "available": false,
  "models": [],
  "default_model": null
}
```

### `POST /chat/stream`

Primary chat endpoint. Returns SSE.

Request body:

```json
{
  "message": "Where is my order 12345?",
  "customer_id": 1,
  "agent_type": "customer_service",
  "thread_id": "optional-existing-thread-id",
  "provider": "optional: openrouter|ollama",
  "model": "accepted-by-schema-but-currently-ignored"
}
```

Request rules:

- Required: `message` (string)
- Optional: `customer_id` (int | null), `agent_type` (string, default `"customer_service"`), `thread_id`, `provider`, `model`
- If `thread_id` is omitted, backend generates a UUID string
- If `provider` is omitted, backend defaults to `openrouter`
- `model` is currently ignored by the route implementation
- Effective model selection is always provider-default:
  - `openrouter` -> `DEFAULT_MODEL`
  - `ollama` -> `OLLAMA_DEFAULT_MODEL`
- `provider` is not validated at request-schema level; an unsupported value can fail later and surface as SSE `error`

`agent_type` validation (enforced by Pydantic model validator, returns HTTP `422` on failure):

- Accepted values: `"customer_service"`, `"refund_email"`, `"calendar"`
- Unknown `agent_type` -> `422` with message `"Unknown agent_type '<value>'. Must be one of: [...]"`
- `agent_type == "customer_service"` and `customer_id` is absent/null -> `422` with message `"customer_id is required for agent_type 'customer_service'"`
- `agent_type` is a workspace type (`"refund_email"` or `"calendar"`) and `customer_id` is present -> `422` with message `"customer_id must not be provided for workspace agent_type '<value>'"`

Response:

- HTTP status on stream open: `200`
- Content-Type: `text/event-stream`
- Response headers include:
  - `Cache-Control: no-cache`
  - `X-Accel-Buffering: no`

SSE frame format:

```text
event: <event_name>
data: <json>

```

#### SSE Event Types

`memory_loaded`

```json
{
  "thread_id": "string",
  "memory_context": [
    {"type":"memory","key":"string","value":"string"},
    {
      "type":"complaint",
      "order_id": 2222,
      "issue": "Package arrived late",
      "status": "resolved",
      "created_at": "2026-05-01 10:00:00"
    }
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
  "content":"Checking order",
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
  "tool_name":"order_lookup",
  "results":{"order_id":12345,"status":"pending"}
}
```

`tool_result` notes:

- The backend now emits one `tool_result` event per tool message.
- `results` is normalized when possible:
  - JSON string content becomes parsed JSON
  - plain strings become `{"raw":"..."}`
  - dict/list/bool/int/float/null pass through

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
{
  "thread_id":"string",
  "key":"last_interaction_summary",
  "value":"User asked for refund details."
}
```

`memory_updated` notes:

- `key` and `value` are emitted directly from the memory update node output.
- If the node output omits them or returns non-string values, the route falls back to empty strings.

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

- The planner/tool loop can repeat multiple times.
- `tool_start` may be followed by zero or many `tool_result` events.
- `response_token` events are emitted only when model stream chunks contain non-empty content.
- `response_end` is the terminal success event.
- Runtime failures emit `error`; they do not guarantee a non-200 HTTP status.

Persistence side effects:

- At stream start:
  - upsert into `sessions(thread_id, customer_id, agent_type)`
  - insert human message into `session_messages` with role `human`
- At stream end:
  - concatenated AI tokens are inserted into `session_messages` with role `ai` only if non-empty

### `GET /sessions`

Returns session metadata.

Success `200`:

```json
[
  {
    "thread_id":"abc-123",
    "customer_id":1,
    "agent_type":"customer_service",
    "created_at":"2026-05-01 10:00:00",
    "first_message":"Where is my order?"
  }
]
```

Notes:

- Ordered newest first by `sessions.created_at DESC`
- `first_message` is the earliest `human` message for that thread
- `customer_id` is nullable (null for workspace agent sessions)

### `GET /sessions/{session_id}`

Returns session metadata and ordered message history for one session.

Success `200`:

```json
{
  "session": {
    "thread_id": "abc-123",
    "customer_id": 1,
    "agent_type": "customer_service",
    "created_at": "2026-05-01 10:00:00"
  },
  "messages": [
    {
      "message_id":1,
      "role":"human",
      "content":"Hello",
      "created_at":"2026-05-01 10:00:00"
    },
    {
      "message_id":2,
      "role":"ai",
      "content":"Hi there",
      "created_at":"2026-05-01 10:00:01"
    }
  ]
}
```

Notes:

- `messages` ordered oldest first by `session_messages.created_at ASC`
- `session.customer_id` is nullable (null for workspace agent sessions)

Not found `404`:

```json
{"detail":"Session not found"}
```

### `GET /memory/{customer_id}`

Returns all saved memory entries for a customer.

Success `200`:

```json
[
  {
    "key":"late_delivery_pattern",
    "value":"Customer has a late delivery pattern across fulfilled orders",
    "created_at":"2026-05-01 10:00:00"
  }
]
```

### `PUT /memory/{customer_id}`

Bulk upserts memory entries.

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

Notes:

- Upsert key is `(customer_id, key)`
- Response count is the number of request entries processed, not the number of rows newly inserted

### `DELETE /memory/{customer_id}/{key}`

Deletes one memory key.

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
  {
    "customer_id":1,
    "name":"Ahmad Rifqi",
    "email":"customer1@example.com",
    "created_at":"2026-05-01 10:00:00"
  }
]
```

### `POST /customers`

Creates a customer.

Request body:

```json
{
  "name":"Alice",
  "email":"alice@example.com"
}
```

Success `201`:

```json
{
  "customer_id":3,
  "name":"Alice",
  "email":"alice@example.com"
}
```

Notes:

- `customer_id` is generated in application code as `MAX(customer_id) + 1`
- `created_at` is not returned from the create response

### `PUT /customers/{customer_id}`

Partially updates a customer.

Request body example:

```json
{
  "name":"Updated",
  "email":"updated@example.com"
}
```

Success `200`:

```json
{
  "customer_id":1,
  "name":"Updated",
  "email":"updated@example.com"
}
```

Error cases:

- Empty JSON object -> `400 {"detail":"No fields to update"}`
- Unknown `customer_id` -> `404 {"detail":"Customer not found"}`

Notes:

- Partial updates are supported
- Sending the same values still returns `200`

### `DELETE /customers/{customer_id}`

Deletes a customer and manually deletes dependent rows first.

Success `200`:

```json
{"deleted":true,"customer_id":1}
```

Delete order of dependent cleanup:

- `complaints` by `customer_id`
- `orders` by `customer_id`
- `customer_memory` by `customer_id`
- `session_messages` joined through `sessions`
- `sessions` by `customer_id`
- `customers`

Not found `404`:

```json
{"detail":"Customer not found"}
```

### `GET /orders`

Returns raw order rows.

Query params:

- `customer_id` optional integer filter

Success `200`:

```json
[
  {
    "order_id":12345,
    "customer_id":1,
    "product_name":"Wireless Headphones",
    "status":"pending",
    "order_date":"2026-04-01 10:00:00",
    "delivery_date":null
  }
]
```

### `POST /orders`

Creates an order.

Request body:

```json
{
  "customer_id":1,
  "product_name":"Desk Lamp",
  "status":"pending"
}
```

Success `201`:

```json
{
  "order_id":103,
  "customer_id":1,
  "product_name":"Desk Lamp",
  "status":"pending"
}
```

Notes:

- `order_id` is generated in application code as `MAX(order_id) + 1`
- `order_date` and `delivery_date` are not returned from the create response

### `PUT /orders/{order_id}`

Partially updates an order.

Request body example:

```json
{
  "product_name":"Desk Lamp Pro",
  "status":"processing"
}
```

Success `200`:

```json
{
  "order_id":101,
  "customer_id":1,
  "product_name":"Desk Lamp Pro",
  "status":"processing"
}
```

Error cases:

- Empty JSON object -> `400 {"detail":"No fields to update"}`
- Unknown `order_id` -> `404 {"detail":"Order not found"}`

Notes:

- Partial updates are supported
- Sending the same values still returns `200`

### `DELETE /orders/{order_id}`

Deletes an order after deleting dependent complaints for that order.

Success `200`:

```json
{"deleted":true,"order_id":101}
```

Not found `404`:

```json
{"detail":"Order not found"}
```

### `GET /complaints`

Returns raw complaint rows.

Query params:

- `customer_id` optional integer filter

Success `200`:

```json
[
  {
    "complaint_id":1,
    "customer_id":1,
    "order_id":5678,
    "issue":"Package arrived two days later than promised",
    "status":"resolved",
    "created_at":"2026-05-01 10:00:00"
  }
]
```

### `POST /complaints`

Creates a complaint.

Request body:

```json
{
  "customer_id":1,
  "order_id":101,
  "issue":"Damaged box",
  "status":"open"
}
```

Success `201`:

```json
{
  "complaint_id":12,
  "customer_id":1,
  "order_id":101,
  "issue":"Damaged box",
  "status":"open"
}
```

Notes:

- `complaint_id` comes from database auto-increment
- `created_at` is not returned from the create response

### `PUT /complaints/{complaint_id}`

Partially updates a complaint.

Request body example:

```json
{
  "issue":"Updated issue",
  "status":"resolved"
}
```

Success `200`:

```json
{
  "complaint_id":1,
  "customer_id":1,
  "order_id":101,
  "issue":"Updated issue",
  "status":"resolved"
}
```

Error cases:

- Empty JSON object -> `400 {"detail":"No fields to update"}`
- Unknown `complaint_id` -> `404 {"detail":"Complaint not found"}`

Notes:

- Partial updates are supported
- Sending the same values still returns `200`

### `DELETE /complaints/{complaint_id}`

Deletes a complaint.

Success `200`:

```json
{"deleted":true,"complaint_id":1}
```

Not found `404`:

```json
{"detail":"Complaint not found"}
```

## 4) Frontend Integration Rules

1. Treat the first seen `thread_id` as the canonical conversation identifier and reuse it on later `/chat/stream` calls.
2. Parse SSE by `event` name, not by positional assumptions.
3. Build live assistant text from `response_token`, then reconcile with `response_end.response`.
4. Handle multiple `tool_result` events per tool phase.
5. Treat `tool_result.results` as normalized JSON-like data, but still defensively code for `{"raw":"..."}` fallback.
6. Handle `400` on empty update payloads for `PUT /customers/{id}`, `PUT /orders/{id}`, and `PUT /complaints/{id}`.
7. Handle `404` for deleted or missing session, memory, customer, order, and complaint resources.
8. Do not rely on request-side `model` selection yet; the backend ignores it in current implementation.
9. When calling `POST /chat/stream`, send `agent_type` to control which agent handles the request. Always send `customer_id` for `"customer_service"` requests; never send it for workspace agents (`"refund_email"`, `"calendar"`). Invalid combinations return `422`.
10. `GET /sessions/{session_id}` now returns `{"session": {...}, "messages": [...]}` — read messages from `.messages`, not the root array.

## 5) Current Gaps / Non-Goals

- No auth or authorization. `customer_id` is client-supplied and trusted.
- No API versioning.
- No pagination.
- No dedicated `GET /customers/{id}`, `GET /orders/{id}`, or `GET /complaints/{id}` routes.
- List endpoints return raw table rows without wrapper objects.
- List endpoints do not declare explicit ordering in SQL.
- Write routes do not perform application-level referential validation before insert or update; database constraints remain the enforcement layer.
