import type { Customer, ProvidersResponse, SessionMeta, SessionMessage } from './types'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`/api${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  getCustomers: () => get<Customer[]>('/customers'),
  getProviders: () => get<ProvidersResponse>('/providers'),
  getSessions: () => get<SessionMeta[]>('/sessions'),
  getSession: (id: string) => get<SessionMessage[]>(`/sessions/${id}`),
}
