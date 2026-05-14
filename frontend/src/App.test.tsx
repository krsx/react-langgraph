import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { routes } from "./routes";

function renderRouter(path = "/chat") {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
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

  it("/chat route renders Chat heading", async () => {
    renderRouter("/chat");
    expect(await screen.findByRole("heading", { name: /^chat$/i })).toBeInTheDocument();
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
