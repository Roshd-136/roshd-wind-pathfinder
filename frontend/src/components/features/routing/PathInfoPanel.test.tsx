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
  checkpoints: [],
  onRemoveCheckpoint: vi.fn(),
  onMoveCheckpoint: vi.fn(),
  onPointInfo: vi.fn(),
  canPointInfo: true,
  onClear: vi.fn(),
  canClear: true,
  addingCheckpoint: false,
  onToggleAddCheckpoint: vi.fn(),
  canAddCheckpoint: true,
  result: null,
}

describe('PathInfoPanel', () => {
  it('shows the route result summary once a result is available', () => {
    withProviders(
      <PathInfoPanel
        {...baseProps}
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
