import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { PathInfoPanel } from './PathInfoPanel'

const baseProps = {
  algorithm: 'a_star' as const,
  onAlgorithmChange: vi.fn(),
  layerVisibility: { surface: true, mid: true, high: true },
  onLayerVisibilityChange: vi.fn(),
  maxWindSpeed: 20,
  onMaxWindSpeedChange: vi.fn(),
  onCalculate: vi.fn(),
  isCalculating: false,
  result: null,
}

describe('PathInfoPanel', () => {
  it('disables the calculate button when origin/destination are not both set', () => {
    render(<PathInfoPanel {...baseProps} canCalculate={false} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('enables the calculate button once both points are chosen', () => {
    render(<PathInfoPanel {...baseProps} canCalculate={true} />)
    expect(screen.getByRole('button')).toBeEnabled()
  })

  it('shows the route result summary once a result is available', () => {
    render(
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
