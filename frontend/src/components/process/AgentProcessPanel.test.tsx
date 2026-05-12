import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AgentProcessPanel } from "./AgentProcessPanel";
import type { ChatStreamEvent } from "../../lib/types";

function renderPanel(events: ChatStreamEvent[]) {
  return render(
    <AgentProcessPanel
      isOpen
      activeCustomerName="Ahmad Rifqi"
      selectedProvider="openrouter"
      selectedModel="openai/gpt-4o"
      threadId="thread-1"
      events={events}
      onToggle={() => {}}
    />,
  );
}

describe("AgentProcessPanel", () => {
  it("renders sequential planner, tool, and verifier cards from normalized events", () => {
    renderPanel([
      {
        type: "planner_result",
        thread_id: "thread-1",
        content: "Inspect the order and verify the status.",
        tool_calls: [{ name: "order_lookup", args: { order_id: 12345 } }],
      },
      { type: "tool_start", thread_id: "thread-1" },
      { type: "tool_result", thread_id: "thread-1", results: "{'status': 'pending'}" },
      {
        type: "verifier_result",
        thread_id: "thread-1",
        valid: true,
        checks: ["Used order data", "Stayed within customer scope"],
        override_message: null,
      },
      {
        type: "planner_result",
        thread_id: "thread-1",
        content: "Double-check the customer profile before finalizing.",
        tool_calls: [{ name: "customer_profile", args: { customer_id: 1 } }],
      },
      { type: "tool_start", thread_id: "thread-1" },
      { type: "tool_result", thread_id: "thread-1", results: "{'vip': true}" },
      {
        type: "verifier_result",
        thread_id: "thread-1",
        valid: false,
        checks: ["Need refund policy verification"],
        override_message: "Ask a follow-up question before promising a refund.",
      },
    ]);

    const headings = screen
      .getAllByRole("heading", { level: 3 })
      .map((heading) => heading.textContent);

    expect(headings).toEqual([
      "Current Turn",
      "Planner",
      "Tool Result",
      "Verifier",
      "Planner",
      "Tool Result",
      "Verifier",
    ]);

    expect(screen.getAllByText("order_lookup")).toHaveLength(2);
    expect(screen.getAllByText("customer_profile")).toHaveLength(2);
    expect(screen.getByText("{'status': 'pending'}")).toBeInTheDocument();
    expect(screen.getByText(/Verifier passed: Used order data/)).toBeInTheDocument();
    expect(screen.getByText(/Verifier failed: Need refund policy verification/)).toBeInTheDocument();
    expect(screen.getByText(/Ask a follow-up question before promising a refund/)).toBeInTheDocument();
  });

  it("shows raw detail only when a card is expanded", async () => {
    renderPanel([
      {
        type: "planner_result",
        thread_id: "thread-1",
        content: "Inspect the order and verify the status.",
        tool_calls: [{ name: "order_lookup", args: { order_id: 12345 } }],
      },
    ]);

    expect(screen.queryByText((content) => content.includes('"tool_calls": ['))).not.toBeInTheDocument();

    const plannerCard = screen.getByRole("heading", { name: "Planner" }).closest("article");
    if (!plannerCard) {
      throw new Error("expected planner card");
    }

    await userEvent.click(within(plannerCard).getByRole("button", { name: "Show detail" }));

    expect(plannerCard).toHaveTextContent('"tool_calls": [');
    expect(plannerCard).toHaveTextContent('"order_id": 12345');
  });
});
