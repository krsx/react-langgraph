import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { getComplaints, getCustomers, getOrders } from "../../lib/api";
import type { Complaint, Customer, Order } from "../../lib/types";
import { Button } from "../ui/button";

type DataExplorerPanelProps = {
  activeCustomerId: number | null;
};

type DataExplorerState = {
  complaints: Complaint[];
  customers: Customer[];
  orders: Order[];
};

function DataSection({
  children,
  title,
}: {
  children: ReactNode;
  title: string;
}) {
  return (
    <section
      aria-label={title}
      className="rounded-[24px] border border-border/70 bg-background/80 p-4 shadow-sm"
      role="region"
    >
      <h3 className="text-lg font-bold">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function renderRows(rows: string[][], emptyLabel: string) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-2 text-sm text-foreground">
      {rows.map((row, index) => (
        <li key={`${row.join("-")}-${index}`} className="rounded-2xl bg-card px-3 py-3">
          {row.map((value) => (
            <p key={value}>{value}</p>
          ))}
        </li>
      ))}
    </ul>
  );
}

export function DataExplorerPanel({ activeCustomerId }: DataExplorerPanelProps) {
  const [state, setState] = useState<DataExplorerState>({
    complaints: [],
    customers: [],
    orders: [],
  });

  async function loadData(cancelled?: () => boolean) {
    const [customers, orders, complaints] = await Promise.all([
      getCustomers(),
      getOrders(activeCustomerId),
      getComplaints(activeCustomerId),
    ]);

    if (cancelled?.()) {
      return;
    }

    setState({ customers, orders, complaints });
  }

  useEffect(() => {
    let isCancelled = false;

    void loadData(() => isCancelled);

    return () => {
      isCancelled = true;
    };
  }, [activeCustomerId]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Right Panel</p>
          <h2 className="text-xl font-bold">Data Explorer</h2>
        </div>
        <Button variant="outline" type="button" onClick={() => void loadData()}>
          Refresh
        </Button>
      </div>

      <DataSection title="Customers">
        {renderRows(
          state.customers.map((customer) => [customer.name, customer.email]),
          "No customers found.",
        )}
      </DataSection>

      <DataSection title="Orders">
        {renderRows(
          state.orders.map((order) => [String(order.order_id), order.product_name, order.status]),
          "No orders for the active customer.",
        )}
      </DataSection>

      <DataSection title="Complaints">
        {renderRows(
          state.complaints.map((complaint) => [String(complaint.complaint_id), complaint.issue, complaint.status]),
          "No complaints for the active customer.",
        )}
      </DataSection>
    </div>
  );
}
