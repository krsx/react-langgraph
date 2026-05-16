import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryPage } from "./memory";
import { createMockFetch } from "../test-utils/mockApi";

const CUSTOMERS = [
  { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
  { customer_id: 2, name: "Bea Foo", email: "bea@example.com", created_at: "2026-05-02" },
];

const MEMORY_ENTRIES = [
  { key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" },
  { key: "vip_status", value: "gold", created_at: "2026-05-02T00:00:00Z" },
];

function renderMemoryPage(overrides: Parameters<typeof createMockFetch>[0]) {
  const { fetchMock } = createMockFetch(overrides);
  vi.stubGlobal("fetch", fetchMock);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryPage />
    </QueryClientProvider>,
  );
}

/** Open a Radix UI Select via keyboard — pointer events do not trigger it in jsdom. */
async function openSelect(combobox: HTMLElement) {
  combobox.focus();
  await userEvent.keyboard(" ");
  await waitFor(() => expect(combobox).toHaveAttribute("data-state", "open"));
}

describe("MemoryPage", () => {
  it("renders the page heading and customer selector", async () => {
    renderMemoryPage({ customers: CUSTOMERS, providers: {}, sessions: [] });

    expect(screen.getByRole("heading", { name: /memory manager/i })).toBeInTheDocument();
    expect(await screen.findByRole("combobox", { name: /customer/i })).toBeInTheDocument();
  });

  it("shows prompt to select a customer when no customers exist", async () => {
    renderMemoryPage({ customers: [], providers: {}, sessions: [] });

    expect(await screen.findByRole("combobox", { name: /customer/i })).toBeInTheDocument();
    expect(screen.getByText(/select a customer to view memory entries/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("auto-selects the first customer when customers load", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: { 1: MEMORY_ENTRIES },
    });

    expect(await screen.findByRole("cell", { name: "preferred_channel" })).toBeInTheDocument();
    expect(await screen.findByRole("combobox", { name: /customer/i })).toHaveTextContent("Ahmad Rifqi");
  });

  it("loads memory entries into the table after selecting a customer", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: { 1: MEMORY_ENTRIES },
    });

    const combobox = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /ahmad rifqi/i }));

    expect(await screen.findByRole("cell", { name: "preferred_channel" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "email" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "vip_status" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "gold" })).toBeInTheDocument();
  });

  it("shows empty state when selected customer has no memory entries", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: { 1: [] },
    });

    const combobox = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /ahmad rifqi/i }));

    expect(await screen.findByText(/no memory entries/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("opens Add Entry dialog and creates a new entry", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: { 1: [] },
    });

    const combobox = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /ahmad rifqi/i }));

    await screen.findByText(/no memory entries/i);

    await userEvent.click(screen.getByRole("button", { name: /add entry/i }));
    expect(await screen.findByRole("dialog", { name: /add memory entry/i })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^key$/i), "loyalty_tier");
    await userEvent.type(screen.getByLabelText(/^value$/i), "platinum");
    await userEvent.click(screen.getByRole("button", { name: /save/i }));

    expect(await screen.findByRole("cell", { name: "loyalty_tier" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "platinum" })).toBeInTheDocument();
  });

  it("opens Edit dialog pre-filled with current values and saves changes", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: { 1: [{ key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" }] },
    });

    const combobox = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /ahmad rifqi/i }));

    const row = await screen.findByRole("row", { name: /preferred_channel/i });
    await userEvent.click(within(row).getByRole("button", { name: /edit/i }));

    const dialog = await screen.findByRole("dialog", { name: /edit memory entry/i });
    expect(within(dialog).getByDisplayValue("email")).toBeInTheDocument();

    const valueInput = within(dialog).getByLabelText(/value/i);
    await userEvent.clear(valueInput);
    await userEvent.type(valueInput, "sms");
    await userEvent.click(within(dialog).getByRole("button", { name: /save/i }));

    expect(await screen.findByRole("cell", { name: "sms" })).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "email" })).not.toBeInTheDocument();
  });

  it("opens Delete confirmation dialog and removes entry on confirm", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: { 1: [{ key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" }] },
    });

    const combobox = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /ahmad rifqi/i }));

    const row = await screen.findByRole("row", { name: /preferred_channel/i });
    await userEvent.click(within(row).getByRole("button", { name: /delete/i }));

    const dialog = await screen.findByRole("dialog", { name: /delete memory entry/i });
    expect(within(dialog).getByText(/preferred_channel/i)).toBeInTheDocument();

    await userEvent.click(within(dialog).getByRole("button", { name: /delete/i }));

    expect(await screen.findByText(/no memory entries/i)).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "preferred_channel" })).not.toBeInTheDocument();
  });

  it("clears entries and reloads when switching to a different customer", async () => {
    renderMemoryPage({
      customers: CUSTOMERS,
      providers: {},
      sessions: [],
      memoryByCustomerId: {
        1: [{ key: "preferred_channel", value: "email", created_at: "2026-05-01T00:00:00Z" }],
        2: [{ key: "discount_code", value: "BEA10", created_at: "2026-05-02T00:00:00Z" }],
      },
    });

    const combobox = await screen.findByRole("combobox", { name: /customer/i });
    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /ahmad rifqi/i }));

    expect(await screen.findByRole("cell", { name: "preferred_channel" })).toBeInTheDocument();

    await openSelect(combobox);
    await userEvent.click(await screen.findByRole("option", { name: /bea foo/i }));

    expect(await screen.findByRole("cell", { name: "discount_code" })).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "preferred_channel" })).not.toBeInTheDocument();
  });
});
