import { useApp } from '@/state/context'
import { MessageList } from './MessageList'
import { MessageComposer } from './MessageComposer'

export function ChatPanel() {
  const { state } = useApp()

  return (
    <div className="flex flex-col flex-1 min-w-0 h-full">
      {state.sessionMode === 'readonly' && (
        <div className="px-4 py-2 bg-yellow-50 border-b text-sm text-yellow-700">
          Read-only — viewing past session. Click <strong>New Chat</strong> to start a new conversation.
        </div>
      )}
      {state.streamError && (
        <div className="px-4 py-2 bg-red-50 border-b text-sm text-red-700">
          Error: {state.streamError}
        </div>
      )}
      <MessageList
        transcript={state.transcript}
        streamingToken={state.streamingToken}
        isStreaming={state.isStreaming}
      />
      <MessageComposer />
    </div>
  )
}
