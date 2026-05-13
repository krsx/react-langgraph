export interface Customer {
  customer_id: number
  name: string
  email: string
  created_at: string
}

export interface ProviderInfo {
  available: boolean
  models: string[]
}

export interface ProvidersResponse {
  openrouter: ProviderInfo
  ollama: ProviderInfo
}

export interface SessionMeta {
  thread_id: string
  customer_id: number
  created_at: string
  first_message: string
}

export interface SessionMessage {
  message_id: number
  role: 'human' | 'ai'
  content: string
  created_at: string
}

export type SseEventName =
  | 'memory_loaded'
  | 'planner_start'
  | 'planner_result'
  | 'tool_start'
  | 'tool_result'
  | 'verifier_result'
  | 'memory_updated'
  | 'response_token'
  | 'response_end'
  | 'error'

export interface SseFrame {
  event: SseEventName
  data: Record<string, unknown>
}

export interface Order {
  order_id: number
  customer_id: number
  product_name: string
  status: string
  order_date: string
  delivery_date: string | null
}

export interface Complaint {
  complaint_id: number
  customer_id: number
  order_id: number
  issue: string
  status: string
  created_at: string
}

export interface MemoryEntry {
  key: string
  value: string
  created_at: string
}
