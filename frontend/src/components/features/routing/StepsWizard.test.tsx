import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
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
})
