import { streamChat } from "./sse";
import type {
  ChatRequest,
  ChatStreamEvent,
  Complaint,
  Customer,
  CustomerMemoryRecord,
  Order,
  ProviderCatalog,
  SessionMessage,
  SessionSummary,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getCustomers(): Promise<Customer[]> {
  return fetchJson<Customer[]>("/customers");
}

export function createCustomer(payload: { name: string; email: string }): Promise<Customer> {
  return fetchJson<Customer>("/customers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateCustomer(customerId: number, payload: { name?: string; email?: string }): Promise<Customer> {
  return fetchJson<Customer>(`/customers/${customerId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteCustomer(customerId: number): Promise<{ deleted: boolean; customer_id: number }> {
  return fetchJson<{ deleted: boolean; customer_id: number }>(`/customers/${customerId}`, {
    method: "DELETE",
  });
}

export function getOrders(customerId: number | null): Promise<Order[]> {
  const search = customerId === null ? "" : `?customer_id=${customerId}`;
  return fetchJson<Order[]>(`/orders${search}`);
}

export function createOrder(payload: { customer_id: number; product_name: string; status: string }): Promise<Order> {
  return fetchJson<Order>("/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateOrder(orderId: number, payload: { customer_id?: number; product_name?: string; status?: string }): Promise<Order> {
  return fetchJson<Order>(`/orders/${orderId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteOrder(orderId: number): Promise<{ deleted: boolean; order_id: number }> {
  return fetchJson<{ deleted: boolean; order_id: number }>(`/orders/${orderId}`, {
    method: "DELETE",
  });
}

export function getComplaints(customerId: number | null): Promise<Complaint[]> {
  const search = customerId === null ? "" : `?customer_id=${customerId}`;
  return fetchJson<Complaint[]>(`/complaints${search}`);
}

export function createComplaint(payload: { customer_id: number; order_id: number; issue: string; status: string }): Promise<Complaint> {
  return fetchJson<Complaint>("/complaints", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function updateComplaint(complaintId: number, payload: { customer_id?: number; order_id?: number; issue?: string; status?: string }): Promise<Complaint> {
  return fetchJson<Complaint>(`/complaints/${complaintId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function deleteComplaint(complaintId: number): Promise<{ deleted: boolean; complaint_id: number }> {
  return fetchJson<{ deleted: boolean; complaint_id: number }>(`/complaints/${complaintId}`, {
    method: "DELETE",
  });
}

export function getMemory(customerId: number): Promise<CustomerMemoryRecord[]> {
  return fetchJson<CustomerMemoryRecord[]>(`/memory/${customerId}`);
}

export function putMemory(
  customerId: number,
  entries: Array<{ key: string; value: string }>,
): Promise<{ updated: number }> {
  return fetchJson<{ updated: number }>(`/memory/${customerId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(entries),
  });
}

export function deleteMemoryEntry(customerId: number, key: string): Promise<{ deleted: boolean }> {
  return fetchJson<{ deleted: boolean }>(`/memory/${customerId}/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
}

export function getProviders(): Promise<ProviderCatalog> {
  return fetchJson<ProviderCatalog>("/providers");
}

export function getSessions(): Promise<SessionSummary[]> {
  return fetchJson<SessionSummary[]>("/sessions");
}

export async function getSessionMessages(threadId: string): Promise<SessionMessage[]> {
  const data = await fetchJson<{ session: unknown; messages: SessionMessage[] }>(`/sessions/${threadId}`);
  return data.messages;
}

export async function postChatStream(
  request: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  await streamChat(request, onEvent);
}
