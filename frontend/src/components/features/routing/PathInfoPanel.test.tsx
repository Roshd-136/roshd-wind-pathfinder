import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { PathInfoPanel } from './PathInfoPanel'

/** PlaceLabel داخل پنل از react-query استفاده می‌کند — ارائه‌دهندهٔ تست. */
function withProviders(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

const baseProps = {
  algorithm: 'a_star' as const,
  onAlgorithmChange: vi.fn(),
  layerVisibility: { surface: true, mid: true, high: true },
  onLayerVisibilityChange: vi.fn(),
  constraints: { max_wind_speed_mps: 20, criterion: 'time' as const },
  onConstraintsChange: vi.fn(),
  origin: { lat: 36.297, lon: 59.606 },
  destination: { lat: 36.215, lon: 57.678 },
  checkpoints: [],
  onRemoveCheckpoint: vi.fn(),
  onMoveCheckpoint: vi.fn(),
  onPointInfo: vi.fn(),
  canPointInfo: true,
  onBack: vi.fn(),
  canBack: true,
  onCalculate: vi.fn(),
  isCalculating: false,
  result: null,
}

describe('PathInfoPanel', () => {
  const calculateButton = () => screen.getByRole('button', { name: /calculate|محاسبه/i })

  it('disables the calculate button when origin/destination are not both set', () => {
    withProviders(<PathInfoPanel {...baseProps} canCalculate={false} />)
    expect(calculateButton()).toBeDisabled()
  })

  it('enables the calculate button once both points are chosen', () => {
    withProviders(<PathInfoPanel {...baseProps} canCalculate={true} />)
    expect(calculateButton()).toBeEnabled()
  })

  it('shows the route result summary once a result is available', () => {
    withProviders(
      <PathInfoPanel
        {...baseProps}
        canCalculate={true}
        result={{
          route_id: 'r1',
          path: [],
          layer_altitude_m: 500,
          algorithm: 'a_star',
          criterion: 'time',
          total_distance_km: 173.1,
          estimated_time_hours: 2.5,
          total_cost: 1.2,
          created_at: new Date().toISOString(),
        }}
      />,
    )
    expect(screen.getByTestId('route-result-summary')).toHaveTextContent('173.1 km')
  })
})
