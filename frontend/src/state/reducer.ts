import type { AppState, Action } from './types'

const SESSION_RESET = {
  activeThreadId: null,
  transcript: [] as AppState['transcript'],
  streamingToken: '',
  isStreaming: false,
  streamError: null,
  currentTurnEvents: [] as AppState['currentTurnEvents'],
  sessionMode: 'writable' as const,
}

export const initialState: AppState = {
  customers: [],
  activeCustomerId: null,
  providers: null,
  activeProvider: 'openrouter',
  activeModel: null,
  sessions: [],
  ...SESSION_RESET,
}

export function appReducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'CUSTOMERS_LOADED':
      return { ...state, customers: action.customers }

    case 'PROVIDERS_LOADED':
      return { ...state, providers: action.providers }

    case 'SESSIONS_LOADED':
      return { ...state, sessions: action.sessions }

    case 'CUSTOMER_CHANGED':
      return { ...state, activeCustomerId: action.customerId, ...SESSION_RESET }

    case 'PROVIDER_CHANGED': {
      const providerModels = state.providers?.[action.provider]?.models ?? []
      const modelStillValid = state.activeModel !== null && providerModels.includes(state.activeModel)
      return {
        ...state,
        activeProvider: action.provider,
        activeModel: modelStillValid ? state.activeModel : (providerModels[0] ?? null),
        ...SESSION_RESET,
      }
    }

    case 'MODEL_CHANGED':
      return { ...state, activeModel: action.model, ...SESSION_RESET }

    case 'SESSION_SELECTED':
      return {
        ...state,
        sessionMode: 'readonly',
        activeThreadId: action.threadId,
        transcript: action.messages.map((m) => ({ role: m.role, content: m.content })),
        streamingToken: '',
        isStreaming: false,
        streamError: null,
        currentTurnEvents: [],
      }

    case 'NEW_CHAT':
      return {
        ...state,
        sessionMode: 'writable',
        activeThreadId: null,
        transcript: [],
        streamingToken: '',
        isStreaming: false,
        streamError: null,
        currentTurnEvents: [],
      }

    case 'SEND_MESSAGE':
      return {
        ...state,
        transcript: [...state.transcript, { role: 'human', content: action.content }],
        isStreaming: true,
        streamError: null,
        currentTurnEvents: [],
      }

    case 'SSE_EVENT': {
      const { frame } = action
      if (frame.event === 'response_token') {
        return { ...state, streamingToken: state.streamingToken + (frame.data.token as string) }
      }
      if (frame.event === 'response_end') {
        const threadId = (frame.data.thread_id as string | undefined) ?? state.activeThreadId
        return {
          ...state,
          transcript: [
            ...state.transcript,
            { role: 'ai', content: frame.data.response as string },
          ],
          streamingToken: '',
          isStreaming: false,
          activeThreadId: state.activeThreadId ?? threadId,
        }
      }
      return { ...state, currentTurnEvents: [...state.currentTurnEvents, frame] }
    }

    case 'STREAM_ERROR':
      return { ...state, isStreaming: false, streamError: action.error }

    default:
      return state
  }
}
