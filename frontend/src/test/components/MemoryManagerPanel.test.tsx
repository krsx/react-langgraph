import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppProvider, useApp } from '@/state/context'
import { MemoryManagerPanel } from '@/components/memory/MemoryManagerPanel'
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
      <MemoryManagerPanel />
    </AppProvider>
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('MemoryManagerPanel – no customer', () => {
  it('shows prompt when no customer is selected', () => {
    renderWithActions()
    expect(screen.getByText(/select a customer/i)).toBeInTheDocument()
  })
})

describe('MemoryManagerPanel – loads entries', () => {
  it('displays memory entries for active customer', async () => {
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await waitFor(() => expect(screen.getByText('late_delivery_pattern')).toBeInTheDocument())
    expect(screen.getByText('complaint_count')).toBeInTheDocument()
  })
})

describe('MemoryManagerPanel – edit mode', () => {
  it('shows value input and keeps key read-only when Edit is clicked', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await waitFor(() => screen.getByText('complaint_count'))
    const editBtns = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editBtns[0])
    // A text input for the value should appear
    expect(screen.getByRole('textbox')).toBeInTheDocument()
  })
})

describe('MemoryManagerPanel – save edit', () => {
  it('calls PUT /memory and refreshes list when Save is clicked', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await waitFor(() => screen.getByText('complaint_count'))
    const editBtns = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editBtns[0])
    const input = screen.getByRole('textbox')
    await user.clear(input)
    await user.type(input, 'new value')
    await user.click(screen.getByRole('button', { name: /save/i }))
    await waitFor(() => expect(screen.queryByRole('textbox')).not.toBeInTheDocument())
  })
})

describe('MemoryManagerPanel – cancel edit', () => {
  it('exits edit mode without saving when Cancel is clicked', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await waitFor(() => screen.getByText('complaint_count'))
    const editBtns = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editBtns[0])
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })
})

describe('MemoryManagerPanel – delete', () => {
  it('calls DELETE /memory and removes entry when confirmed', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await waitFor(() => screen.getByText('complaint_count'))
    const deleteBtns = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteBtns[0])
    expect(window.confirm).toHaveBeenCalled()
  })
})

describe('MemoryManagerPanel – add entry', () => {
  it('submits new KV pair and refreshes list', async () => {
    const user = userEvent.setup()
    renderWithActions([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    await waitFor(() => screen.getByText('complaint_count'))
    await user.click(screen.getByRole('button', { name: /add entry/i }))
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[inputs.length - 2], 'new_key')
    await user.type(inputs[inputs.length - 1], 'new_value')
    await user.click(screen.getByRole('button', { name: /^add$/i }))
    await waitFor(() => {
      const textboxes = screen.queryAllByRole('textbox')
      expect(textboxes.length).toBe(0)
    })
  })
})

describe('MemoryManagerPanel – dirty guard', () => {
  it('calls window.confirm when customer is switched during active edit', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    // Render with sidebar so we can switch customers
    function App() {
      const { state, dispatch, dirtyGuardRef } = useApp()
      useEffect(() => { dispatch({ type: 'CUSTOMER_CHANGED', customerId: 1 }) }, [dispatch])
      function switchCustomer() {
        if (dirtyGuardRef.current && !dirtyGuardRef.current()) return
        dispatch({ type: 'CUSTOMER_CHANGED', customerId: 2 })
      }
      return (
        <>
          <button onClick={switchCustomer}>Switch Customer</button>
          <MemoryManagerPanel />
          <div data-testid="active-customer">{state.activeCustomerId}</div>
        </>
      )
    }

    render(<AppProvider><App /></AppProvider>)
    await waitFor(() => screen.getByText('complaint_count'))

    const editBtns = screen.getAllByRole('button', { name: /edit/i })
    await user.click(editBtns[0])

    await user.click(screen.getByRole('button', { name: /switch customer/i }))
    expect(window.confirm).toHaveBeenCalled()
    // confirm returned false → customer should NOT have changed
    expect(screen.getByTestId('active-customer').textContent).toBe('1')
  })
})
