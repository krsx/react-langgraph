import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AppProvider, useApp } from '@/state/context'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { useEffect } from 'react'
import type { Action } from '@/state/types'

function renderWithState(actions: Action[]) {
  function Primer() {
    const { dispatch } = useApp()
    useEffect(() => { actions.forEach((a) => dispatch(a)) }, [dispatch])
    return null
  }
  return render(
    <AppProvider>
      <Primer />
      <ChatPanel />
    </AppProvider>
  )
}

describe('ChatPanel', () => {
  it('disables composer when no customer is selected', () => {
    render(
      <AppProvider>
        <ChatPanel />
      </AppProvider>
    )
    const input = screen.getByPlaceholderText(/type a message/i)
    expect(input).toBeDisabled()
  })

  it('enables composer when a customer is selected', () => {
    renderWithState([{ type: 'CUSTOMER_CHANGED', customerId: 1 }])
    const input = screen.getByPlaceholderText(/type a message/i)
    expect(input).not.toBeDisabled()
  })

  it('disables composer in readonly session mode', () => {
    renderWithState([
      { type: 'CUSTOMER_CHANGED', customerId: 1 },
      {
        type: 'SESSION_SELECTED',
        threadId: 't1',
        messages: [{ message_id: 1, role: 'human', content: 'hi', created_at: '' }],
      },
    ])
    const input = screen.getByPlaceholderText(/type a message/i)
    expect(input).toBeDisabled()
  })

  it('renders committed transcript messages', () => {
    renderWithState([
      { type: 'CUSTOMER_CHANGED', customerId: 1 },
      { type: 'SEND_MESSAGE', content: 'Hello agent' },
    ])
    expect(screen.getByText('Hello agent')).toBeInTheDocument()
  })

  it('renders streaming token in live bubble', () => {
    renderWithState([
      { type: 'CUSTOMER_CHANGED', customerId: 1 },
      { type: 'SEND_MESSAGE', content: 'test' },
      { type: 'SSE_EVENT', frame: { event: 'response_token', data: { token: 'Thinking...' } } },
    ])
    expect(screen.getByText(/Thinking\.\.\./)).toBeInTheDocument()
  })
})
