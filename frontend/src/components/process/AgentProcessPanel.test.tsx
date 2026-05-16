import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AgentProcessPanel } from "./AgentProcessPanel";
import type { ChatStreamEvent } from "../../lib/types";

function renderPanel(
  events: ChatStreamEvent[],
  opts?: { isHistoryMode?: boolean; isStreaming?: boolean },
) {
  return render(
    <AgentProcessPanel
      events={events}
      isHistoryMode={opts?.isHistoryMode ?? false}
      isStreaming={opts?.isStreaming ?? false}
    />,
  );
}

describe("AgentProcessPanel", () => {
  // Tracer bullet: history mode empty state
  it("shows empty state message when in history mode", () => {
    renderPanel([], { isHistoryMode: true });
    expect(
      screen.getByText(/process trace is only available during live conversation/i),
    ).toBeInTheDocument();
  });

  // Layer 1: all step summaries visible by default
  it("renders Layer 1 summaries for all event types", () => {
    renderPanel([
      {
        type: "memory_loaded",
        thread_id: "t1",
        memory_context: [{ type: "memory", key: "k", value: "v" }],
      },
      {
        type: "planner_result",
        thread_id: "t1",
        content: "I will look up the order.",
        tool_calls: [{ name: "order_lookup", args: { order_id: 12345 } }],
      },
      { type: "tool_start", thread_id: "t1" },
      {
        type: "tool_result",
        thread_id: "t1",
        tool_name: "order_lookup",
        results: { status: "pending" },
      },
      {
        type: "verifier_result",
        thread_id: "t1",
        valid: true,
        checks: ["Used order data", "Stayed in scope"],
        override_message: null,
      },
      {
        type: "memory_updated",
        thread_id: "t1",
        key: "last_order",
        value: "order_12345",
      },
    ]);

    expect(screen.getByText(/1 memory item loaded/i)).toBeInTheDocument();
    expect(screen.getByText(/agent decided to call order_lookup/i)).toBeInTheDocument();
    expect(screen.getByText(/tool order_lookup completed/i)).toBeInTheDocument();
    expect(screen.getByText(/verifier passed/i)).toBeInTheDocument();
    expect(screen.getByText(/stored last_order/i)).toBeInTheDocument();
  });

  // Layer 2: memory loaded step shows key-value pairs
  it("expands memory loaded step to show key-value pairs in Layer 2", async () => {
    renderPanel([
      {
        type: "memory_loaded",
        thread_id: "t1",
        memory_context: [
          { type: "memory", key: "preferred_channel", value: "email" },
          { type: "memory", key: "vip_status", value: "true" },
        ],
      },
    ]);

    await userEvent.click(screen.getByRole("button", { name: /2 memory items loaded/i }));

    expect(screen.getByText("preferred_channel")).toBeInTheDocument();
    expect(screen.getByText("email")).toBeInTheDocument();
    expect(screen.getByText("vip_status")).toBeInTheDocument();
    expect(screen.getByText("true")).toBeInTheDocument();
  });

  // Layer 2: planner shows reasoning text + tool call cards
  it("expands planner step to show reasoning and tool call cards in Layer 2", async () => {
    renderPanel([
      {
        type: "planner_result",
        thread_id: "t1",
        content: "I will look up the order to check its status.",
        tool_calls: [{ name: "order_lookup", args: { order_id: 99 } }],
      },
    ]);

    await userEvent.click(
      screen.getByRole("button", { name: /agent decided to call order_lookup/i }),
    );

    expect(
      screen.getByText("I will look up the order to check its status."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("order_lookup").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/order_id/i)).toBeInTheDocument();
  });

  // Layer 2: tool result shows structured data
  it("expands tool result step to show structured data in Layer 2", async () => {
    renderPanel([
      {
        type: "tool_result",
        thread_id: "t1",
        tool_name: "order_lookup",
        results: { order_id: 99, status: "pending", product_name: "Widget" },
      },
    ]);

    await userEvent.click(
      screen.getByRole("button", { name: /tool order_lookup completed/i }),
    );

    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("product_name")).toBeInTheDocument();
  });

  // Layer 2: verifier shows pass/fail checklist
  it("expands verifier step to show pass/fail checklist in Layer 2", async () => {
    renderPanel([
      {
        type: "verifier_result",
        thread_id: "t1",
        valid: false,
        checks: ["Used order data", "Need refund policy"],
        override_message: "Ask follow-up first.",
      },
    ]);

    await userEvent.click(screen.getByRole("button", { name: /verifier failed/i }));

    expect(screen.getByText("Used order data")).toBeInTheDocument();
    expect(screen.getByText("Need refund policy")).toBeInTheDocument();
    expect(screen.getByText("Ask follow-up first.")).toBeInTheDocument();
  });

  // Layer 2: memory updated shows key/value written
  it("expands memory updated step to show key/value in Layer 2", async () => {
    renderPanel([
      {
        type: "memory_updated",
        thread_id: "t1",
        key: "last_interaction_summary",
        value: "User asked to verify order 12345.",
      },
    ]);

    await userEvent.click(
      screen.getByRole("button", { name: /stored last_interaction_summary/i }),
    );

    expect(screen.getByText("last_interaction_summary")).toBeInTheDocument();
    expect(screen.getByText("User asked to verify order 12345.")).toBeInTheDocument();
  });

  // Layer 3: payload toggle reveals raw JSON
  it('reveals raw JSON in a code block via "View payload" button', async () => {
    renderPanel([
      {
        type: "verifier_result",
        thread_id: "t1",
        valid: true,
        checks: ["Used order data"],
        override_message: null,
      },
    ]);

    // Layer 2 closed: raw JSON not present
    expect(screen.queryByText(/"valid"/)).not.toBeInTheDocument();

    // Expand Layer 2
    await userEvent.click(screen.getByRole("button", { name: /verifier passed/i }));

    // Payload toggle now visible
    await userEvent.click(screen.getByRole("button", { name: /view payload/i }));

    // Raw JSON visible in code block
    expect(screen.getByText((text) => text.includes('"valid"'))).toBeInTheDocument();
  });

  // Active streaming step shows Running badge
  it("shows Running badge on the last step during streaming and no data-active attribute", () => {
    renderPanel(
      [
        {
          type: "memory_loaded",
          thread_id: "t1",
          memory_context: [],
        },
        {
          type: "planner_result",
          thread_id: "t1",
          content: "Thinking...",
          tool_calls: [],
        },
      ],
      { isStreaming: true },
    );

    // Running badge text indicates active streaming step
    expect(screen.getByText(/running/i)).toBeInTheDocument();
    // No data-active attribute is set on any step (yellow ring removed)
    const steps = screen.getAllByRole("listitem");
    for (const step of steps) {
      expect(step).not.toHaveAttribute("data-active");
    }
  });

  // planner_start shows running placeholder, upgraded by planner_result
  it("shows a running planner placeholder for planner_start, upgraded by planner_result", () => {
    const { rerender } = renderPanel([{ type: "planner_start", thread_id: "t1" }]);
    expect(screen.getByText(/agent is reasoning/i)).toBeInTheDocument();

    rerender(
      <AgentProcessPanel
        events={[
          { type: "planner_start", thread_id: "t1" },
          {
            type: "planner_result",
            thread_id: "t1",
            content: "I will look up the order.",
            tool_calls: [{ name: "order_lookup", args: {} }],
          },
        ]}
        isHistoryMode={false}
        isStreaming={false}
      />,
    );

    expect(screen.queryByText(/agent is reasoning/i)).not.toBeInTheDocument();
    expect(screen.getByText(/agent decided to call order_lookup/i)).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  // layer3Open resets when Layer 2 is toggled closed
  it("hides raw JSON again when Layer 2 is closed and re-opened", async () => {
    renderPanel([
      {
        type: "verifier_result",
        thread_id: "t1",
        valid: true,
        checks: ["Used order data"],
        override_message: null,
      },
    ]);

    // Open Layer 2, then Layer 3
    await userEvent.click(screen.getByRole("button", { name: /verifier passed/i }));
    await userEvent.click(screen.getByRole("button", { name: /view payload/i }));
    expect(screen.getByText((t) => t.includes('"valid"'))).toBeInTheDocument();

    // Close Layer 2
    await userEvent.click(screen.getByRole("button", { name: /verifier passed/i }));
    // Re-open Layer 2 — raw JSON should NOT be visible
    await userEvent.click(screen.getByRole("button", { name: /verifier passed/i }));
    expect(screen.queryByText(/"valid"/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /view payload/i })).toBeInTheDocument();
  });

  // No empty state when in live mode with events
  it("does not show history empty state when in live mode", () => {
    renderPanel(
      [{ type: "memory_loaded", thread_id: "t1", memory_context: [] }],
      { isHistoryMode: false },
    );
    expect(
      screen.queryByText(/process trace is only available during live conversation/i),
    ).not.toBeInTheDocument();
  });
});
