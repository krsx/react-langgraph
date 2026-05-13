import { useState, useEffect, useCallback } from 'react'
import { useApp } from '@/state/context'
import { api } from '@/api/client'
import type { MemoryEntry } from '@/api/types'
import { MemoryRow } from './MemoryRow'

export function MemoryManagerPanel() {
  const { state, dirtyGuardRef } = useApp()
  const { activeCustomerId } = state

  const [entries, setEntries] = useState<MemoryEntry[]>([])
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [adding, setAdding] = useState(false)
  const [newKey, setNewKey] = useState('')
  const [newValue, setNewValue] = useState('')

  const fetchEntries = useCallback(() => {
    if (activeCustomerId === null) return
    api.getMemory(activeCustomerId).then(setEntries).catch(() => {})
  }, [activeCustomerId])

  useEffect(() => {
    setEditingKey(null)
    setAdding(false)
    fetchEntries()
  }, [fetchEntries])

  // Register dirty guard while a row is being edited
  useEffect(() => {
    if (editingKey !== null) {
      dirtyGuardRef.current = () =>
        window.confirm('You have unsaved edits. Switch customer and discard changes?')
    } else {
      dirtyGuardRef.current = null
    }
    return () => { dirtyGuardRef.current = null }
  }, [editingKey, dirtyGuardRef])

  if (activeCustomerId === null) {
    return (
      <div className="flex items-center justify-center h-full text-xs text-gray-400">
        Select a customer to manage memory.
      </div>
    )
  }

  function startEdit(entry: MemoryEntry) {
    setEditingKey(entry.key)
    setEditValue(entry.value)
    setAdding(false)
  }

  function cancelEdit() {
    setEditingKey(null)
    setEditValue('')
  }

  async function saveEdit() {
    if (!editingKey) return
    await api.updateMemory(activeCustomerId!, [{ key: editingKey, value: editValue }])
    setEditingKey(null)
    setEditValue('')
    fetchEntries()
  }

  async function deleteEntry(key: string) {
    if (!window.confirm(`Delete key "${key}"?`)) return
    await api.deleteMemory(activeCustomerId!, key)
    fetchEntries()
  }

  async function addEntry() {
    if (!newKey.trim()) return
    await api.updateMemory(activeCustomerId!, [{ key: newKey.trim(), value: newValue }])
    setNewKey('')
    setNewValue('')
    setAdding(false)
    fetchEntries()
  }

  return (
    <div className="flex flex-col h-full overflow-hidden text-xs">
      <div className="flex items-center justify-between px-3 py-2 border-b shrink-0">
        <span className="font-medium text-gray-600">
          {state.customers.find((c) => c.customer_id === activeCustomerId)?.name ?? `Customer ${activeCustomerId}`}
        </span>
        <button
          onClick={() => { setAdding((v) => !v); setEditingKey(null) }}
          className="px-2 py-0.5 bg-blue-500 text-white rounded text-[10px] hover:bg-blue-600"
        >
          + Add Entry
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        <table className="w-full">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-2 py-1.5 text-left font-medium text-gray-600 border-b">Key</th>
              <th className="px-2 py-1.5 text-left font-medium text-gray-600 border-b">Value</th>
              <th className="px-2 py-1.5 border-b" />
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <MemoryRow
                key={entry.key}
                entry={entry}
                isEditing={editingKey === entry.key}
                editValue={editValue}
                onEdit={() => startEdit(entry)}
                onSave={() => void saveEdit()}
                onCancel={cancelEdit}
                onEditValueChange={setEditValue}
                onDelete={() => void deleteEntry(entry.key)}
              />
            ))}
          </tbody>
        </table>

        {entries.length === 0 && (
          <p className="text-center text-gray-400 py-8">No memory entries for this customer.</p>
        )}

        {adding && (
          <div className="p-3 border-t flex flex-col gap-2">
            <input
              className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              placeholder="Key"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
            />
            <input
              className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
              placeholder="Value"
              value={newValue}
              onChange={(e) => setNewValue(e.target.value)}
            />
            <button
              onClick={() => void addEntry()}
              disabled={!newKey.trim()}
              className="px-3 py-1 bg-blue-500 text-white rounded text-xs hover:bg-blue-600 disabled:opacity-50"
            >
              Add
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
