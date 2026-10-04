import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Collapsible } from './Collapsible'

describe('Collapsible', () => {
  it('hides content until expanded, then shows it', async () => {
    const user = userEvent.setup()
    render(
      <Collapsible title="ارتفاع پرواز">
        <p>محتوای پنهان</p>
      </Collapsible>,
    )
    expect(screen.queryByText('محتوای پنهان')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'ارتفاع پرواز' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )

    await user.click(screen.getByRole('button', { name: 'ارتفاع پرواز' }))

    expect(screen.getByText('محتوای پنهان')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'ارتفاع پرواز' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
  })

  it('supports defaultOpen and collapses back on second click', async () => {
    const user = userEvent.setup()
    const onToggle = vi.fn()
    render(
      <Collapsible title="بهینه‌سازی" defaultOpen>
        <p>آشکار</p>
      </Collapsible>,
    )
    onToggle.mockClear()
    expect(screen.getByText('آشکار')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'بهینه‌سازی' }))
    expect(screen.queryByText('آشکار')).not.toBeInTheDocument()
  })
})
