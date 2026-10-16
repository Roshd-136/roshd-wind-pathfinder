import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CheckpointManager } from './CheckpointManager'

const baseProps = {
  checkpoints: [],
  onRemove: vi.fn(),
  onMove: vi.fn(),
}

describe('CheckpointManager', () => {
  it('shows the explicit 2D-only reason when adding is disabled in 3D', () => {
    render(
      <CheckpointManager
        {...baseProps}
        canAdd={false}
        disabledHint="افزودن چک‌پوینت فقط در نمایش ۲بعدی امکان‌پذیر است؛ به نمای ۲بعدی بروید."
      />,
    )
    expect(screen.getByText(/۲بعدی/)).toBeInTheDocument()
  })

  it('stays silent about the reason when the button is enabled', () => {
    render(<CheckpointManager {...baseProps} canAdd />)
    expect(screen.queryByText(/۲بعدی/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add checkpoint/i })).toBeEnabled()
  })

  it('numbers the checkpoints and allows removal', () => {
    render(
      <CheckpointManager
        {...baseProps}
        checkpoints={[
          { lat: 36.2, lon: 58.6, order: 0 },
          { lat: 36.3, lon: 58.9, order: 1 },
        ]}
      />,
    )
    expect(screen.getByText('#1 — 36.200, 58.600')).toBeInTheDocument()
    expect(screen.getByText('#2 — 36.300, 58.900')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /remove/i })).toHaveLength(2)
  })
})
