import { ProcessCard } from './ProcessCard'

export function MemoryUpdatedCard() {
  return (
    <ProcessCard icon="💾" title="Memory Updated" badgeText="memory" badgeClass="bg-purple-100 text-purple-700">
      <span className="text-gray-500">Memory updated for this turn.</span>
    </ProcessCard>
  )
}
