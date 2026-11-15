import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import type { Checkpoint } from '../../../types/routing'
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

  it('shows the locked altitude in an editable input per row (comment 8)', () => {
    render(
      <CheckpointManager
        {...baseProps}
        onSetAltitude={vi.fn()}
        checkpoints={[{ lat: 36.2, lon: 58.6, order: 0, alt: 2200 }]}
      />,
    )
    const input = screen.getByLabelText('Altitude of checkpoint #1 (m MSL)')
    expect(input).toHaveValue('2200')
  })

  it('leaves the altitude input empty for plain checkpoints', () => {
    render(
      <CheckpointManager
        {...baseProps}
        onSetAltitude={vi.fn()}
        checkpoints={[{ lat: 36.2, lon: 58.6, order: 0 }]}
      />,
    )
    expect(screen.getByLabelText('Altitude of checkpoint #1 (m MSL)')).toHaveValue('')
  })

  it('types a positive altitude and reports it (comment 8)', async () => {
    const user = userEvent.setup()
    const onSetAltitude = vi.fn()
    /** والد واقعی (استور) مقدار را برمی‌گرداند — وگرنه ورودی کنترل‌شده
     * با پیشنویسِ خودش همگام نمیشود. */
    function Harness() {
      const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([
        { lat: 36.2, lon: 58.6, order: 0 },
      ])
      return (
        <CheckpointManager
          checkpoints={checkpoints}
          onRemove={vi.fn()}
          onMove={vi.fn()}
          onSetAltitude={(i, alt) => {
            setCheckpoints((cps) =>
              cps.map((cp, idx) => {
                if (idx !== i) return cp
                const next = { ...cp }
                if (alt == null) delete next.alt
                else next.alt = alt
                return next
              }),
            )
            onSetAltitude(i, alt)
          }}
        />
      )
    }
    render(<Harness />)
    const input = screen.getByLabelText('Altitude of checkpoint #1 (m MSL)')
    await user.type(input, '2200')
    expect(onSetAltitude).toHaveBeenLastCalledWith(0, 2200)
    expect(input).toHaveValue('2200')
  })

  it('clearing the altitude input reports a free crossing (null)', async () => {
    const user = userEvent.setup()
    const onSetAltitude = vi.fn()
    render(
      <CheckpointManager
        {...baseProps}
        onSetAltitude={onSetAltitude}
        checkpoints={[{ lat: 36.2, lon: 58.6, order: 0, alt: 2200 }]}
      />,
    )
    const input = screen.getByLabelText('Altitude of checkpoint #1 (m MSL)')
    await user.clear(input)
    expect(onSetAltitude).toHaveBeenLastCalledWith(0, null)
  })

  it('rejects zero and negative altitudes (backend requires alt > 0)', async () => {
    const user = userEvent.setup()
    const onSetAltitude = vi.fn()
    render(
      <CheckpointManager
        {...baseProps}
        onSetAltitude={onSetAltitude}
        checkpoints={[{ lat: 36.2, lon: 58.6, order: 0 }]}
      />,
    )
    const input = screen.getByLabelText('Altitude of checkpoint #1 (m MSL)')
    await user.type(input, '0')
    expect(onSetAltitude).not.toHaveBeenCalled()
    await user.type(input, '-5')
    expect(onSetAltitude).not.toHaveBeenCalled()
  })

  it('omits the altitude inputs entirely when no setter is provided', () => {
    render(
      <CheckpointManager
        {...baseProps}
        checkpoints={[{ lat: 36.2, lon: 58.6, order: 0, alt: 2200 }]}
      />,
    )
    expect(screen.queryByTestId('checkpoint-altitude-input')).not.toBeInTheDocument()
  })
})
