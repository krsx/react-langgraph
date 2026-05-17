Based on the current implementation I wanted to refactor the current frontend application implementation. Use "OpenWebUI" and ChatGPT as the layout reference.

I think I wanted to introduce a sidebar like in OpenWebUI or ChatGPT where user could select the past session and create new chat, while also showing available menu of the app. We could use 'shadcn sidebar' in here. This way we dont need to have the left layout and move it into the sidebar. Since sidebar can be closed and open, this way the main layout can have much space.

I think I also wanted to add the ability of CRUD for the Customer, Orders, and Complaints. Currently only Memory Manager can only this. Therefore thinkwe could add this into a dedicated menu in the sidebar.

Then as for right panel that shows the Agent Proces, Data Explorer, and Memory Manager, I think we need to make it more professional, less slop, and functional based on its existing feature intention. This way we need to brainstorm and research further.

We will use this comamnd to install the approprite style of this application: `npx shadcn@latest apply --preset b38TwQdb6`. We will strictly use this as our theme.

Keep it simple, align, miniamlistic, yet functional according to the backend implementation. Use Notion, ChatGPT, OpenWebUI as design inspiration and blend it with our design system.

## Resolved Design Decisions

See the grill-with-docs session for full rationale. Issues created:

| # | Issue | Blocked by |
|---|---|---|
| #17 | Apply shadcn preset and install foundational dependencies | None |
| #18 | Backend: enrich SSE payloads for tool_result and memory_updated | None |
| #19 | Backend: CRUD endpoints for customers, orders, complaints | None |
| #20 | Chat page: sidebar session history, Chat Header, and conversation | #17 |
| #21 | Chat page: Agent Process Panel as ResizablePanel | #20 |
| #22 | Data Explorer page with tabbed CRUD | #17, #19 |
| #23 | Memory Manager page | #17 |
| #24 | Cleanup: remove old layout, components, and reducer | #20, #21, #22, #23 |
