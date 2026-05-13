interface Props {
  isCollapsed: boolean
  onToggle: () => void
  children?: React.ReactNode
}

export function RightPanelShell({ isCollapsed, onToggle, children }: Props) {
  return (
    <div className="flex h-full">
      <button
        onClick={onToggle}
        className="flex items-center justify-center w-6 border-l bg-gray-50 hover:bg-gray-100 text-gray-500 text-xs shrink-0"
        title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
      >
        {isCollapsed ? '►' : '◄'}
      </button>
      {!isCollapsed && (
        <div className="w-80 flex flex-col h-full border-l overflow-hidden">
          {children}
        </div>
      )}
    </div>
  )
}
