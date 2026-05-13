import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RightPanelShell } from '@/components/layout/RightPanelShell'

describe('RightPanelShell', () => {
  it('shows placeholder text when not collapsed', () => {
    render(<RightPanelShell isCollapsed={false} onToggle={() => {}} />)
    expect(screen.getByText(/agent process/i)).toBeInTheDocument()
  })

  it('hides placeholder when collapsed', () => {
    render(<RightPanelShell isCollapsed={true} onToggle={() => {}} />)
    expect(screen.queryByText(/agent process/i)).not.toBeInTheDocument()
  })

  it('calls onToggle when toggle button is clicked', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    render(<RightPanelShell isCollapsed={false} onToggle={onToggle} />)
    await user.click(screen.getByRole('button'))
    expect(onToggle).toHaveBeenCalledOnce()
  })
})
