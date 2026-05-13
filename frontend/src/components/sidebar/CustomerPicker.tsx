import { useApp } from '@/state/context'

export function CustomerPicker() {
  const { state, dispatch } = useApp()

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">Customer</label>
      <select
        data-testid="customer-select"
        className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        value={state.activeCustomerId ?? ''}
        onChange={(e) =>
          e.target.value && dispatch({ type: 'CUSTOMER_CHANGED', customerId: Number(e.target.value) })
        }
      >
        <option value="">Select customer…</option>
        {state.customers.map((c) => (
          <option key={c.customer_id} value={c.customer_id}>
            {c.name}
          </option>
        ))}
      </select>
    </div>
  )
}
