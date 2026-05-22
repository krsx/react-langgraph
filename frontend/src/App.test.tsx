import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient } from "@tanstack/react-query";
import { createMemoryRouter } from "react-router-dom";
import { App } from "./App";
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

  render(<App router={router} queryClient={queryClient} />);
  return { router, user: userEvent.setup() };
}

describe("App layout – foundation", () => {
  it("renders sidebar with Agent Type nav items", async () => {
    renderRouter("/chat");
    const nav = await screen.findByTestId("agent-type-nav");
    expect(within(nav).getByRole("button", { name: /customer service/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /refund email/i })).toBeInTheDocument();
    expect(within(nav).getByRole("button", { name: /calendar/i })).toBeInTheDocument();
  });

  it("sidebar has agent type buttons and tool nav links", async () => {
    renderRouter("/chat");
    const nav = await screen.findByTestId("agent-type-nav");
    expect(within(nav).getByRole("button", { name: /customer service/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /data explorer/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /memory manager/i })).toBeInTheDocument();
  });

  it("sidebar has Customer Service session history collapsible group", async () => {
    renderRouter("/chat");
    await screen.findByTestId("agent-type-nav");
    // Both agent type nav and session history groups show agent type names — verify groups exist
    const allCustomerServiceEls = screen.getAllByText("Customer Service");
    expect(allCustomerServiceEls.length).toBeGreaterThanOrEqual(2);
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
          agent_type: "customer_service" as const,
        },
      ],
    });

    // Session history collapsibles start closed — expand Customer Service section first
    await screen.findByTestId("agent-type-nav");
    const allCustomerServiceEls = await screen.findAllByText("Customer Service");
    await user.click(allCustomerServiceEls[allCustomerServiceEls.length - 1]);

    expect(await screen.findByText(sessionSummary)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /toggle sidebar/i }));

    expect(screen.queryByText(sessionSummary)).not.toBeInTheDocument();
  });

  it("renders Agent Type nav section above session history groups", async () => {
    renderRouter("/chat");

    const nav = await screen.findByTestId("agent-type-nav");
    const customerServiceBtn = within(nav).getByRole("button", { name: /customer service/i });

    // Session history group labels appear below the nav section in the DOM
    const allCustomerServiceElements = screen.getAllByText("Customer Service");
    expect(allCustomerServiceElements.length).toBeGreaterThanOrEqual(2);
    // The nav button precedes the session group label
    expect(customerServiceBtn.compareDocumentPosition(allCustomerServiceElements[allCustomerServiceElements.length - 1]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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
