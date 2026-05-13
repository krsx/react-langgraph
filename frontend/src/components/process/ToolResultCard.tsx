import { ProcessCard } from './ProcessCard'

interface Props {
  data: Record<string, unknown>
  isStart?: boolean
}

export function ToolResultCard({ data, isStart = false }: Props) {
  if (isStart) {
    return (
      <ProcessCard icon="⚙" title="Tools" badgeText="calling" badgeClass="bg-orange-100 text-orange-700">
        <span className="text-gray-500 italic">Calling tools…</span>
      </ProcessCard>
    )
  }

  const results = String(data.results ?? '')

  return (
    <ProcessCard
      icon="⚙"
      title="Tool Result"
      badgeText="tool"
      badgeClass="bg-orange-100 text-orange-700"
      detail={data}
    >
      <p className="font-mono text-gray-600 line-clamp-2">{results.slice(0, 80)}{results.length > 80 ? '…' : ''}</p>
    </ProcessCard>
  )
}
