import { describe, it, expect } from 'vitest'
import { appReducer, initialState } from '@/state/reducer'
import type { AppState } from '@/state/types'
import type { SseFrame } from '@/api/types'

const mockProviders = {
  openrouter: { available: true, models: ['gpt-4o', 'gemini'] },
  ollama: { available: true, models: ['qwen3:4b', 'llama3'] },
}

const stateWithProviders: AppState = {
  ...initialState,
  providers: mockProviders,
  activeProvider: 'openrouter',
  activeModel: 'gpt-4o',
  activeCustomerId: 1,
  activeThreadId: 'thread-abc',
  transcript: [{ role: 'human', content: 'hello' }],
  streamingToken: 'partial',
  isStreaming: true,
  currentTurnEvents: [{ event: 'planner_start', data: {} } as SseFrame],
}

describe('appReducer – CUSTOMER_CHANGED', () => {
  it('resets session state when customer changes', () => {
    const next = appReducer(stateWithProviders, { type: 'CUSTOMER_CHANGED', customerId: 2 })
    expect(next.activeCustomerId).toBe(2)
    expect(next.activeThreadId).toBeNull()
    expect(next.transcript).toHaveLength(0)
    expect(next.streamingToken).toBe('')
    expect(next.isStreaming).toBe(false)
    expect(next.currentTurnEvents).toHaveLength(0)
    expect(next.sessionMode).toBe('writable')
  })
})

describe('appReducer – PROVIDER_CHANGED', () => {
  it('resets session state on provider change', () => {
    const next = appReducer(stateWithProviders, { type: 'PROVIDER_CHANGED', provider: 'ollama' })
    expect(next.activeThreadId).toBeNull()
    expect(next.transcript).toHaveLength(0)
    expect(next.isStreaming).toBe(false)
  })

  it('keeps current model when it exists in new provider', () => {
    const state: AppState = { ...stateWithProviders, activeModel: 'qwen3:4b' }
    const next = appReducer(state, { type: 'PROVIDER_CHANGED', provider: 'ollama' })
    expect(next.activeModel).toBe('qwen3:4b')
  })

  it('auto-selects first model when current model not available in new provider', () => {
    const next = appReducer(stateWithProviders, { type: 'PROVIDER_CHANGED', provider: 'ollama' })
    expect(next.activeModel).toBe('qwen3:4b')
  })
})

describe('appReducer – SESSION_SELECTED', () => {
  it('sets readonly mode and populates transcript', () => {
    const messages = [
      { message_id: 1, role: 'human' as const, content: 'hi', created_at: '' },
      { message_id: 2, role: 'ai' as const, content: 'hello', created_at: '' },
    ]
    const next = appReducer(initialState, { type: 'SESSION_SELECTED', threadId: 't1', messages })
    expect(next.sessionMode).toBe('readonly')
    expect(next.activeThreadId).toBe('t1')
    expect(next.transcript).toHaveLength(2)
    expect(next.transcript[0]).toEqual({ role: 'human', content: 'hi' })
  })
})

describe('appReducer – NEW_CHAT', () => {
  it('returns to writable mode and clears transcript', () => {
    const readonly: AppState = {
      ...stateWithProviders,
      sessionMode: 'readonly',
      transcript: [{ role: 'ai', content: 'old' }],
    }
    const next = appReducer(readonly, { type: 'NEW_CHAT' })
    expect(next.sessionMode).toBe('writable')
    expect(next.activeThreadId).toBeNull()
    expect(next.transcript).toHaveLength(0)
    expect(next.currentTurnEvents).toHaveLength(0)
  })
})

describe('appReducer – SSE_EVENT', () => {
  it('accumulates response_token into streamingToken', () => {
    const s1 = appReducer(initialState, { type: 'SSE_EVENT', frame: { event: 'response_token', data: { token: 'Hel' } } })
    const s2 = appReducer(s1, { type: 'SSE_EVENT', frame: { event: 'response_token', data: { token: 'lo' } } })
    expect(s2.streamingToken).toBe('Hello')
  })

  it('finalizes transcript and sets threadId on response_end', () => {
    const withTokens: AppState = { ...initialState, streamingToken: 'Hello world', isStreaming: true }
    const next = appReducer(withTokens, {
      type: 'SSE_EVENT',
      frame: { event: 'response_end', data: { thread_id: 'new-thread', response: 'Hello world' } },
    })
    expect(next.transcript).toHaveLength(1)
    expect(next.transcript[0]).toEqual({ role: 'ai', content: 'Hello world' })
    expect(next.streamingToken).toBe('')
    expect(next.isStreaming).toBe(false)
    expect(next.activeThreadId).toBe('new-thread')
  })

  it('appends non-token events to currentTurnEvents', () => {
    const frame: SseFrame = { event: 'planner_start', data: { thread_id: 't1' } }
    const next = appReducer(initialState, { type: 'SSE_EVENT', frame })
    expect(next.currentTurnEvents).toHaveLength(1)
    expect(next.currentTurnEvents[0].event).toBe('planner_start')
  })
})

describe('appReducer – STREAM_ERROR', () => {
  it('marks stream as failed', () => {
    const streaming: AppState = { ...initialState, isStreaming: true }
    const next = appReducer(streaming, { type: 'STREAM_ERROR', error: 'timeout' })
    expect(next.isStreaming).toBe(false)
    expect(next.streamError).toBe('timeout')
  })
})
