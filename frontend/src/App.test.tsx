import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "./routes";
import { createMockFetch } from "./test-utils/mockApi";
import type { Customer, ProviderCatalog, SessionSummary } from "./lib/types";

type RenderConfig = {
  customers?: Customer[];
  providers?: ProviderCatalog;
  sessions?: SessionSummary[];
};

function renderRouter(path = "/chat", config: RenderConfig = {}) {
  const { fetchMock } = createMockFetch({
    customers: config.customers ?? [],
    providers: config.providers ?? {},
    sessions: config.sessions ?? [],
  });
  vi.stubGlobal("fetch", fetchMock);

  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, user: userEvent.setup() };
}

describe("App layout – foundation", () => {
  it("renders sidebar with New Chat nav link", async () => {
    renderRouter("/chat");
    expect(await screen.findByRole("link", { name: /^new chat$/i })).toBeInTheDocument();
  });

  it("sidebar has all three nav links", async () => {
    renderRouter("/chat");
    expect(await screen.findByRole("link", { name: /^new chat$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /data explorer/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /memory manager/i })).toBeInTheDocument();
  });

  it("sidebar has Session History collapsible group", async () => {
    renderRouter("/chat");
    expect(await screen.findByText("Session History")).toBeInTheDocument();
  });

  it("/chat route renders the chat interface with message composer", async () => {
    renderRouter("/chat");
    expect(await screen.findByRole("textbox", { name: /message/i })).toBeInTheDocument();
  });

  it("/data route renders Data Explorer heading", async () => {
    renderRouter("/data");
    expect(await screen.findByRole("heading", { name: /data explorer/i })).toBeInTheDocument();
  });

  it("/memory route renders Memory Manager heading", async () => {
    renderRouter("/memory");
    expect(await screen.findByRole("heading", { name: /memory manager/i })).toBeInTheDocument();
  });

  it("hides session history when the sidebar is collapsed", async () => {
    const sessionSummary = "Need refund for order 1001";
    const { user } = renderRouter("/chat", {
      customers: [
        {
          customer_id: 1,
          name: "Ada Lovelace",
          email: "ada@example.com",
          created_at: "2026-05-01T00:00:00Z",
        },
      ],
      providers: {
        openai: {
          available: true,
          models: ["gpt-4o-mini"],
          default_model: "gpt-4o-mini",
        },
      },
      sessions: [
        {
          thread_id: "thread-1",
          customer_id: 1,
          created_at: "2026-05-01T00:00:00Z",
          first_message: sessionSummary,
        },
      ],
    });

    expect(await screen.findByText("Session History")).toBeInTheDocument();
    expect(await screen.findByText(sessionSummary)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /toggle sidebar/i }));

    expect(screen.queryByText("Session History")).not.toBeInTheDocument();
    expect(screen.queryByText(sessionSummary)).not.toBeInTheDocument();
  });

  it("renders New Chat nav item above Session History", async () => {
    renderRouter("/chat", {
      customers: [
        {
          customer_id: 1,
          name: "Ada Lovelace",
          email: "ada@example.com",
          created_at: "2026-05-01T00:00:00Z",
        },
      ],
      providers: {
        openai: {
          available: true,
          models: ["gpt-4o-mini"],
          default_model: "gpt-4o-mini",
        },
      },
    });

    const newChatButton = await screen.findByRole("link", { name: /new chat/i });
    const sessionHistory = screen.getByText("Session History");

    expect(newChatButton.compareDocumentPosition(sessionHistory) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("renders select triggers on a visible background surface", async () => {
    renderRouter("/chat", {
      customers: [
        {
          customer_id: 1,
          name: "Ada Lovelace",
          email: "ada@example.com",
          created_at: "2026-05-01T00:00:00Z",
        },
      ],
      providers: {
        openai: {
          available: true,
          models: ["gpt-4o-mini"],
          default_model: "gpt-4o-mini",
        },
      },
    });

    const customerSelect = await screen.findByRole("combobox", { name: /customer/i });
    const providerSelect = screen.getByRole("combobox", { name: /provider/i });
    const modelSelect = screen.getByRole("combobox", { name: /model/i });

    expect(customerSelect).toHaveClass("bg-card");
    expect(providerSelect).toHaveClass("bg-card");
    expect(modelSelect).toHaveClass("bg-card");
  });
});
