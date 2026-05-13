import type { Customer, ProvidersResponse, SessionMeta, SessionMessage, SseFrame } from '@/api/types'

export type SessionMode = 'writable' | 'readonly'

export interface TranscriptEntry {
  role: 'human' | 'ai'
  content: string
}

export interface AppState {
  customers: Customer[]
  activeCustomerId: number | null
  providers: ProvidersResponse | null
  activeProvider: 'openrouter' | 'ollama'
  activeModel: string | null
  sessions: SessionMeta[]
  activeThreadId: string | null
  sessionMode: SessionMode
  transcript: TranscriptEntry[]
  streamingToken: string
  isStreaming: boolean
  streamError: string | null
  currentTurnEvents: SseFrame[]
}

export type Action =
  | { type: 'CUSTOMERS_LOADED'; customers: Customer[] }
  | { type: 'PROVIDERS_LOADED'; providers: ProvidersResponse }
  | { type: 'SESSIONS_LOADED'; sessions: SessionMeta[] }
  | { type: 'CUSTOMER_CHANGED'; customerId: number }
  | { type: 'PROVIDER_CHANGED'; provider: 'openrouter' | 'ollama' }
  | { type: 'MODEL_CHANGED'; model: string }
  | { type: 'SESSION_SELECTED'; threadId: string; messages: SessionMessage[] }
  | { type: 'NEW_CHAT' }
  | { type: 'SEND_MESSAGE'; content: string }
  | { type: 'SSE_EVENT'; frame: SseFrame }
  | { type: 'STREAM_ERROR'; error: string }
