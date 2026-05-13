import { useState } from 'react'
import { AgentProcessPanel } from '@/components/process/AgentProcessPanel'
import { DataExplorerPanel } from '@/components/data/DataExplorerPanel'
import { MemoryManagerPanel } from '@/components/memory/MemoryManagerPanel'

type Tab = 'process' | 'data' | 'memory'

const TABS: { value: Tab; label: string }[] = [
  { value: 'process', label: 'Agent Process' },
  { value: 'data', label: 'Data' },
  { value: 'memory', label: 'Memory' },
]

export function RightPanelContent() {
  const [activeTab, setActiveTab] = useState<Tab>('process')

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex border-b shrink-0" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            role="tab"
            aria-selected={activeTab === tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`flex-1 py-1.5 text-xs font-medium ${
              activeTab === tab.value
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {activeTab === 'process' && <AgentProcessPanel />}
        {activeTab === 'data' && <DataExplorerPanel />}
        {activeTab === 'memory' && <MemoryManagerPanel />}
      </div>
    </div>
  )
}
