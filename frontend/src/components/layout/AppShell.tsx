import { useState } from 'react'
import { AppProvider } from '@/state/context'
import { Sidebar } from '@/components/sidebar/Sidebar'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { RightPanelShell } from './RightPanelShell'

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
        />
      </div>
    </AppProvider>
  )
}
