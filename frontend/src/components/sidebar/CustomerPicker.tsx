import { useApp } from '@/state/context'

export function CustomerPicker() {
  const { state, dispatch, dirtyGuardRef } = useApp()

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const customerId = Number(e.target.value)
    if (!customerId) return
    if (dirtyGuardRef.current && !dirtyGuardRef.current()) return
    dispatch({ type: 'CUSTOMER_CHANGED', customerId })
  }

  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1">Customer</label>
      <select
        data-testid="customer-select"
        className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        value={state.activeCustomerId ?? ''}
        onChange={handleChange}
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
