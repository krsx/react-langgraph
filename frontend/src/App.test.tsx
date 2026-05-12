import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { createMockFetch } from "./test-utils/mockApi";

describe("App shell", () => {
  it("loads bootstrap data, filters Session History by Customer, and disables unavailable providers", async () => {
    const { fetchMock } = createMockFetch({
      customers: [
        { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
        { customer_id: 2, name: "Bea Foo", email: "bea@example.com", created_at: "2026-05-01" },
      ],
      providers: {
        openrouter: { available: true, models: ["openai/gpt-4o"] },
        ollama: { available: false, models: [] },
      },
      sessions: [
        { thread_id: "thread-1", customer_id: 1, created_at: "2026-05-01", first_message: "Order status?" },
        { thread_id: "thread-2", customer_id: 2, created_at: "2026-05-02", first_message: "Need refund" },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Conversation Sessions")).toBeInTheDocument();
    expect(screen.getByText("Order status?")).toBeInTheDocument();
    expect(screen.queryByText("Need refund")).not.toBeInTheDocument();

    const customerSelect = screen.getByLabelText("Customer");
    await userEvent.selectOptions(customerSelect, "2");

    expect(await screen.findByText("Need refund")).toBeInTheDocument();
    expect(screen.queryByText("Order status?")).not.toBeInTheDocument();

    const providerSelect = screen.getByLabelText("Provider");
    const ollamaOption = screen.getByRole("option", { name: /ollama/i });
    expect(ollamaOption).toBeDisabled();
    expect(providerSelect).toHaveValue("openrouter");
  });

  it("loads read-only history, disables the composer, and restores writable mode on New Chat", async () => {
    const { fetchMock } = createMockFetch({
      customers: [
        { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
      ],
      providers: {
        openrouter: { available: true, models: ["openai/gpt-4o"] },
      },
      sessions: [
        { thread_id: "thread-1", customer_id: 1, created_at: "2026-05-01", first_message: "Order status?" },
      ],
      sessionMessages: {
        "thread-1": [
          { message_id: 1, role: "human", content: "Order status?", created_at: "2026-05-01" },
          { message_id: 2, role: "ai", content: "It ships tomorrow.", created_at: "2026-05-01" },
        ],
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await userEvent.click(await screen.findByText("Order status?"));

    expect(await screen.findByText("Read-only history")).toBeInTheDocument();
    expect(screen.getByText("It ships tomorrow.")).toBeInTheDocument();
    expect(screen.getByLabelText("Message composer")).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "New Chat" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Message composer")).not.toBeDisabled();
    });
  });

  it("streams assistant output, commits on response_end, and reuses thread_id for follow-up sends", async () => {
    const { fetchMock, requests } = createMockFetch({
      customers: [
        { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
      ],
      providers: {
        openrouter: { available: true, models: ["openai/gpt-4o"] },
      },
      sessions: [],
      streamRuns: [
        {
          events: [
            { type: "memory_loaded", thread_id: "thread-1", memory_context: [] },
            { type: "planner_start", thread_id: "thread-1" },
            { type: "response_token", thread_id: "thread-1", token: "Your " },
            { type: "response_token", thread_id: "thread-1", token: "order" },
            { type: "response_end", thread_id: "thread-1", response: "Your order" },
          ],
          chunks: [40, 20, 24],
        },
        {
          events: [
            { type: "planner_start", thread_id: "thread-1" },
            { type: "response_token", thread_id: "thread-1", token: "Still " },
            { type: "response_end", thread_id: "thread-1", response: "Still pending" },
          ],
        },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const composer = await screen.findByLabelText("Message composer");
    await userEvent.type(composer, "Where is my order?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Your order")).toBeInTheDocument();
    expect(screen.getByText("memory_loaded")).toBeInTheDocument();
    expect(screen.getByText("response_end")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Message composer"), "And now?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Still pending")).toBeInTheDocument();
    expect(requests).toHaveLength(2);
    expect(requests[0]).toMatchObject({
      customer_id: 1,
      provider: "openrouter",
      model: "openai/gpt-4o",
    });
    expect(requests[0].thread_id).toBeUndefined();
    expect(requests[1].thread_id).toBe("thread-1");
  });

  it("retains all SSE event types for the Right Panel placeholder", async () => {
    const { fetchMock } = createMockFetch({
      customers: [
        { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
      ],
      providers: {
        openrouter: { available: true, models: ["openai/gpt-4o"] },
      },
      sessions: [],
      streamRuns: [
        {
          events: [
            { type: "memory_loaded", thread_id: "thread-1", memory_context: [] },
            { type: "planner_start", thread_id: "thread-1" },
            { type: "planner_result", thread_id: "thread-1", content: "Checking", tool_calls: [{ name: "order_lookup", args: { order_id: 12345 } }] },
            { type: "tool_start", thread_id: "thread-1" },
            { type: "tool_result", thread_id: "thread-1", results: "{'status': 'pending'}" },
            { type: "verifier_result", thread_id: "thread-1", valid: true, checks: ["ok"], override_message: null },
            { type: "memory_updated", thread_id: "thread-1" },
            { type: "response_token", thread_id: "thread-1", token: "Pending" },
            { type: "response_end", thread_id: "thread-1", response: "Pending" },
          ],
        },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await userEvent.type(await screen.findByLabelText("Message composer"), "Where is my order?");
    await userEvent.click(screen.getByRole("button", { name: "Send" }));

    for (const eventName of [
      "memory_loaded",
      "planner_start",
      "planner_result",
      "tool_start",
      "tool_result",
      "verifier_result",
      "memory_updated",
      "response_token",
      "response_end",
    ]) {
      expect(await screen.findByText(eventName)).toBeInTheDocument();
    }
  });
});
