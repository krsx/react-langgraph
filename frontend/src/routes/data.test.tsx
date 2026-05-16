import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DataPage } from "./data";
import { createMockFetch } from "../test-utils/mockApi";

const CUSTOMERS = [
  { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01T00:00:00Z" },
  { customer_id: 2, name: "Jane Doe", email: "jane@example.com", created_at: "2026-05-02T00:00:00Z" },
];

const ORDERS = [
  { order_id: 1001, customer_id: 1, product_name: "Widget Pro", status: "pending", order_date: "2026-05-03T00:00:00Z", delivery_date: null },
  { order_id: 1002, customer_id: 2, product_name: "Gadget X", status: "processing", order_date: "2026-05-04T00:00:00Z", delivery_date: null },
];

const COMPLAINTS = [
  { complaint_id: 9001, customer_id: 1, order_id: 1001, issue: "Late delivery", status: "open", created_at: "2026-05-05T00:00:00Z" },
];

const PROVIDERS = {
  openrouter: { available: true, models: ["gpt-4o"], default_model: "gpt-4o" },
};

function renderDataPage(overrides: Record<string, unknown> = {}) {
  const config = { customers: CUSTOMERS, orders: ORDERS, complaints: COMPLAINTS, providers: PROVIDERS, sessions: [], ...overrides };
  const { fetchMock } = createMockFetch(config);
  vi.stubGlobal("fetch", fetchMock);
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  return {
    fetchMock,
    queryClient,
    result: render(
      <QueryClientProvider client={queryClient}>
        <DataPage />
      </QueryClientProvider>,
    ),
  };
}

describe("DataPage tab switching", () => {
  it("renders the Data Explorer heading and three tabs", async () => {
    renderDataPage();

    expect(screen.getByRole("heading", { name: /data explorer/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /customers/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /orders/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /complaints/i })).toBeInTheDocument();
  });

  it("shows the Customers table with correct data by default", async () => {
    renderDataPage();

    expect(await screen.findByText("Ahmad Rifqi")).toBeInTheDocument();
    expect(screen.getByText("ahmad@example.com")).toBeInTheDocument();
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("switches to Orders tab and shows order data including processing status", async () => {
    renderDataPage();

    await userEvent.click(screen.getByRole("tab", { name: /orders/i }));

    expect(await screen.findByText("Widget Pro")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
    expect(screen.getByText("Gadget X")).toBeInTheDocument();
    expect(screen.getByText("processing")).toBeInTheDocument();
  });

  it("switches to Complaints tab and shows complaint data", async () => {
    renderDataPage();

    await userEvent.click(screen.getByRole("tab", { name: /complaints/i }));

    expect(await screen.findByText("Late delivery")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
  });
});

describe("DataPage Customers CRUD", () => {
  it("adds a new customer via dialog and refreshes the table", async () => {
    renderDataPage();

    await screen.findByText("Ahmad Rifqi");

    await userEvent.click(screen.getByRole("button", { name: /add customer/i }));

    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/name/i), "Charlie Brown");
    await userEvent.type(within(dialog).getByLabelText(/email/i), "charlie@example.com");
    await userEvent.click(within(dialog).getByRole("button", { name: /save/i }));

    expect(await screen.findByText("Charlie Brown")).toBeInTheDocument();
    expect(screen.getByText("charlie@example.com")).toBeInTheDocument();
  });

  it("edits a customer via dialog and refreshes the table", async () => {
    renderDataPage();

    await screen.findByText("Ahmad Rifqi");

    const rows = screen.getAllByRole("row");
    const ahmadRow = rows.find((r) => within(r).queryByText("Ahmad Rifqi"));
    const editBtn = within(ahmadRow!).getByRole("button", { name: /edit/i });
    await userEvent.click(editBtn);

    const dialog = await screen.findByRole("dialog");
    const nameInput = within(dialog).getByLabelText(/name/i);
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, "Ahmad Updated");
    await userEvent.click(within(dialog).getByRole("button", { name: /save/i }));

    expect(await screen.findByText("Ahmad Updated")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Ahmad Rifqi")).not.toBeInTheDocument();
    });
  });

  it("deletes a customer after confirmation dialog", async () => {
    renderDataPage();

    await screen.findByText("Ahmad Rifqi");

    const rows = screen.getAllByRole("row");
    const ahmadRow = rows.find((r) => within(r).queryByText("Ahmad Rifqi"));
    const deleteBtn = within(ahmadRow!).getByRole("button", { name: /delete/i });
    await userEvent.click(deleteBtn);

    const confirmDialog = await screen.findByRole("dialog");
    await userEvent.click(within(confirmDialog).getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      expect(screen.queryByText("Ahmad Rifqi")).not.toBeInTheDocument();
    });
  });
});

describe("DataPage Orders CRUD", () => {
  it("opens add order dialog with customer combobox and status combobox", async () => {
    renderDataPage();

    await userEvent.click(screen.getByRole("tab", { name: /orders/i }));
    await screen.findByText("Widget Pro");

    await userEvent.click(screen.getByRole("button", { name: /add order/i }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText(/product name/i)).toBeInTheDocument();
    expect(within(dialog).getByRole("combobox", { name: /customer/i })).toBeInTheDocument();
    expect(within(dialog).getByRole("combobox", { name: /status/i })).toBeInTheDocument();
  });

  it("deletes an order after confirmation dialog and refreshes the table", async () => {
    renderDataPage();

    await userEvent.click(screen.getByRole("tab", { name: /orders/i }));
    await screen.findByText("Widget Pro");

    const rows = screen.getAllByRole("row");
    const widgetRow = rows.find((r) => within(r).queryByText("Widget Pro"));
    const deleteBtn = within(widgetRow!).getByRole("button", { name: /delete/i });
    await userEvent.click(deleteBtn);

    const confirmDialog = await screen.findByRole("dialog");
    await userEvent.click(within(confirmDialog).getByRole("button", { name: /confirm/i }));

    await waitFor(() => {
      expect(screen.queryByText("Widget Pro")).not.toBeInTheDocument();
    });
  });
});
