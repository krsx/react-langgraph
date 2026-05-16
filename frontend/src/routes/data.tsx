import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCustomers, createCustomer, updateCustomer, deleteCustomer,
  getOrders, createOrder, updateOrder, deleteOrder,
  getComplaints, createComplaint, updateComplaint, deleteComplaint,
} from "../lib/api";
import type { Customer, Order, Complaint } from "../lib/types";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/table";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../components/ui/select";
import { Textarea } from "../components/ui/textarea";

// ─── Order statuses from backend seed data ────────────────────────────────────
const ORDER_STATUSES = ["pending", "processing", "delivered", "refund_requested"] as const;
const COMPLAINT_STATUSES = ["open", "resolved", "closed"] as const;

// ─── Shared label wrapper ──────────────────────────────────────────────────────
function Field({ label, htmlFor, children }: { label: string; htmlFor: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1.5">
      <label htmlFor={htmlFor} className="text-sm font-medium leading-none">
        {label}
      </label>
      {children}
    </div>
  );
}

// ─── Loading / error / empty states ───────────────────────────────────────────
function TableState({ colSpan, children }: { colSpan: number; children: React.ReactNode }) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan} className="py-10 text-center text-sm text-muted-foreground">
        {children}
      </TableCell>
    </TableRow>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Customers Tab
// ══════════════════════════════════════════════════════════════════════════════

type CustomerForm = { name: string; email: string };

