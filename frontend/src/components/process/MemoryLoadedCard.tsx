import { ProcessCard } from './ProcessCard'

interface Props {
  data: Record<string, unknown>
}

export function MemoryLoadedCard({ data }: Props) {
  const entries = (data.memory_context as unknown[]) ?? []
  return (
    <ProcessCard
      icon="🧠"
      title="Memory Loaded"
      badgeText="memory"
      badgeClass="bg-purple-100 text-purple-700"
      detail={data}
    >
      <span>{entries.length} entries loaded</span>
    </ProcessCard>
  )
}
