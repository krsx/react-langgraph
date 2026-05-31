# Test Cases: AI Workspace Agent Suite

Two independent sets of 11 test cases — one per agent — covering all functional areas
from `docs/project-spec-extend.md`. Run each set with a live Google Workspace account
and valid OAuth credentials.

---

## Set A — Refund Email Agent (`refund_agent.py`)

*Source: `project-spec-extend.md §2.1, §5.1, §6`. Seed data mirrors Gmail inbox messages below.*

| # | Function | Test Query / Trigger | Expected Behavior |
|---|---|---|---|
| 1 | Gmail Search Tool | Auto mode launch (`run_auto_refund_processing`) | `search_gmail_messages` called with `query="refund OR return is:unread"`; returns list of matching message IDs |
| 2 | Batch Email Fetch | 3+ unread refund emails in inbox | Agent uses `get_gmail_messages_content_batch` (not individual calls); all messages fetched in ≤ 1 MCP round-trip |
| 3 | Intent Classification — REFUND_REQUEST | Email subject: "I need a refund for my order" | Agent classifies as `REFUND_REQUEST`; composes approval reply with 3–5 day processing info |
| 4 | Intent Classification — RETURN_REQUEST | Email body: "I'd like to return the item I received" | Agent classifies as `RETURN_REQUEST`; composes return instructions with prepaid label steps |
| 5 | Intent Classification — COMPLAINT | Email body: "This is completely unacceptable service" | Agent classifies as `COMPLAINT`; sends empathetic acknowledgement with 24hr follow-up promise |
| 6 | Intent Classification — OTHER | Email subject: "Special offer just for you!" | Agent classifies as `OTHER`; no `send_gmail_message` or `create_gmail_draft` call is made |
| 7 | Threaded Reply | Any classified email with `thread_id` | `send_gmail_message` called with the original `thread_id`; reply appears in same thread, not a new conversation |
| 8 | Draft on Uncertainty | Email with ambiguous intent (e.g. mixed refund + complaint) | Agent calls `create_gmail_draft` instead of `send_gmail_message`; draft saved for human review |
| 9 | Multi-step ReAct Loop | Inbox contains 3 actionable emails | Agent completes search → read → classify → reply cycle for all 3 emails before producing final summary; `should_continue` routes back to `agent_node` between each email |
| 10 | Summary Report | Auto mode completes full workflow | Final `AIMessage` contains structured summary: email count, per-email classification and action taken, skipped count |
| 11 | Thread Read | "Show me the full thread for the last email I replied to" (interactive mode) | Agent calls `get_gmail_thread` with correct `thread_id`; returns full conversation history in human-readable form |

---

## Set B — Calendar Agent (`calendar_agent.py`)

*Source: `project-spec-extend.md §2.2, §5.2, §5.3, §6`. Seed events seeded in primary Google Calendar.*

| # | Function | Test Query | Expected Behavior |
|---|---|---|---|
| 1 | CLI Today Events | What's on my calendar today? | Agent calls `cli_today_events`; tool executes `workspace-cli call list_calendar_events` with today's UTC ISO range; returns events without an MCP roundtrip |
| 2 | CLI List Events | Show me my events for the next 7 days | Agent calls `cli_list_events` with `time_min=now`, `time_max=+7d`; events returned in chronological order via `singleEvents=true` |
| 3 | CLI List Calendars | What calendars do I have? | Agent calls `cli_list_calendars`; returns all calendar names, IDs, access roles, and colors |
| 4 | CLI Get Event | Get the details for the Team Standup event | Agent calls `cli_get_event` with the event ID from a prior list call; returns full event metadata including attendees and location |
| 5 | MCP Create Event | Schedule a team lunch next Friday at noon for 1 hour | Agent calls MCP `create_calendar_event` (not CLI); event created with correct `summary`, `start`, `end`; confirmation shown to user |
| 6 | MCP Update Event | Change the team lunch to 1:30 PM | Agent calls MCP `update_calendar_event` with correct `eventId` and updated start/end; prompts user to confirm before executing |
| 7 | MCP Delete Event — Confirmation Guard | Delete the Client Review meeting | Agent asks for explicit confirmation before calling MCP `delete_calendar_event`; cancels if user says no |
| 8 | MCP Suggest Meeting Time | Find a free 30-minute slot for a call with john@example.com this week | Agent calls MCP `suggest_meeting_time` with correct `attendees` and `duration`; returns 2–3 available time slots |
| 9 | MCP RSVP | Accept the invitation for the Friday all-hands | Agent calls MCP `respond_to_calendar_event` with `response="accepted"` and correct `eventId`; confirms RSVP sent |
| 10 | Dual Tool Strategy | "What's on today?" then "Create a 2 PM meeting tomorrow" | First query → `cli_today_events` (CLI path); second query → `create_calendar_event` (MCP path); agent selects correct surface for each task type |
| 11 | Demo Mode | Type `demo` in interactive prompt | `run_demo()` executes all 3 pre-written queries (`list calendars`, `today's events`, `next 7 days`) sequentially; all three produce valid non-empty responses |

