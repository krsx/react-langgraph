interface Props {
  role: 'human' | 'ai'
  content: string
  streaming?: boolean
}

export function MessageBubble({ role, content, streaming = false }: Props) {
  const isHuman = role === 'human'
  return (
    <div className={`flex ${isHuman ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={
          isHuman
            ? 'bg-blue-500 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[75%]'
            : 'bg-gray-100 text-gray-900 rounded-2xl rounded-bl-sm px-4 py-2 max-w-[75%]'
        }
      >
        {content}
        {streaming && <span className="animate-pulse">▋</span>}
      </div>
    </div>
  )
}
