import { ProcessCard } from './ProcessCard'

interface ToolCall {
  name: string
  args: Record<string, unknown>
}

interface Props {
  data: Record<string, unknown>
  isStart?: boolean
}

export function PlannerCard({ data, isStart = false }: Props) {
  if (isStart) {
    return (
      <ProcessCard icon="💭" title="Planner" badgeText="thinking" badgeClass="bg-blue-100 text-blue-700">
        <span className="text-gray-500 italic">Thinking…</span>
      </ProcessCard>
    )
  }

  const content = (data.content as string | undefined) ?? ''
  const toolCalls = (data.tool_calls as ToolCall[] | undefined) ?? []

  return (
    <ProcessCard
      icon="💭"
      title="Planner"
      badgeText="planner"
      badgeClass="bg-blue-100 text-blue-700"
      detail={data}
    >
      <div className="flex flex-col gap-1">
        <p className="text-gray-700 line-clamp-3">{content.slice(0, 120)}{content.length > 120 ? '…' : ''}</p>
        {toolCalls.length > 0 && (
          <ul className="mt-1 flex flex-col gap-0.5">
            {toolCalls.map((tc, i) => (
              <li key={i} className="font-mono text-[10px] text-orange-700 bg-orange-50 px-2 py-0.5 rounded">
                → {tc.name}({JSON.stringify(tc.args)})
              </li>
            ))}
          </ul>
        )}
      </div>
    </ProcessCard>
  )
}
