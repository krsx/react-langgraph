import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RightPanelShell } from '@/components/layout/RightPanelShell'

describe('RightPanelShell', () => {
  it('renders children when not collapsed', () => {
    render(<RightPanelShell isCollapsed={false} onToggle={() => {}}><span>panel content</span></RightPanelShell>)
    expect(screen.getByText('panel content')).toBeInTheDocument()
  })

  it('hides children when collapsed', () => {
    render(<RightPanelShell isCollapsed={true} onToggle={() => {}}><span>panel content</span></RightPanelShell>)
    expect(screen.queryByText('panel content')).not.toBeInTheDocument()
  })

  it('calls onToggle when toggle button is clicked', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    render(<RightPanelShell isCollapsed={false} onToggle={onToggle} />)
    await user.click(screen.getByRole('button'))
    expect(onToggle).toHaveBeenCalledOnce()
  })
})
