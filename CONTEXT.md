# AI Workspace Agent Suite

This context covers a multi-agent application with three agent types: a customer service agent, a refund email agent, and a calendar agent — all sharing one React frontend and FastAPI backend.

## Language

**Agent Type**:
One of three distinct agent capabilities the user can select: **Customer Service Agent**, **Refund Email Agent**, or **Calendar Agent**. Each has its own LangGraph graph, tool set, and system prompt.
_Avoid_: Mode, agent mode, persona

**Customer Service Agent**:
The original agent that answers questions about orders, complaints, refunds, and stored customer preferences. Operates in the context of exactly one **Customer**. Uses MySQL-backed tools.
_Avoid_: Support agent, default agent

**Refund Email Agent**:
A conversational agent that reads, classifies, and replies to customer refund/return emails in a Gmail inbox via MCP tools. Can process emails one at a time or in batch ("process all refund emails"). A **Workspace Agent**.
_Avoid_: Email bot, auto-responder

**Calendar Agent**:
A conversational agent that queries, creates, and manages Google Calendar events via MCP tools and workspace-cli. A **Workspace Agent**.
_Avoid_: Scheduler, booking agent

**Workspace Agent**:
Collective term for agents that connect to Google Workspace (currently **Refund Email Agent** and **Calendar Agent**). They have no **Customer** scoping, require Google OAuth, and use MCP tools.
_Avoid_: Google agent, external agent

**Customer**:
A person whose orders, complaints, and memory entries the **Customer Service Agent** may access. Not applicable to **Workspace Agents**.
_Avoid_: Client, buyer, account

**Conversation Session**:
A single user-agent conversation. For the **Customer Service Agent**, scoped to exactly one **Customer**. For **Workspace Agents**, scoped to the authenticated Google account.
_Avoid_: Thread, chat, conversation ID

**App Sidebar**:
The collapsible left-edge navigation (shadcn Sidebar) that holds **Agent Type** selection, session history grouped by agent type, and page links (Data Explorer, Memory Manager).
_Avoid_: Left panel, navigation bar

**Chat Header**:
The horizontal bar above the conversation area. Shows Customer, Provider, and Model selectors for the **Customer Service Agent**. Shows only Provider and Model selectors for **Workspace Agents**.
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

**MCP (Model Context Protocol)**:
The open-standard JSON-RPC protocol used by **Workspace Agents** to access Gmail and Calendar APIs through the `workspace-mcp` server subprocess.
_Avoid_: API layer, tool protocol

**workspace-cli**:
A command-line tool (from the `google_workspace_mcp` repo) used by the **Calendar Agent** for fast, read-only calendar queries via subprocess calls. Write operations go through MCP instead.
_Avoid_: CLI tools, bash tools

## Relationships

- The **App Sidebar** lists three **Agent Types**; selecting one starts a fresh **Conversation Session**
- A **Conversation Session** belongs to exactly one **Agent Type**
- A **Customer Service Agent** session additionally belongs to exactly one **Customer**
- **Workspace Agent** sessions have no **Customer** — they operate on the authenticated Google account
- A **Customer** may have many **Conversation Sessions** (Customer Service only)
- Session history in the **App Sidebar** is grouped by **Agent Type** (ChatGPT project-style)
- The **Chat Header** adapts to the active **Agent Type**: Customer selector visible only for **Customer Service Agent**
- The **Agent Process Panel** sits beside the chat and shows one turn within a **Conversation Session**, not the whole session history
- The **Data Explorer** and **Memory Manager** pages are relevant only to the **Customer Service Agent**
- Both **Workspace Agents** share a single `workspace-mcp` subprocess started at app boot
- The **Calendar Agent** uses both MCP tools (for create/update/delete) and **workspace-cli** (for fast reads)

## Example dialogue

> **Dev:** "If the user switches from Customer Service to Calendar Agent, does the conversation continue?"
> **Domain expert:** "No. Switching Agent Type always starts a fresh Conversation Session. The previous session is saved in history."

> **Dev:** "Does the Refund Email Agent need a Customer selected?"
> **Domain expert:** "No. Workspace Agents have no Customer scoping. The Customer selector is hidden."

> **Dev:** "Can the Refund Email Agent process all emails automatically?"
> **Domain expert:** "Yes. The user types 'process all refund emails' and the agent runs the full batch workflow within the conversation. But it's still conversational — the user can also ask about specific emails."

> **Dev:** "Does the Agent Process Panel show the whole conversation?"
> **Domain expert:** "No. The transcript is session history. The Agent Process Panel is only the current turn."

## Flagged ambiguities

- "thread" was being used to mean **Conversation Session**. Resolved: the canonical concept is **Conversation Session**; any thread ID is only the transport identifier for that session.
- "right panel" was being used to mean both the shell region and the specific process view. Resolved: the tabbed Right Panel has been retired. **Agent Process Panel** is now a standalone pane beside the chat. **Data Explorer** and **Memory Manager** are separate pages accessed via the **App Sidebar**.
- "agent" was ambiguous between the overall app and a specific agent type. Resolved: use **Agent Type** for the selectable capability, and the specific names (**Customer Service Agent**, **Refund Email Agent**, **Calendar Agent**) when referring to a particular one.
- "customer" in the context of workspace agents was unclear. Resolved: **Customer** is a domain concept for the **Customer Service Agent** only. Email senders processed by the **Refund Email Agent** are not Customers in this system — they are external Gmail correspondents.