function CustomerDialog({
  open,
  initial,
  onClose,
  onSave,
}: {
  open: boolean;
  initial?: Customer | null;
  onClose: () => void;
  onSave: (form: CustomerForm) => void;
}) {
  const [form, setForm] = useState<CustomerForm>({ name: "", email: "" });

  useEffect(() => {
    if (open) setForm({ name: initial?.name ?? "", email: initial?.email ?? "" });
  }, [open, initial?.customer_id]);

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) onClose();
  };

  const handleSave = () => {
    if (!form.name.trim() || !form.email.trim()) return;
    onSave(form);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit Customer" : "Add Customer"}</DialogTitle>
          <DialogDescription>
            {initial ? "Update the customer's details." : "Fill in the details for the new customer."}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <Field label="Name" htmlFor="customer-name">
            <Input
              id="customer-name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Full name"
            />
          </Field>
          <Field label="Email" htmlFor="customer-email">
            <Input
              id="customer-email"
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="email@example.com"
            />
          </Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteConfirmDialog({
  open,
  description,
  onClose,
  onConfirm,
}: {
  open: boolean;
  description: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm Delete</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button variant="destructive" onClick={onConfirm}>Confirm</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CustomersTab() {
  const qc = useQueryClient();
  const { data: customers, isLoading, isError } = useQuery({ queryKey: ["customers"], queryFn: () => getCustomers() });

  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Customer | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Customer | null>(null);

  const addMutation = useMutation({
    mutationFn: (form: CustomerForm) => createCustomer(form),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["customers"] }); setAddOpen(false); },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, form }: { id: number; form: CustomerForm }) => updateCustomer(id, form),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["customers"] }); setEditTarget(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteCustomer(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["customers"] }); setDeleteTarget(null); },
  });

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{customers?.length ?? 0} records</p>
        <Button size="sm" onClick={() => setAddOpen(true)}>Add Customer</Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Created At</TableHead>
            <TableHead className="w-[120px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && <TableState colSpan={5}>Loading…</TableState>}
          {isError && <TableState colSpan={5}>Failed to load customers.</TableState>}
          {!isLoading && !isError && customers?.length === 0 && (
            <TableState colSpan={5}>No customers found.</TableState>
          )}
          {customers?.map((c) => (
            <TableRow key={c.customer_id}>
              <TableCell className="tabular-nums">{c.customer_id}</TableCell>
              <TableCell>{c.name}</TableCell>
              <TableCell>{c.email}</TableCell>
              <TableCell className="text-muted-foreground">{c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" onClick={() => setEditTarget(c)}>Edit</Button>
                  <Button size="sm" variant="destructive" onClick={() => setDeleteTarget(c)}>Delete</Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <CustomerDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSave={(form) => addMutation.mutate(form)}
      />
      <CustomerDialog
        open={!!editTarget}
        initial={editTarget}
        onClose={() => setEditTarget(null)}
        onSave={(form) => editMutation.mutate({ id: editTarget!.customer_id, form })}
      />
      <DeleteConfirmDialog
        open={!!deleteTarget}
        description={`Delete customer "${deleteTarget?.name}"? This cannot be undone.`}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget!.customer_id)}
      />
    </>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Orders Tab
// ══════════════════════════════════════════════════════════════════════════════

type OrderForm = { customer_id: string; product_name: string; status: string };

function OrderDialog({
  open,
  initial,
  customers,
  onClose,
  onSave,
}: {
  open: boolean;
  initial?: Order | null;
  customers: Customer[];
  onClose: () => void;
  onSave: (form: OrderForm) => void;
}) {
  const [form, setForm] = useState<OrderForm>({ customer_id: "", product_name: "", status: "pending" });

  useEffect(() => {
    if (open) setForm({
      customer_id: initial ? String(initial.customer_id) : "",
      product_name: initial?.product_name ?? "",
      status: initial?.status ?? "pending",
    });
  }, [open, initial?.order_id]);

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) onClose();
  };

  const handleSave = () => {
    if (!form.customer_id || !form.product_name.trim() || !form.status) return;
    onSave(form);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit Order" : "Add Order"}</DialogTitle>
          <DialogDescription>
            {initial ? "Update the order details." : "Fill in the details for the new order."}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <Field label="Customer" htmlFor="order-customer">
            <Select
              value={form.customer_id}
              onValueChange={(v) => setForm((f) => ({ ...f, customer_id: v }))}
            >
              <SelectTrigger id="order-customer" aria-label="Customer">
                <SelectValue placeholder="Select customer" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.customer_id} value={String(c.customer_id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Product Name" htmlFor="order-product">
            <Input
              id="order-product"
              value={form.product_name}
              onChange={(e) => setForm((f) => ({ ...f, product_name: e.target.value }))}
              placeholder="Product name"
            />
          </Field>
          <Field label="Status" htmlFor="order-status">
            <Select
              value={form.status}
              onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}
            >
              <SelectTrigger id="order-status" aria-label="Status">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                {ORDER_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function OrdersTab() {
  const qc = useQueryClient();
  const { data: customers = [] } = useQuery({ queryKey: ["customers"], queryFn: () => getCustomers() });
  const { data: orders, isLoading, isError } = useQuery({ queryKey: ["orders"], queryFn: () => getOrders(null) });

  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Order | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Order | null>(null);

  const customerName = (id: number) => customers.find((c) => c.customer_id === id)?.name ?? String(id);

  const addMutation = useMutation({
    mutationFn: (form: OrderForm) => createOrder({ customer_id: Number(form.customer_id), product_name: form.product_name, status: form.status }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["orders"] }); setAddOpen(false); },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, form }: { id: number; form: OrderForm }) =>
      updateOrder(id, { customer_id: Number(form.customer_id), product_name: form.product_name, status: form.status }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["orders"] }); setEditTarget(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteOrder(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["orders"] }); setDeleteTarget(null); },
  });

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{orders?.length ?? 0} records</p>
        <Button size="sm" onClick={() => setAddOpen(true)}>Add Order</Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead>Product Name</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Order Date</TableHead>
            <TableHead className="w-[120px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && <TableState colSpan={6}>Loading…</TableState>}
          {isError && <TableState colSpan={6}>Failed to load orders.</TableState>}
          {!isLoading && !isError && orders?.length === 0 && (
            <TableState colSpan={6}>No orders found.</TableState>
          )}
          {orders?.map((o) => (
            <TableRow key={o.order_id}>
              <TableCell className="tabular-nums">{o.order_id}</TableCell>
              <TableCell>{customerName(o.customer_id)}</TableCell>
              <TableCell>{o.product_name}</TableCell>
              <TableCell>{o.status}</TableCell>
              <TableCell className="text-muted-foreground">{o.order_date ? new Date(o.order_date).toLocaleDateString() : "—"}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" onClick={() => setEditTarget(o)}>Edit</Button>
                  <Button size="sm" variant="destructive" onClick={() => setDeleteTarget(o)}>Delete</Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <OrderDialog
        open={addOpen}
        customers={customers}
        onClose={() => setAddOpen(false)}
        onSave={(form) => addMutation.mutate(form)}
      />
      <OrderDialog
        open={!!editTarget}
        initial={editTarget}
        customers={customers}
        onClose={() => setEditTarget(null)}
        onSave={(form) => editMutation.mutate({ id: editTarget!.order_id, form })}
      />
      <DeleteConfirmDialog
        open={!!deleteTarget}
        description={`Delete order #${deleteTarget?.order_id} "${deleteTarget?.product_name}"? This cannot be undone.`}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget!.order_id)}
      />
    </>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Complaints Tab
// ══════════════════════════════════════════════════════════════════════════════

type ComplaintForm = { customer_id: string; order_id: string; issue: string; status: string };

function parsePositiveInt(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed <= 0) return null;
  return parsed;
}

