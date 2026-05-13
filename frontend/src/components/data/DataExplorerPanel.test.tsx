import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataExplorerPanel } from "./DataExplorerPanel";
import { createMockFetch } from "../../test-utils/mockApi";

describe("DataExplorerPanel", () => {
  it("renders global customers plus active-customer orders and complaints", async () => {
    const { fetchMock } = createMockFetch({
      customers: [
        { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
        { customer_id: 2, name: "Bea Foo", email: "bea@example.com", created_at: "2026-05-02" },
      ],
      providers: {},
      sessions: [],
      orders: [
        { order_id: 1001, customer_id: 1, product_name: "Widget", status: "pending", created_at: "2026-05-03" },
      ],
      complaints: [
        {
          complaint_id: 9001,
          customer_id: 1,
          order_id: 1001,
          issue: "Late delivery",
          status: "open",
          created_at: "2026-05-04",
        },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<DataExplorerPanel activeCustomerId={1} />);

    const customersSection = await screen.findByRole("region", { name: "Customers" });
    expect(within(customersSection).getByText("Ahmad Rifqi")).toBeInTheDocument();
    expect(within(customersSection).getByText("Bea Foo")).toBeInTheDocument();

    const ordersSection = screen.getByRole("region", { name: "Orders" });
    expect(await within(ordersSection).findByText("Widget")).toBeInTheDocument();
    expect(within(ordersSection).getByText("pending")).toBeInTheDocument();

    const complaintsSection = screen.getByRole("region", { name: "Complaints" });
    expect(await within(complaintsSection).findByText("Late delivery")).toBeInTheDocument();
    expect(within(complaintsSection).getByText("open")).toBeInTheDocument();
  });

  it("refetches scoped data when Refresh is clicked", async () => {
    let orders = [
      { order_id: 1001, customer_id: 1, product_name: "Widget", status: "pending", created_at: "2026-05-03" },
    ];
    let complaints = [
      {
        complaint_id: 9001,
        customer_id: 1,
        order_id: 1001,
        issue: "Late delivery",
        status: "open",
        created_at: "2026-05-04",
      },
    ];

    const { fetchMock } = createMockFetch({
      customers: [
        { customer_id: 1, name: "Ahmad Rifqi", email: "ahmad@example.com", created_at: "2026-05-01" },
      ],
      providers: {},
      sessions: [],
      get orders() {
        return orders;
      },
      get complaints() {
        return complaints;
      },
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<DataExplorerPanel activeCustomerId={1} />);

    expect(await screen.findByText("Widget")).toBeInTheDocument();
    expect(screen.getByText("Late delivery")).toBeInTheDocument();

    orders = [
      { order_id: 1002, customer_id: 1, product_name: "Replacement", status: "delivered", created_at: "2026-05-05" },
    ];
    complaints = [];

    await userEvent.click(screen.getByRole("button", { name: "Refresh" }));

    expect(await screen.findByText("Replacement")).toBeInTheDocument();
    expect(screen.getByText("delivered")).toBeInTheDocument();
    expect(screen.queryByText("Widget")).not.toBeInTheDocument();
    expect(screen.getByText("No complaints for the active customer.")).toBeInTheDocument();
  });

  it("shows clear empty states for customers, orders, and complaints", async () => {
    const { fetchMock } = createMockFetch({
      customers: [],
      providers: {},
      sessions: [],
      orders: [],
      complaints: [],
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<DataExplorerPanel activeCustomerId={1} />);

    expect(await screen.findByText("No customers found.")).toBeInTheDocument();
    expect(screen.getByText("No orders for the active customer.")).toBeInTheDocument();
    expect(screen.getByText("No complaints for the active customer.")).toBeInTheDocument();
  });
});