---

## Seed Data Coverage Summary

### Email Seed (Gmail Inbox — Refund Agent)

| Message ID (mock) | Sender | Subject | Classification | Covers Test(s) |
|---|---|---|---|---|
| msg_refund_001 | alice@customer.com | "I need a refund for my order" | REFUND_REQUEST | A3, A7 |
| msg_return_001 | bob@customer.com | "Return request for recent purchase" | RETURN_REQUEST | A4, A7 |
| msg_complaint_001 | carol@customer.com | "Terrible experience — still waiting" | COMPLAINT | A5, A7 |
| msg_promo_001 | promo@newsletter.com | "Exclusive deal just for you!" | OTHER | A6 |
| msg_ambiguous_001 | dave@customer.com | "Refund? Or maybe store credit?" | AMBIGUOUS | A8 |
| msg_thread_001 | eve@customer.com | "Follow-up on my last refund request" | REFUND_REQUEST | A9, A11 |

### Calendar Seed (Google Calendar — Calendar Agent)

| Event Name | Calendar | Date/Time | Status | Covers Test(s) |
|---|---|---|---|---|
| Team Standup | primary | Today 9:00–9:30 AM | confirmed | B1, B4 |
| Client Review | primary | Today 2:00–3:00 PM | confirmed | B1, B7 |
| 1:1 with Manager | primary | Today 5:30–6:00 PM | confirmed | B1 |
| Sprint Planning | primary | Tomorrow 10:00–11:00 AM | confirmed | B2 |
| Friday All-Hands | primary | This Friday 3:00–4:00 PM | needs RSVP | B9 |
| Team Lunch *(created in test)* | primary | Next Friday 12:00–1:00 PM | — | B5, B6 |

Tests B8, B10, B11 require no pre-seeded event — they use live free/busy data and the demo mode workflow.

---

## Shared Behaviour Tests

These apply to both agents and verify the core ReAct infrastructure.

| # | Function | Trigger | Expected Behavior |
|---|---|---|---|
| S1 | Env Var Validation | Run agent with `OPENAI_API_KEY` unset | `_print_setup_guide()` called; process exits with readable setup instructions, no traceback |
| S2 | MCP stdio Transport | Normal startup | `MultiServerMCPClient` spawns `workspace-mcp` subprocess; `transport: stdio` confirmed (no HTTP port opened) |
| S3 | Tool Filter | `build_agent()` called | Only the agent's designated tool subset is bound to the LLM (Gmail-only for Refund Agent; Calendar + CLI for Calendar Agent) |
| S4 | ReAct Loop Termination | Any multi-tool query | `should_continue` returns `END` only after GPT-4o emits an `AIMessage` with empty `tool_calls`; never terminates mid-sequence |
| S5 | CLI Timeout Guard | `_run_cli` called with a hanging subprocess | `subprocess.run` raises `TimeoutExpired` at 15 s; tool returns error string; agent recovers and reports failure to user |
