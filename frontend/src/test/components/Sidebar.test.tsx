import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppProvider } from '@/state/context'
import { Sidebar } from '@/components/sidebar/Sidebar'

function renderSidebar() {
  return render(
    <AppProvider>
      <Sidebar />
    </AppProvider>
  )
}

describe('Sidebar', () => {
  it('loads and displays customer names from API', async () => {
    renderSidebar()
    await waitFor(() => expect(screen.getByText('Ahmad Rifqi')).toBeInTheDocument())
    expect(screen.getByText('Jane Doe')).toBeInTheDocument()
  })

  it('displays both provider options', async () => {
    renderSidebar()
    await waitFor(() => expect(screen.getByText('openrouter')).toBeInTheDocument())
    expect(screen.getByText('ollama')).toBeInTheDocument()
  })

  it('shows session history filtered to active customer after selecting one', async () => {
    const user = userEvent.setup()
    renderSidebar()
    await waitFor(() => expect(screen.getByText('Ahmad Rifqi')).toBeInTheDocument())
    // Before customer selection, sessions are unfiltered - customer 1 session should appear
    // after we pick customer 1
    const customerSelect = screen.getByTestId('customer-select')
    await user.selectOptions(customerSelect, 'Ahmad Rifqi')
    await waitFor(() => expect(screen.getByText('Where is my order?')).toBeInTheDocument())
    expect(screen.queryByText('I need a refund')).not.toBeInTheDocument()
  })

  it('renders a New Chat button', async () => {
    renderSidebar()
    await waitFor(() => expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument())
  })
})
