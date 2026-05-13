import { useState } from 'react'

interface Props {
  icon: string
  title: string
  badgeText?: string
  badgeClass?: string
  defaultExpanded?: boolean
  children: React.ReactNode
  detail?: unknown
}

export function ProcessCard({
  icon,
  title,
  badgeText,
  badgeClass = 'bg-gray-100 text-gray-700',
  defaultExpanded = false,
  children,
  detail,
}: Props) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div className="rounded border border-gray-200 bg-white text-xs overflow-hidden">
      <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-50 border-b border-gray-100">
        <span>{icon}</span>
        <span className="font-medium text-gray-700 flex-1">{title}</span>
        {badgeText && (
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${badgeClass}`}>
            {badgeText}
          </span>
        )}
        {detail !== undefined && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="ml-1 text-gray-400 hover:text-gray-600 w-4 text-center"
            aria-label={expanded ? 'Collapse detail' : 'Expand detail'}
          >
            {expanded ? '▲' : '▼'}
          </button>
        )}
      </div>
      <div className="px-3 py-2 text-gray-700">{children}</div>
      {expanded && detail !== undefined && (
        <pre className="text-[10px] bg-gray-50 border-t border-gray-100 p-2 overflow-auto max-h-48 text-gray-600">
          {JSON.stringify(detail, null, 2)}
        </pre>
      )}
    </div>
  )
}
