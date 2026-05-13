import { useState, useEffect, useCallback } from 'react'
import { useApp } from '@/state/context'
import { api } from '@/api/client'
import type { Customer, Order, Complaint } from '@/api/types'

type SubTab = 'customers' | 'orders' | 'complaints'

function DataTable<T>({
  columns,
  rows,
  renderRow,
}: {
  columns: string[]
  rows: T[]
  renderRow: (row: T, i: number) => React.ReactNode
}) {
  return (
    <div className="overflow-auto h-full">
      <table className="w-full text-xs">
        <thead className="bg-gray-50 sticky top-0">
          <tr>
            {columns.map((col) => (
              <th key={col} className="px-2 py-1.5 text-left font-medium text-gray-600 border-b">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
              {renderRow(row, i)}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length === 0 && (
        <p className="text-center text-gray-400 py-8 text-xs">No data.</p>
      )}
    </div>
  )
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  processing: 'bg-blue-100 text-blue-700',
  delivered: 'bg-green-100 text-green-700',
  refund_requested: 'bg-red-100 text-red-700',
  resolved: 'bg-green-100 text-green-700',
  closed: 'bg-gray-100 text-gray-600',
  open: 'bg-orange-100 text-orange-700',
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${STATUS_COLORS[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

export function DataExplorerPanel() {
  const { state } = useApp()
  const { activeCustomerId } = state

  const [subTab, setSubTab] = useState<SubTab>('customers')
  const [customers, setCustomers] = useState<Customer[]>([])
  const [orders, setOrders] = useState<Order[]>([])
  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [tick, setTick] = useState(0)

  const fetchAll = useCallback(() => {
    api.getCustomers().then(setCustomers).catch(() => {})
    api.getOrders(activeCustomerId ?? undefined).then(setOrders).catch(() => {})
    api.getComplaints(activeCustomerId ?? undefined).then(setComplaints).catch(() => {})
  }, [activeCustomerId])

  useEffect(() => { fetchAll() }, [fetchAll, tick])

  const SUB_TABS: SubTab[] = ['customers', 'orders', 'complaints']

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex items-center border-b px-2 shrink-0">
        {SUB_TABS.map((t) => (
          <button
            key={t}
            onClick={() => setSubTab(t)}
            className={`px-3 py-1.5 text-xs font-medium capitalize ${
              subTab === t ? 'border-b-2 border-blue-500 text-blue-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
          </button>
        ))}
        <button
          onClick={() => setTick((n) => n + 1)}
          className="ml-auto px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
          title="Refresh"
          aria-label="Refresh"
        >
          ↻
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        {subTab === 'customers' && (
          <DataTable
            columns={['ID', 'Name', 'Email', 'Created']}
            rows={customers}
            renderRow={(c) => (
              <>
                <td className="px-2 py-1">{c.customer_id}</td>
                <td className="px-2 py-1">{c.name}</td>
                <td className="px-2 py-1">{c.email}</td>
                <td className="px-2 py-1">{c.created_at.slice(0, 10)}</td>
              </>
            )}
          />
        )}
        {subTab === 'orders' && (
          <DataTable
            columns={['ID', 'Product', 'Status', 'Order Date', 'Delivery']}
            rows={orders}
            renderRow={(o) => (
              <>
                <td className="px-2 py-1">{o.order_id}</td>
                <td className="px-2 py-1">{o.product_name}</td>
                <td className="px-2 py-1"><StatusBadge status={o.status} /></td>
                <td className="px-2 py-1">{o.order_date.slice(0, 10)}</td>
                <td className="px-2 py-1">{o.delivery_date?.slice(0, 10) ?? '—'}</td>
              </>
            )}
          />
        )}
        {subTab === 'complaints' && (
          <DataTable
            columns={['ID', 'Order', 'Issue', 'Status', 'Created']}
            rows={complaints}
            renderRow={(c) => (
              <>
                <td className="px-2 py-1">{c.complaint_id}</td>
                <td className="px-2 py-1">{c.order_id}</td>
                <td className="px-2 py-1 max-w-[120px] truncate">{c.issue}</td>
                <td className="px-2 py-1"><StatusBadge status={c.status} /></td>
                <td className="px-2 py-1">{c.created_at.slice(0, 10)}</td>
              </>
            )}
          />
        )}
      </div>
    </div>
  )
}
