import type { Customer, ProvidersResponse, SessionMeta, SessionMessage, Order, Complaint, MemoryEntry } from './types'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  getCustomers: () => get<Customer[]>('/customers'),
  getProviders: () => get<ProvidersResponse>('/providers'),
  getSessions: () => get<SessionMeta[]>('/sessions'),
  getSession: (id: string) => get<SessionMessage[]>(`/sessions/${id}`),

  getOrders: (customerId?: number) =>
    get<Order[]>(customerId !== undefined ? `/orders?customer_id=${customerId}` : '/orders'),

  getComplaints: (customerId?: number) =>
    get<Complaint[]>(customerId !== undefined ? `/complaints?customer_id=${customerId}` : '/complaints'),

  getMemory: (customerId: number) => get<MemoryEntry[]>(`/memory/${customerId}`),

  updateMemory: (customerId: number, entries: { key: string; value: string }[]) =>
    put<{ updated: number }>(`/memory/${customerId}`, entries),

  deleteMemory: (customerId: number, key: string) =>
    del<{ deleted: boolean }>(`/memory/${customerId}/${encodeURIComponent(key)}`),
}
