import { useApp } from '@/state/context'
import { api } from '@/api/client'

export function SessionList() {
  const { state, dispatch } = useApp()

  const filtered = state.sessions.filter(
    (s) => state.activeCustomerId === null || s.customer_id === state.activeCustomerId
  )

  async function selectSession(threadId: string) {
    try {
      const messages = await api.getSession(threadId)
      dispatch({ type: 'SESSION_SELECTED', threadId, messages })
    } catch {
      // session not found — ignore
    }
  }

  if (filtered.length === 0) {
    return <p className="text-xs text-gray-400 mt-2">No sessions yet.</p>
  }

  return (
    <ul className="flex flex-col gap-1 mt-2">
      {filtered.map((s) => (
        <li key={s.thread_id}>
          <button
            className={`w-full text-left px-2 py-1.5 rounded text-xs truncate hover:bg-gray-200 ${
              state.activeThreadId === s.thread_id ? 'bg-gray-200 font-medium' : ''
            }`}
            onClick={() => void selectSession(s.thread_id)}
          >
            {s.first_message}
          </button>
        </li>
      ))}
    </ul>
  )
}
