# Intelligent Customer Service Agent

This context covers an evaluator-facing customer service agent that answers questions about orders, complaints, refunds, and stored customer preferences.

## Language

**Customer**:
A person whose orders, complaints, and memory entries the agent may access.
_Avoid_: Client, buyer, account

**Conversation Session**:
A single evaluator-agent conversation conducted in the context of exactly one **Customer**.
_Avoid_: Thread, chat, conversation ID

**Right Panel**:
The shell region that hosts evaluator-facing inspection and control panels beside the chat.
_Avoid_: Sidebar, drawer, process panel

**Agent Process Panel**:
The current-turn trace that shows how the agent reasoned, selected tools, and verified the reply.
_Avoid_: Debug log, backend trace

**Data Explorer**:
A read-only panel for inspecting customer-service tables to verify agent side effects.
_Avoid_: Admin console, database viewer

**Memory Manager**:
A panel for viewing and editing long-term customer memory entries.
_Avoid_: Settings, profile editor

## Relationships

- A **Conversation Session** belongs to exactly one **Customer**
- A **Customer** may have many **Conversation Sessions**
- The **Right Panel** may host the **Agent Process Panel**, **Data Explorer**, and **Memory Manager**
- The **Agent Process Panel** shows one turn within a **Conversation Session**, not the whole session history
- The **Memory Manager** edits memory entries for exactly one active **Customer**

## Example dialogue

> **Dev:** "If the evaluator switches to another Customer, can the same Conversation Session continue?"
> **Domain expert:** "No. A Conversation Session stays bound to one Customer. Switching customers starts a new session."

> **Dev:** "Does the Agent Process Panel show the whole conversation?"
> **Domain expert:** "No. The transcript is session history. The Agent Process Panel is only the current turn."

## Flagged ambiguities

- "thread" was being used to mean **Conversation Session**. Resolved: the canonical concept is **Conversation Session**; any thread ID is only the transport identifier for that session.
- "right panel" was being used to mean both the shell region and the specific process view. Resolved: **Right Panel** is the region; **Agent Process Panel**, **Data Explorer**, and **Memory Manager** are separate hosted panels.
