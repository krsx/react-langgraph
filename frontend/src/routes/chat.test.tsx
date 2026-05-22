// Mock react-resizable-panels: the Group component uses ResizeObserver callbacks
// for layout calculation that never fire in jsdom, preventing state re-renders.
// Replace with lightweight div wrappers so tests exercise real chat logic.
vi.mock("react-resizable-panels", () => ({
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Group: ({ children, className }: any) => <div className={className}>{children}</div>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Panel: ({ children }: any) => <div>{children}</div>,
  Separator: () => <div />,
  usePanelRef: () => ({ current: null }),
}));

import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "../routes";
import { createMockFetch } from "../test-utils/mockApi";
import type { ChatStreamEvent } from "../lib/types";

const ALICE = { customer_id: 1, name: "Alice Chen", email: "alice@example.com", created_at: "2026-01-01T00:00:00Z" };
const BOB = { customer_id: 2, name: "Bob Tan", email: "bob@example.com", created_at: "2026-01-02T00:00:00Z" };
const CUSTOMERS = [ALICE, BOB];

const PROVIDERS = {
  openrouter: {
    available: true,
    models: ["google/gemini-2.5-flash"],
    default_model: "google/gemini-2.5-flash",
  },
  ollama: { available: true, models: ["qwen3:4b"], default_model: "qwen3:4b" },
};

const SESSIONS = [
  { thread_id: "t1", customer_id: 1, created_at: "2026-01-01T00:00:00Z", first_message: "Hello there", agent_type: "customer_service" as const },
  { thread_id: "t2", customer_id: 2, created_at: "2026-01-02T00:00:00Z", first_message: "Hi from Bob", agent_type: "customer_service" as const },
  { thread_id: "t3", customer_id: null, created_at: "2026-01-03T00:00:00Z", first_message: "Refund request email", agent_type: "refund_email" as const },
];

const SESSION_MESSAGES = {
  t1: [
    { message_id: 1, role: "human" as const, content: "Hello there", created_at: "2026-01-01T00:00:00Z" },
    { message_id: 2, role: "ai" as const, content: "Hi! How can I help you today?", created_at: "2026-01-01T00:01:00Z" },
  ],
  t3: [
    { message_id: 3, role: "human" as const, content: "Refund request email", created_at: "2026-01-03T00:00:00Z" },
    { message_id: 4, role: "ai" as const, content: "I can help draft your refund email.", created_at: "2026-01-03T00:01:00Z" },
  ],
};

type MockConfig = Parameters<typeof createMockFetch>[0];

function renderChat(config: MockConfig = { customers: CUSTOMERS, providers: PROVIDERS, sessions: SESSIONS, sessionMessages: SESSION_MESSAGES }) {
  const { fetchMock } = createMockFetch(config);
  vi.stubGlobal("fetch", fetchMock);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: ["/chat"] });
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

/** Wait until auto-selection is complete (textarea becomes enabled). */
async function waitForReady() {
  await waitFor(() => {
    expect(screen.getByRole("textbox", { name: /message/i })).not.toBeDisabled();
  });
}

/** Open a Radix UI Select via keyboard (Space) — pointer events do not open it in jsdom. */
async function openSelect(combobox: HTMLElement) {
  combobox.focus();
  await userEvent.keyboard(" ");
  await waitFor(() => expect(combobox).toHaveAttribute("data-state", "open"));
}

