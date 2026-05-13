import { useRef, useState, type KeyboardEvent } from 'react'
import { useApp } from '@/state/context'
import { streamChat } from '@/api/sse'

export function MessageComposer() {
  const { state, dispatch } = useApp()
  const [text, setText] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  const disabled =
    !state.activeCustomerId || state.sessionMode === 'readonly' || state.isStreaming

  async function send() {
    const content = text.trim()
    if (!content || disabled) return
    setText('')
    dispatch({ type: 'SEND_MESSAGE', content })

    abortRef.current = new AbortController()
    try {
      for await (const frame of streamChat(
        {
          message: content,
          customer_id: state.activeCustomerId!,
          thread_id: state.activeThreadId ?? undefined,
          provider: state.activeProvider,
          model: state.activeModel ?? undefined,
        },
        abortRef.current.signal
      )) {
        dispatch({ type: 'SSE_EVENT', frame })
      }
    } catch (err) {
      dispatch({ type: 'STREAM_ERROR', error: String(err) })
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void send()
    }
  }

  return (
    <div className="flex gap-2 p-4 border-t">
      <textarea
        className="flex-1 resize-none rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-50"
        rows={1}
        placeholder="Type a message… (Enter to send, Shift+Enter for newline)"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      <button
        onClick={() => void send()}
        disabled={disabled || !text.trim()}
        className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Send
      </button>
    </div>
  )
}
