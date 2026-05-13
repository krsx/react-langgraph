import { useEffect } from 'react'
import { useApp } from '@/state/context'
import { api } from '@/api/client'
import { CustomerPicker } from './CustomerPicker'
import { ProviderModelPicker } from './ProviderModelPicker'
import { SessionList } from './SessionList'

export function Sidebar() {
  const { dispatch } = useApp()

  useEffect(() => {
    api.getCustomers().then((c) => dispatch({ type: 'CUSTOMERS_LOADED', customers: c })).catch(() => {})
    api.getProviders().then((p) => dispatch({ type: 'PROVIDERS_LOADED', providers: p })).catch(() => {})
    api.getSessions().then((s) => dispatch({ type: 'SESSIONS_LOADED', sessions: s })).catch(() => {})
  }, [dispatch])

  return (
    <aside className="w-64 h-full bg-gray-50 border-r flex flex-col gap-4 p-4 overflow-y-auto">
      <h1 className="font-semibold text-sm text-gray-700">CS Agent</h1>
      <CustomerPicker />
      <ProviderModelPicker />
      <button
        onClick={() => dispatch({ type: 'NEW_CHAT' })}
        className="w-full py-1.5 px-3 rounded border border-gray-300 text-sm hover:bg-gray-100 text-left"
      >
        + New Chat
      </button>
      <div>
        <p className="text-xs font-medium text-gray-500 mb-1">Sessions</p>
        <SessionList />
      </div>
    </aside>
  )
}
