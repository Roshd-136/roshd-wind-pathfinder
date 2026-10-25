import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { RouteErrorDialog } from './RouteErrorDialog'

describe('RouteErrorDialog', () => {
  it('renders the engine error message in its own frame (not an inline banner)', () => {
    render(
      <RouteErrorDialog
        message="در باند ارتفاعی «سطحی» مسیر پروازپذیری پیدا نشد."
        onClose={vi.fn()}
      />,
    )
    expect(screen.getByRole('alertdialog')).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByTestId('route-error-dialog')).toHaveTextContent(
      'در باند ارتفاعی «سطحی» مسیر پروازپذیری پیدا نشد.',
    )
  })

  it('closes on Escape', () => {
    const onClose = vi.fn()
    render(<RouteErrorDialog message="خطا" onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes on backdrop click but not on the card itself', () => {
    const onClose = vi.fn()
    render(<RouteErrorDialog message="خطا" onClose={onClose} />)
    fireEvent.click(screen.getByTestId('route-error-dialog'))
    expect(onClose).not.toHaveBeenCalled()
    fireEvent.click(screen.getByTestId('route-error-overlay'))
    expect(onClose).toHaveBeenCalledOnce()
  })
})