describe("ChatPage", () => {
  it("shows Customer, Provider, and Model selectors auto-populated from the API", async () => {
    const { container } = renderChat();

    expect(await screen.findByRole("combobox", { name: /customer/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /provider/i })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /model/i })).toBeInTheDocument();

    await waitFor(() => expect(screen.getByRole("combobox", { name: /customer/i })).toHaveTextContent("Alice Chen"));
    await waitFor(() => expect(screen.getByRole("combobox", { name: /provider/i })).toHaveTextContent("openrouter"));
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /model/i })).toHaveTextContent("google/gemini-2.5-flash"),
    );

    expect(container.querySelector(".h-8.w-px.bg-border")).toBeNull();
  });

  it("constrains the app shell to viewport height to prevent page-level scroll stealing", async () => {
    const { container } = renderChat();
    await screen.findByRole("combobox", { name: /customer/i });

    const wrapper = container.querySelector('[data-slot="sidebar-wrapper"]');
    expect(wrapper).toHaveClass("h-svh");
  });

  it("shows empty state placeholder when no messages have been sent", async () => {
    renderChat();
    await screen.findByRole("combobox", { name: /customer/i });
    expect(screen.getByText(/start a fresh conversation/i)).toBeInTheDocument();
  });

  it("sends a message and streams assistant tokens progressively", async () => {
    const streamEvents: ChatStreamEvent[] = [
      { type: "response_token", thread_id: "new-t1", token: "Hello" },
      { type: "response_token", thread_id: "new-t1", token: " world" },
      { type: "response_end", thread_id: "new-t1", response: "Hello world" },
    ];

    renderChat({ customers: CUSTOMERS, providers: PROVIDERS, sessions: [], streamRuns: [{ events: streamEvents, chunkEachEvent: true }] });

    await waitForReady();
    await userEvent.type(screen.getByRole("textbox", { name: /message/i }), "Tell me a joke");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("Tell me a joke")).toBeInTheDocument();
    expect(await screen.findByText("Hello world")).toBeInTheDocument();
  });

  it("shows sessions grouped by agent type in the sidebar", async () => {
    renderChat();
    await screen.findByTestId("agent-type-nav");

    // Expand Customer Service collapsible
    const allCSEls = await screen.findAllByText("Customer Service");
    await userEvent.click(allCSEls[allCSEls.length - 1]);
    expect(await screen.findByText("Hello there")).toBeInTheDocument();
    expect(screen.getByText("Hi from Bob")).toBeInTheDocument();

    // Expand Refund Email collapsible
    const allREEls = await screen.findAllByText("Refund Email");
    await userEvent.click(allREEls[allREEls.length - 1]);
    expect(await screen.findByText("Refund request email")).toBeInTheDocument();
  });

  it("loads read-only transcript when a sidebar session is clicked", async () => {
    renderChat();

    const allCSEls = await screen.findAllByText("Customer Service");
    await userEvent.click(allCSEls[allCSEls.length - 1]);

    await userEvent.click(await screen.findByText("Hello there"));

    expect(await screen.findByText("Hi! How can I help you today?")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("textbox", { name: /message/i })).toBeDisabled());
  });

  it("restores the session customer context when opening Customer Service history", async () => {
    renderChat();

    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /customer/i })).toHaveTextContent("Alice Chen"),
    );

    const allCSEls = await screen.findAllByText("Customer Service");
    await userEvent.click(allCSEls[allCSEls.length - 1]);
    await userEvent.click(await screen.findByText("Hi from Bob"));

    expect(await screen.findByText("Hi from Bob")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /customer/i })).toHaveTextContent("Bob Tan"),
    );
  });

  it("clicking an Agent Type button resets to a writable empty conversation", async () => {
    renderChat();

    const allCSEls = await screen.findAllByText("Customer Service");
    await userEvent.click(allCSEls[allCSEls.length - 1]);

    await userEvent.click(await screen.findByText("Hello there"));
    await screen.findByText("Hi! How can I help you today?");

    const nav = screen.getByTestId("agent-type-nav");
    await userEvent.click(within(nav).getByRole("button", { name: /customer service/i }));

    expect(await screen.findByText(/start a fresh conversation/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("textbox", { name: /message/i })).not.toBeDisabled());
  });

  it("loads refund email session history without being overwritten by provider auto-selection", async () => {
    renderChat();

    const allREEls = await screen.findAllByText("Refund Email");
    await userEvent.click(allREEls[allREEls.length - 1]);

    await userEvent.click(await screen.findByText("Refund request email"));

    expect(await screen.findByText("I can help draft your refund email.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("textbox", { name: /message/i })).toBeDisabled());
  });

  it("disables composer and send button when no customer is available", async () => {
    renderChat({ customers: [], providers: PROVIDERS, sessions: [] });

    await screen.findByRole("combobox", { name: /customer/i });

    expect(screen.getByRole("textbox", { name: /message/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("renders assistant response markdown — bold text becomes <strong>, not raw asterisks", async () => {
    const streamEvents: ChatStreamEvent[] = [
      { type: "response_token", thread_id: "t-md", token: "**Bold**" },
      { type: "response_end", thread_id: "t-md", response: "**Bold**" },
    ];

    renderChat({ customers: CUSTOMERS, providers: PROVIDERS, sessions: [], streamRuns: [{ events: streamEvents }] });

    await waitForReady();
    await userEvent.type(screen.getByRole("textbox", { name: /message/i }), "test");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    const boldEl = await screen.findByText("Bold");
    expect(boldEl.tagName.toLowerCase()).toBe("strong");
    expect(screen.queryByText("**Bold**")).not.toBeInTheDocument();
  });

  it("changing customer resets the conversation to empty", async () => {
    const streamEvents: ChatStreamEvent[] = [
      { type: "response_end", thread_id: "t-reset", response: "A response" },
    ];

    renderChat({ customers: CUSTOMERS, providers: PROVIDERS, sessions: [], streamRuns: [{ events: streamEvents }] });

    await waitForReady();

    await userEvent.type(screen.getByRole("textbox", { name: /message/i }), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText("A response")).toBeInTheDocument();

    // Radix Select must be opened via keyboard in jsdom (click does not trigger onPointerDown)
    await openSelect(screen.getByRole("combobox", { name: /customer/i }));
    await userEvent.click(await screen.findByRole("option", { name: /bob tan/i }));

    expect(await screen.findByText(/start a fresh conversation/i)).toBeInTheDocument();
    expect(screen.queryByText("A response")).not.toBeInTheDocument();
  });

  it("shows the Agent Process Panel open by default on the chat page", async () => {
    renderChat();
    expect(await screen.findByRole("heading", { name: /agent process/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /close agent process panel/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /open agent process panel/i })).not.toBeInTheDocument();
  });

  it("shows the trace empty state in history mode without requiring manual expansion", async () => {
    renderChat();

    const allCSEls = await screen.findAllByText("Customer Service");
    await userEvent.click(allCSEls[allCSEls.length - 1]);

    await userEvent.click(await screen.findByText("Hello there"));
    await screen.findByText("Hi! How can I help you today?");

    expect(
      await screen.findByText(/process trace is only available during live conversation/i),
    ).toBeInTheDocument();
  });

  it("renders the open select menu on a visible popover surface", async () => {
    renderChat();

    const customerSelect = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(customerSelect);

    const listbox = await screen.findByRole("listbox");
    const content = listbox.closest('[data-slot="select-content"]');
    expect(content).toHaveClass("bg-popover");
    expect(content).toHaveClass("text-popover-foreground");
  });

  it("keeps headers/composer fixed while chat and trace bodies are scrollable", async () => {
    renderChat();

    expect(await screen.findByRole("combobox", { name: /customer/i })).toBeInTheDocument();

    expect(screen.getByTestId("chat-header")).toHaveClass("sticky");
    expect(screen.getByTestId("chat-composer")).toHaveClass("sticky");
    expect(screen.getByTestId("conversation-scroll-region")).toHaveClass("overflow-y-auto");

    expect(screen.getByTestId("agent-process-header")).toHaveClass("sticky");
    expect(screen.getByTestId("agent-process-scroll-region")).toHaveClass("overflow-y-auto");
  });

  it("sidebar shows Agent Type nav items for Customer Service, Refund Email, and Calendar", async () => {
    renderChat();
    const nav = await screen.findByTestId("agent-type-nav");

    expect(within(nav).getByRole("button", { name: /customer service/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /refund email/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /calendar/i })).toBeInTheDocument();
  });

  it("Customer selector is shown when Customer Service agent is active", async () => {
    renderChat();
    expect(await screen.findByRole("combobox", { name: /customer/i })).toBeInTheDocument();
  });

  it("Customer selector is hidden when Refund Email agent is selected", async () => {
    renderChat();
    const nav = await screen.findByTestId("agent-type-nav");

    await userEvent.click(within(nav).getByRole("button", { name: /refund email/i }));

    await waitFor(() => expect(screen.queryByRole("combobox", { name: /customer/i })).not.toBeInTheDocument());
  });

  it("Customer selector is hidden when Calendar agent is selected", async () => {
    renderChat();
    const nav = await screen.findByTestId("agent-type-nav");

    await userEvent.click(within(nav).getByRole("button", { name: /calendar/i }));

    await waitFor(() => expect(screen.queryByRole("combobox", { name: /customer/i })).not.toBeInTheDocument());
  });

  it("switching to a workspace agent resets the conversation to empty", async () => {
    const streamEvents: ChatStreamEvent[] = [
      { type: "response_end", thread_id: "t-ws", response: "A response" },
    ];

    renderChat({ customers: CUSTOMERS, providers: PROVIDERS, sessions: [], streamRuns: [{ events: streamEvents }] });

    await waitForReady();
    await userEvent.type(screen.getByRole("textbox", { name: /message/i }), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(await screen.findByText("A response")).toBeInTheDocument();

    const nav = screen.getByTestId("agent-type-nav");
    await userEvent.click(within(nav).getByRole("button", { name: /refund email/i }));

    expect(await screen.findByText(/start a fresh conversation/i)).toBeInTheDocument();
    expect(screen.queryByText("A response")).not.toBeInTheDocument();
  });

  it("switching to a workspace agent reapplies the OpenRouter Gemini default after a manual override", async () => {
    renderChat({ customers: CUSTOMERS, providers: PROVIDERS, sessions: [] });

    await waitForReady();
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /provider/i })).toHaveTextContent("openrouter"),
    );

    await openSelect(screen.getByRole("combobox", { name: /provider/i }));
    await userEvent.click(await screen.findByRole("option", { name: /ollama/i }));

    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /provider/i })).toHaveTextContent("ollama"),
    );
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /model/i })).toHaveTextContent("qwen3:4b"),
    );

    const nav = screen.getByTestId("agent-type-nav");
    await userEvent.click(within(nav).getByRole("button", { name: /refund email/i }));

    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /provider/i })).toHaveTextContent("openrouter"),
    );
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: /model/i })).toHaveTextContent("google/gemini-2.5-flash"),
    );
  });

  it("sendMessage includes agent_type in the chat request body", async () => {
    const streamEvents: ChatStreamEvent[] = [
      { type: "response_end", thread_id: "t-at", response: "Done" },
    ];

    const { fetchMock } = createMockFetch({
      customers: CUSTOMERS,
      providers: PROVIDERS,
      sessions: [],
      streamRuns: [{ events: streamEvents }],
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = createMemoryRouter(routes, { initialEntries: ["/chat"] });
    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    await waitForReady();
    await userEvent.type(screen.getByRole("textbox", { name: /message/i }), "Hello");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByText("Done");

    const chatCall = fetchMock.mock.calls.find(([url]) => {
      const u = typeof url === "string" ? url : url instanceof URL ? url.toString() : (url as Request).url;
      return u.includes("/chat/stream");
    });
    expect(chatCall).toBeDefined();
    const body = JSON.parse(String(chatCall![1]?.body)) as Record<string, unknown>;
    expect(body).toHaveProperty("agent_type", "customer_service");
    expect(body).toHaveProperty("customer_id");

    unmount();
  });

  it("sendMessage omits customer_id for workspace agent requests", async () => {
    const streamEvents: ChatStreamEvent[] = [
      { type: "response_end", thread_id: "t-ws2", response: "Done" },
    ];

    const { fetchMock } = createMockFetch({
      customers: CUSTOMERS,
      providers: PROVIDERS,
      sessions: [],
      streamRuns: [{ events: streamEvents }],
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const router = createMemoryRouter(routes, { initialEntries: ["/chat"] });
    const { unmount } = render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    // Switch to Refund Email agent
    const nav = await screen.findByTestId("agent-type-nav");
    await userEvent.click(within(nav).getByRole("button", { name: /refund email/i }));

    // Wait for provider to be available (textarea enabled without customer)
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: /message/i })).not.toBeDisabled();
    });

    await userEvent.type(screen.getByRole("textbox", { name: /message/i }), "Draft email");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    await screen.findByText("Done");

    const chatCall = fetchMock.mock.calls.find(([url]) => {
      const u = typeof url === "string" ? url : url instanceof URL ? url.toString() : (url as Request).url;
      return u.includes("/chat/stream");
    });
    expect(chatCall).toBeDefined();
    const body = JSON.parse(String(chatCall![1]?.body)) as Record<string, unknown>;
    expect(body).toHaveProperty("agent_type", "refund_email");
    expect(body).not.toHaveProperty("customer_id");

    unmount();
  });
});
