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

export function getOrders(customerId: number | null): Promise<Order[]> {
  const search = customerId === null ? "" : `?customer_id=${customerId}`;
  return fetchJson<Order[]>(`/orders${search}`);
}

export function getComplaints(customerId: number | null): Promise<Complaint[]> {
  const search = customerId === null ? "" : `?customer_id=${customerId}`;
  return fetchJson<Complaint[]>(`/complaints${search}`);
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

export function getSessionMessages(threadId: string): Promise<SessionMessage[]> {
  return fetchJson<SessionMessage[]>(`/sessions/${threadId}`);
}

export async function postChatStream(
  request: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  await streamChat(request, onEvent);
}
