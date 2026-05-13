interface Props {
  isCollapsed: boolean
  onToggle: () => void
}

export function RightPanelShell({ isCollapsed, onToggle }: Props) {
  return (
    <div className="flex h-full">
      <button
        onClick={onToggle}
        className="flex items-center justify-center w-6 border-l bg-gray-50 hover:bg-gray-100 text-gray-500 text-xs"
        title={isCollapsed ? 'Expand panel' : 'Collapse panel'}
      >
        {isCollapsed ? '►' : '◄'}
      </button>
      {!isCollapsed && (
        <div className="w-80 flex flex-col items-center justify-center h-full text-gray-400 text-sm border-l">
          <span>Agent Process — coming in #13</span>
        </div>
      )}
    </div>
  )
}
