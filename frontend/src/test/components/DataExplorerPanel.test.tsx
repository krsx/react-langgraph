import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppProvider, useApp } from '@/state/context'
import { DataExplorerPanel } from '@/components/data/DataExplorerPanel'
import { useEffect } from 'react'
import type { Action } from '@/state/types'

function renderWithActions(actions: Action[] = []) {
  function Primer() {
    const { dispatch } = useApp()
    useEffect(() => { actions.forEach((a) => dispatch(a)) }, [dispatch])
    return null
  }
  return render(
    <AppProvider>
      <Primer />
      <DataExplorerPanel />
    </AppProvider>
  )
}

describe('DataExplorerPanel – Customers tab', () => {
  it('loads all customers regardless of active customer selection', async () => {
    renderWithActions()
    await waitFor(() => expect(screen.getByText('Ahmad Rifqi')).toBeInTheDocument())
    expect(screen.getByText('Jane Doe')).toBeInTheDocument()
  })
})

describe('DataExplorerPanel – Orders tab', () => {
  it('shows only active customer orders after switching to Orders tab', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await user.click(screen.getByRole('button', { name: /orders/i }))
    await waitFor(() => expect(screen.getByText('Wireless Headphones')).toBeInTheDocument())
    expect(screen.queryByText('Other Product')).not.toBeInTheDocument()
  })
})

describe('DataExplorerPanel – Complaints tab', () => {
  it('shows only active customer complaints after switching to Complaints tab', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await user.click(screen.getByRole('button', { name: /complaints/i }))
    await waitFor(() => expect(screen.getByText('Package arrived late')).toBeInTheDocument())
  })
})

describe('DataExplorerPanel – Refresh', () => {
  it('refresh button triggers data refetch', async () => {
    const user = userEvent.setup()
    renderWithActions()
    await waitFor(() => expect(screen.getByText('Ahmad Rifqi')).toBeInTheDocument())
    const refreshBtn = screen.getByRole('button', { name: /refresh/i })
    await user.click(refreshBtn)
    await waitFor(() => expect(screen.getByText('Ahmad Rifqi')).toBeInTheDocument())
  })
})

describe('DataExplorerPanel – Empty state', () => {
  it('shows empty state message when complaints table has no rows for customer 2', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 2 }])
    await user.click(screen.getByRole('button', { name: /complaints/i }))
    await waitFor(() => expect(screen.getByText(/no data/i)).toBeInTheDocument())
  })
})
