# Intelligent Customer Service Agent

This context covers an evaluator-facing customer service agent that answers questions about orders, complaints, refunds, and stored customer preferences.

## Language

**Customer**:
A person whose orders, complaints, and memory entries the agent may access.
_Avoid_: Client, buyer, account

**Conversation Session**:
A single evaluator-agent conversation conducted in the context of exactly one **Customer**.
_Avoid_: Thread, chat, conversation ID

**App Sidebar**:
The collapsible left-edge navigation (shadcn Sidebar) that holds session history, new-chat action, and page links (Chat, Data Explorer, Memory Manager).
_Avoid_: Left panel, navigation bar

**Chat Header**:
The horizontal bar above the conversation area containing the Customer, Provider, and Model selectors.
_Avoid_: Toolbar, config bar

**Agent Process Panel**:
The collapsible right-edge pane beside the chat that shows the current-turn trace: how the agent reasoned, selected tools, and verified the reply.
_Avoid_: Right panel, debug log, backend trace

**Data Explorer**:
A dedicated page (accessed via App Sidebar) with tabbed CRUD views for Customers, Orders, and Complaints.
_Avoid_: Database, admin console, database viewer

**Memory Manager**:
A dedicated page (accessed via App Sidebar) for viewing and editing long-term customer memory entries.
_Avoid_: Settings, profile editor

## Relationships

- A **Conversation Session** belongs to exactly one **Customer**
- A **Customer** may have many **Conversation Sessions**
- The **App Sidebar** provides navigation to Chat, **Data Explorer**, and **Memory Manager** pages
- The **Chat Header** displays the active **Customer**, Provider, and Model selectors above the conversation
- The **Agent Process Panel** sits beside the chat and shows one turn within a **Conversation Session**, not the whole session history
- The **Data Explorer** page has three tabs: Customers, Orders, Complaints — each with full CRUD
- The **Memory Manager** page edits memory entries for exactly one selected **Customer**

## Example dialogue

> **Dev:** "If the evaluator switches to another Customer, can the same Conversation Session continue?"
> **Domain expert:** "No. A Conversation Session stays bound to one Customer. Switching customers starts a new session."

> **Dev:** "Does the Agent Process Panel show the whole conversation?"
> **Domain expert:** "No. The transcript is session history. The Agent Process Panel is only the current turn."

## Flagged ambiguities

- "thread" was being used to mean **Conversation Session**. Resolved: the canonical concept is **Conversation Session**; any thread ID is only the transport identifier for that session.
- "right panel" was being used to mean both the shell region and the specific process view. Resolved: the tabbed Right Panel has been retired. **Agent Process Panel** is now a standalone pane beside the chat. **Data Explorer** and **Memory Manager** are separate pages accessed via the **App Sidebar**.
