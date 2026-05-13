import { useApp } from '@/state/context'
import type { SseFrame } from '@/api/types'
import { ExecutionContextCard } from './ExecutionContextCard'
import { MemoryLoadedCard } from './MemoryLoadedCard'
import { PlannerCard } from './PlannerCard'
import { ToolResultCard } from './ToolResultCard'
import { VerifierCard } from './VerifierCard'
import { MemoryUpdatedCard } from './MemoryUpdatedCard'
import { ProcessCard } from './ProcessCard'

function EventCard({ frame }: { frame: SseFrame }) {
  switch (frame.event) {
    case 'memory_loaded':
      return <MemoryLoadedCard data={frame.data} />
    case 'planner_start':
      return <PlannerCard data={frame.data} isStart />
    case 'planner_result':
      return <PlannerCard data={frame.data} />
    case 'tool_start':
      return <ToolResultCard data={frame.data} isStart />
    case 'tool_result':
      return <ToolResultCard data={frame.data} />
    case 'verifier_result':
      return <VerifierCard data={frame.data} />
    case 'memory_updated':
      return <MemoryUpdatedCard />
    default:
      return (
        <ProcessCard icon="·" title={frame.event} detail={frame.data}>
          <span className="text-gray-500 font-mono">{frame.event}</span>
        </ProcessCard>
      )
  }
}

export function AgentProcessPanel() {
  const { state } = useApp()
  const events = state.currentTurnEvents

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-3 py-2 border-b text-xs font-semibold text-gray-500 uppercase tracking-wide shrink-0">
        Agent Process
      </div>
      <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2">
        <ExecutionContextCard />
        {events.map((frame, i) => (
          <EventCard key={i} frame={frame} />
        ))}
        {events.length === 0 && !state.isStreaming && (
          <p className="text-xs text-gray-400 text-center mt-8">
            Send a message to see agent steps.
          </p>
        )}
      </div>
    </div>
  )
}
