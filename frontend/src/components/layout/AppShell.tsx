import { useState } from 'react'
import { AppProvider } from '@/state/context'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { RightPanelShell } from './RightPanelShell'
import { RightPanelContent } from './RightPanelContent'

export function AppShell() {
  const [rightCollapsed, setRightCollapsed] = useState(false)

  return (
    <AppProvider>
      <div className="flex h-screen overflow-hidden bg-white">
        <Sidebar />
        <ChatPanel />
        <RightPanelShell
          isCollapsed={rightCollapsed}
          onToggle={() => setRightCollapsed((v) => !v)}
        >
          <RightPanelContent />
        </RightPanelShell>
      </div>
    </AppProvider>
  )
}