function ComplaintDialog({
  open,
  initial,
  customers,
  onClose,
  onSave,
}: {
  open: boolean;
  initial?: Complaint | null;
  customers: Customer[];
  onClose: () => void;
  onSave: (form: ComplaintForm) => void;
}) {
  const [form, setForm] = useState<ComplaintForm>({ customer_id: "", order_id: "", issue: "", status: "open" });

  useEffect(() => {
    if (open) setForm({
      customer_id: initial ? String(initial.customer_id) : "",
      order_id: initial?.order_id ? String(initial.order_id) : "",
      issue: initial?.issue ?? "",
      status: initial?.status ?? "open",
    });
  }, [open, initial?.complaint_id]);

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) onClose();
  };

  const handleSave = () => {
    const orderId = parsePositiveInt(form.order_id);
    if (!form.customer_id || !form.issue.trim() || !form.status || orderId === null) return;
    onSave(form);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{initial ? "Edit Complaint" : "Add Complaint"}</DialogTitle>
          <DialogDescription>
            {initial ? "Update the complaint details." : "Fill in the details for the new complaint."}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <Field label="Customer" htmlFor="complaint-customer">
            <Select
              value={form.customer_id}
              onValueChange={(v) => setForm((f) => ({ ...f, customer_id: v }))}
            >
              <SelectTrigger id="complaint-customer" aria-label="Customer">
                <SelectValue placeholder="Select customer" />
              </SelectTrigger>
              <SelectContent>
                {customers.map((c) => (
                  <SelectItem key={c.customer_id} value={String(c.customer_id)}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="Order ID" htmlFor="complaint-order">
            <Input
              id="complaint-order"
              type="number"
              min="1"
              step="1"
              value={form.order_id}
              onChange={(e) => setForm((f) => ({ ...f, order_id: e.target.value }))}
              placeholder="Order ID"
            />
          </Field>
          <Field label="Issue" htmlFor="complaint-issue">
            <Textarea
              id="complaint-issue"
              value={form.issue}
              onChange={(e) => setForm((f) => ({ ...f, issue: e.target.value }))}
              placeholder="Describe the issue"
              rows={3}
            />
          </Field>
          <Field label="Status" htmlFor="complaint-status">
            <Select
              value={form.status}
              onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}
            >
              <SelectTrigger id="complaint-status" aria-label="Status">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                {COMPLAINT_STATUSES.map((s) => (
                  <SelectItem key={s} value={s}>{s}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ComplaintsTab() {
  const qc = useQueryClient();
  const { data: customers = [] } = useQuery({ queryKey: ["customers"], queryFn: () => getCustomers() });
  const { data: complaints, isLoading, isError } = useQuery({ queryKey: ["complaints"], queryFn: () => getComplaints(null) });

  const [addOpen, setAddOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<Complaint | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Complaint | null>(null);

  const customerName = (id: number) => customers.find((c) => c.customer_id === id)?.name ?? String(id);

  const addMutation = useMutation({
    mutationFn: (form: ComplaintForm) => {
      const orderId = parsePositiveInt(form.order_id);
      if (orderId === null) throw new Error("Order ID must be a positive integer");
      return createComplaint({
        customer_id: Number(form.customer_id),
        order_id: orderId,
        issue: form.issue,
        status: form.status,
      });
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["complaints"] }); setAddOpen(false); },
  });

  const editMutation = useMutation({
    mutationFn: ({ id, form }: { id: number; form: ComplaintForm }) => {
      const orderId = form.order_id ? parsePositiveInt(form.order_id) : undefined;
      if (form.order_id && orderId === null) throw new Error("Order ID must be a positive integer");
      return updateComplaint(id, {
        customer_id: Number(form.customer_id),
        order_id: orderId ?? undefined,
        issue: form.issue,
        status: form.status,
      });
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["complaints"] }); setEditTarget(null); },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteComplaint(id),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ["complaints"] }); setDeleteTarget(null); },
  });

  return (
    <>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-muted-foreground">{complaints?.length ?? 0} records</p>
        <Button size="sm" onClick={() => setAddOpen(true)}>Add Complaint</Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead>Order ID</TableHead>
            <TableHead>Issue</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created At</TableHead>
            <TableHead className="w-[120px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading && <TableState colSpan={7}>Loading…</TableState>}
          {isError && <TableState colSpan={7}>Failed to load complaints.</TableState>}
          {!isLoading && !isError && complaints?.length === 0 && (
            <TableState colSpan={7}>No complaints found.</TableState>
          )}
          {complaints?.map((c) => (
            <TableRow key={c.complaint_id}>
              <TableCell className="tabular-nums">{c.complaint_id}</TableCell>
              <TableCell>{customerName(c.customer_id)}</TableCell>
              <TableCell className="tabular-nums">{c.order_id ?? "—"}</TableCell>
              <TableCell className="max-w-[200px] truncate">{c.issue}</TableCell>
              <TableCell>{c.status}</TableCell>
              <TableCell className="text-muted-foreground">{new Date(c.created_at).toLocaleDateString()}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" onClick={() => setEditTarget(c)}>Edit</Button>
                  <Button size="sm" variant="destructive" onClick={() => setDeleteTarget(c)}>Delete</Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <ComplaintDialog
        open={addOpen}
        customers={customers}
        onClose={() => setAddOpen(false)}
        onSave={(form) => addMutation.mutate(form)}
      />
      <ComplaintDialog
        open={!!editTarget}
        initial={editTarget}
        customers={customers}
        onClose={() => setEditTarget(null)}
        onSave={(form) => editMutation.mutate({ id: editTarget!.complaint_id, form })}
      />
      <DeleteConfirmDialog
        open={!!deleteTarget}
        description={`Delete complaint #${deleteTarget?.complaint_id}? This cannot be undone.`}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteMutation.mutate(deleteTarget!.complaint_id)}
      />
    </>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// Page root
// ══════════════════════════════════════════════════════════════════════════════

export function DataPage() {
  return (
    <div className="flex h-full flex-col">
      <header className="border-b px-6 py-4">
        <h1 className="text-xl font-semibold tracking-tight">Data Explorer</h1>
      </header>

      <div className="flex-1 overflow-auto px-6 py-4">
        <Tabs defaultValue="customers">
          <TabsList className="mb-4">
            <TabsTrigger value="customers">Customers</TabsTrigger>
            <TabsTrigger value="orders">Orders</TabsTrigger>
            <TabsTrigger value="complaints">Complaints</TabsTrigger>
          </TabsList>

          <TabsContent value="customers">
            <CustomersTab />
          </TabsContent>

          <TabsContent value="orders">
            <OrdersTab />
          </TabsContent>

          <TabsContent value="complaints">
            <ComplaintsTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
