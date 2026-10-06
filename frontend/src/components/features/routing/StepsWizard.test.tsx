import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { StepsWizard } from './StepsWizard'

function withProviders(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const base = {
  origin: { lat: 36.297, lon: 59.606 },
  destination: { lat: 36.215, lon: 57.678 },
  hasResult: false,
  onBack: vi.fn(),
  canBack: true,
  canCalculate: true,
  onCalculate: vi.fn(),
  isCalculating: false,
}

describe('StepsWizard', () => {
  const calcButton = () => screen.getByRole('button', { name: /calculate|محاسبه/i })
  const prevButton = () => screen.getByRole('button', { name: /previous step|مرحله قبل/i })
  const nextButton = () => screen.getByRole('button', { name: /next step|گام بعد/i })

  it('disables calculate until both points are chosen', () => {
    withProviders(<StepsWizard {...base} origin={null} canCalculate={false} />)
    expect(calcButton()).toBeDisabled()
  })

  it('enables calculate once both points are chosen', () => {
    withProviders(<StepsWizard {...base} canCalculate={true} />)
    expect(calcButton()).toBeEnabled()
  })

  it('shows the big title of the current step', () => {
    withProviders(<StepsWizard {...base} hasResult={true} />)
    expect(screen.getByText('Compute route')).toBeInTheDocument()
  })

  it('renders the place search input (ui-only)', () => {
    withProviders(<StepsWizard {...base} />)
    expect(screen.getByPlaceholderText('Search a place…')).toBeInTheDocument()
  })

  it('does not show the steps title as visible text', () => {
    withProviders(<StepsWizard {...base} />)
    // «Route steps» فقط برچسب دسترس‌پذیری است، نه متن قابل‌دیدن
    expect(screen.queryByText('Route steps')).not.toBeInTheDocument()
  })

  it('goes one step back with the side arrow and calls onBack', async () => {
    const user = userEvent.setup()
    const onBack = vi.fn()
    withProviders(<StepsWizard {...base} hasResult={true} onBack={onBack} />)
    await user.click(prevButton())
    expect(onBack).toHaveBeenCalledTimes(1)
    // بعد از بازگشت، فلش بعد فعال می‌شود (بازتولید گام‌ها)
    expect(nextButton()).toBeEnabled()
  })

  it('disables the next arrow while the last reached step is shown', () => {
    withProviders(<StepsWizard {...base} hasResult={true} />)
    expect(nextButton()).toBeDisabled()
  })

  it('moves forward again with the next arrow after going back', async () => {
    const user = userEvent.setup()
    withProviders(<StepsWizard {...base} hasResult={true} />)
    await user.click(prevButton())
    expect(screen.getByText('Select end')).toBeInTheDocument()
    await user.click(nextButton())
    expect(screen.getByText('Compute route')).toBeInTheDocument()
  })
})
