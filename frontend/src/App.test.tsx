import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "./routes";
import { createMockFetch } from "./test-utils/mockApi";

function renderRouter(path = "/chat") {
  const { fetchMock } = createMockFetch({
    customers: [],
    providers: {},
    sessions: [],
  });
  vi.stubGlobal("fetch", fetchMock);

  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const router = createMemoryRouter(routes, { initialEntries: [path] });

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return router;
}

describe("App layout – foundation", () => {
  it("renders sidebar with Chat nav link", async () => {
    renderRouter("/chat");
    expect(await screen.findByRole("link", { name: /^chat$/i })).toBeInTheDocument();
  });

  it("sidebar has all three nav links", async () => {
    renderRouter("/chat");
    expect(await screen.findByRole("link", { name: /^chat$/i })).toBeInTheDocument();
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
});
