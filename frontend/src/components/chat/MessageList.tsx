import { useEffect, useRef } from 'react'
import { MessageBubble } from './MessageBubble'
import type { TranscriptEntry } from '@/state/types'

interface Props {
  transcript: TranscriptEntry[]
  streamingToken: string
  isStreaming: boolean
}

export function MessageList({ transcript, streamingToken, isStreaming }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, streamingToken])

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {transcript.map((entry, i) => (
        <MessageBubble key={i} role={entry.role} content={entry.content} />
      ))}
      {isStreaming && streamingToken && (
        <MessageBubble role="ai" content={streamingToken} streaming />
      )}
      <div ref={bottomRef} />
    </div>
  )
}
