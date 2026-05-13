import { useApp } from '@/state/context'

export function ExecutionContextCard() {
  const { state } = useApp()
  const customer = state.customers.find((c) => c.customer_id === state.activeCustomerId)

  return (
    <div className="rounded border border-gray-200 p-3 bg-gray-50 text-xs">
      <div className="font-medium text-gray-600 mb-2 flex items-center gap-1">ℹ Execution Context</div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-gray-700">
        <dt className="text-gray-500">Customer</dt>
        <dd>{customer?.name ?? '—'}</dd>
        <dt className="text-gray-500">Provider</dt>
        <dd>{state.activeProvider}</dd>
        <dt className="text-gray-500">Model</dt>
        <dd className="truncate">{state.activeModel ? state.activeModel.slice(0, 30) : '—'}</dd>
        <dt className="text-gray-500">Thread</dt>
        <dd className="font-mono truncate">{state.activeThreadId ?? '—'}</dd>
      </dl>
    </div>
  )
}
