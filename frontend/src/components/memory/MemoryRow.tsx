import type { MemoryEntry } from '@/api/types'

interface Props {
  entry: MemoryEntry
  isEditing: boolean
  editValue: string
  onEdit: () => void
  onSave: () => void
  onCancel: () => void
  onEditValueChange: (v: string) => void
  onDelete: () => void
}

export function MemoryRow({
  entry,
  isEditing,
  editValue,
  onEdit,
  onSave,
  onCancel,
  onEditValueChange,
  onDelete,
}: Props) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50">
      <td className="px-2 py-1.5 font-mono text-xs text-gray-700 align-top">{entry.key}</td>
      <td className="px-2 py-1.5 text-xs text-gray-600 align-top">
        {isEditing ? (
          <input
            className="w-full border border-gray-300 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={editValue}
            onChange={(e) => onEditValueChange(e.target.value)}
          />
        ) : (
          <span className="line-clamp-2">{entry.value}</span>
        )}
      </td>
      <td className="px-2 py-1.5 text-xs whitespace-nowrap align-top">
        {isEditing ? (
          <div className="flex gap-1">
            <button
              onClick={onSave}
              className="px-2 py-0.5 bg-blue-500 text-white rounded text-[10px] hover:bg-blue-600"
            >
              Save
            </button>
            <button
              onClick={onCancel}
              className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded text-[10px] hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="flex gap-1">
            <button
              onClick={onEdit}
              className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-[10px] hover:bg-gray-200"
            >
              Edit
            </button>
            <button
              onClick={onDelete}
              className="px-2 py-0.5 bg-red-50 text-red-600 rounded text-[10px] hover:bg-red-100"
            >
              Delete
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}
