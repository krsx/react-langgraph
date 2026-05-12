import { streamChat } from "./sse";
import type {
  ChatRequest,
  ChatStreamEvent,
  Customer,
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
