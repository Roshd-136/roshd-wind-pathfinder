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
  step: 1 as 1 | 2 | 3,
  onBack: vi.fn(),
  onNext: vi.fn(),
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
    withProviders(<StepsWizard {...base} step={3} hasResult={true} />)
    expect(screen.getByText('Compute route')).toBeInTheDocument()
  })

  it('renders the place search input on picking steps (ui-only)', () => {
    withProviders(<StepsWizard {...base} step={1} />)
    expect(screen.getByPlaceholderText('Search a place…')).toBeInTheDocument()
  })

  it('hides the place search input on the compute step', () => {
    withProviders(<StepsWizard {...base} step={3} hasResult={true} />)
    expect(screen.queryByPlaceholderText('Search a place…')).not.toBeInTheDocument()
  })

  it('does not show the steps title as visible text', () => {
    withProviders(<StepsWizard {...base} />)
    // «Route steps» فقط برچسب دسترس‌پذیری است، نه متن قابل‌دیدن
    expect(screen.queryByText('Route steps')).not.toBeInTheDocument()
  })

  it('disables the back arrow on the first step and the next arrow on the last', () => {
    const first = withProviders(<StepsWizard {...base} step={1} />)
    expect(prevButton()).toBeDisabled()
    expect(nextButton()).toBeEnabled()
    first.unmount()
    withProviders(<StepsWizard {...base} step={3} hasResult={true} />)
    expect(prevButton()).toBeEnabled()
    expect(nextButton()).toBeDisabled()
  })

  it('fires onBack and onNext without clearing data (replace-on-click model)', async () => {
    const user = userEvent.setup()
    const onBack = vi.fn()
    const onNext = vi.fn()
    withProviders(<StepsWizard {...base} step={2} onBack={onBack} onNext={onNext} />)
    await user.click(prevButton())
    expect(onBack).toHaveBeenCalledTimes(1)
    await user.click(nextButton())
    expect(onNext).toHaveBeenCalledTimes(1)
  })
})
