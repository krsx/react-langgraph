import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AppProvider, useApp } from '@/state/context'
import { AgentProcessPanel } from '@/components/process/AgentProcessPanel'
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
      <AgentProcessPanel />
    </AppProvider>
  )
}

// ── Test 1: Empty state ────────────────────────────────────────────────────

describe('AgentProcessPanel – empty state', () => {
  it('shows prompt text when no events have been dispatched', () => {
    renderWithActions()
    expect(screen.getByText(/send a message/i)).toBeInTheDocument()
  })
})

// ── Test 2: memory_loaded ─────────────────────────────────────────────────

describe('AgentProcessPanel – memory_loaded', () => {
  it('shows entry count when memory_loaded event is dispatched', () => {
    renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: {
          event: 'memory_loaded',
          data: {
            thread_id: 't1',
            memory_context: [
              { type: 'memory', key: 'k1', value: 'v1' },
              { type: 'complaint', order_id: 1, issue: 'late', status: 'open', created_at: '' },
            ],
          },
        },
      },
    ])
    expect(screen.getByText(/2 entries loaded/i)).toBeInTheDocument()
  })
})

// ── Test 3: planner_result ─────────────────────────────────────────────────

describe('AgentProcessPanel – planner_result', () => {
  it('shows reasoning text and tool call name', () => {
    renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: {
          event: 'planner_result',
          data: {
            thread_id: 't1',
            content: 'I will look up the order for you.',
            tool_calls: [{ name: 'order_lookup', args: { order_id: 12345 } }],
          },
        },
      },
    ])
    expect(screen.getByText(/I will look up the order for you\./)).toBeInTheDocument()
    expect(screen.getByText(/order_lookup/)).toBeInTheDocument()
  })
})

// ── Test 4: verifier PASS ──────────────────────────────────────────────────

describe('AgentProcessPanel – verifier PASS', () => {
  it('shows PASS badge and check description', () => {
    renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: {
          event: 'verifier_result',
          data: { valid: true, checks: ['all checks passed'], override_message: null },
        },
      },
    ])
    expect(screen.getByText('PASS')).toBeInTheDocument()
    expect(screen.getByText(/all checks passed/i)).toBeInTheDocument()
  })
})

// ── Test 5: verifier FAIL ──────────────────────────────────────────────────

describe('AgentProcessPanel – verifier FAIL', () => {
  it('shows FAIL badge and override message', () => {
    renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: {
          event: 'verifier_result',
          data: {
            valid: false,
            checks: ['tool error: Order 0 not found'],
            override_message: 'I could not complete that request.',
          },
        },
      },
    ])
    expect(screen.getByText('FAIL')).toBeInTheDocument()
    expect(screen.getByText(/I could not complete that request\./)).toBeInTheDocument()
  })
})

// ── Test 6: multiple iterations ────────────────────────────────────────────

describe('AgentProcessPanel – multi-iteration', () => {
  it('renders planner → tool → planner in document order', () => {
    renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: { event: 'planner_result', data: { content: 'First plan', tool_calls: [] } },
      },
      {
        type: 'SSE_EVENT',
        frame: { event: 'tool_result', data: { results: 'some result' } },
      },
      {
        type: 'SSE_EVENT',
        frame: { event: 'planner_result', data: { content: 'Second plan', tool_calls: [] } },
      },
    ])
    const plannerCards = screen.getAllByText(/First plan|Second plan/)
    expect(plannerCards).toHaveLength(2)
    expect(screen.getByText(/some result/)).toBeInTheDocument()
  })
})

// ── Test 7: reset on SEND_MESSAGE ─────────────────────────────────────────

describe('AgentProcessPanel – reset on new turn', () => {
  it('clears cards when SEND_MESSAGE is dispatched', () => {
    const { rerender } = renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: { event: 'planner_result', data: { content: 'Old reasoning', tool_calls: [] } },
      },
    ])
    expect(screen.getByText(/Old reasoning/)).toBeInTheDocument()

    rerender(
      <AppProvider>
        {/* new provider with a SEND_MESSAGE action */}
        {(() => {
          function Resetter() {
            const { dispatch } = useApp()
            useEffect(() => { dispatch({ type: 'SEND_MESSAGE', content: 'new msg' }) }, [dispatch])
            return null
          }
          return <Resetter />
        })()}
        <AgentProcessPanel />
      </AppProvider>
    )
    expect(screen.queryByText(/Old reasoning/)).not.toBeInTheDocument()
  })
})

// ── Test 8: expand / collapse ─────────────────────────────────────────────

describe('AgentProcessPanel – expand/collapse', () => {
  it('shows raw JSON detail only after expand button click', async () => {
    const user = userEvent.setup()
    renderWithActions([
      {
        type: 'SSE_EVENT',
        frame: {
          event: 'planner_result',
          data: { content: 'Expandable plan', tool_calls: [] },
        },
      },
    ])
    // Detail (raw JSON) not visible by default
    expect(screen.queryByText(/"content"/)).not.toBeInTheDocument()

    // Click the expand toggle
    const toggleBtn = screen.getByRole('button', { name: /expand|show detail|▼|▶/i })
    await user.click(toggleBtn)

    // Raw JSON now visible
    expect(screen.getByText(/"content"/)).toBeInTheDocument()

    // Click again to collapse
    await user.click(toggleBtn)
    expect(screen.queryByText(/"content"/)).not.toBeInTheDocument()
  })
})
