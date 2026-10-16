import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import i18n from '../../../i18n'
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
  layerVisibility: { surface: true, mid: true, high: true, top: true },
  onLayerVisibilityChange: vi.fn(),
  constraints: { max_wind_speed_mps: 20, criterion: 'time' as const },
  onConstraintsChange: vi.fn(),
  checkpoints: [],
  onRemoveCheckpoint: vi.fn(),
  onMoveCheckpoint: vi.fn(),
  onClear: vi.fn(),
  canClear: true,
  addingCheckpoint: false,
  onToggleAddCheckpoint: vi.fn(),
  canAddCheckpoint: true,
  result: null,
}

describe('PathInfoPanel', () => {
  const sampleResult = {
    route_id: 'r1',
    path: [],
    layer_altitude_m: 500,
    algorithm: 'a_star' as const,
    criterion: 'time' as const,
    total_distance_km: 173.1,
    estimated_time_hours: 2.5,
    total_cost: 1.2,
    created_at: new Date().toISOString(),
  }

  it('shows the route result summary once a result is available', () => {
    withProviders(<PathInfoPanel {...baseProps} result={sampleResult} />)
    expect(screen.getByTestId('route-result-summary')).toHaveTextContent('173.1 km')
  })

  it('formats the summary with Persian units in fa («ک.م» and «۱س۲۰د» style)', async () => {
    await i18n.changeLanguage('fa')
    try {
      withProviders(<PathInfoPanel {...baseProps} result={sampleResult} />)
      expect(screen.getByTestId('route-result-summary')).toHaveTextContent('۱۷۳٫۱ ک.م')
      expect(screen.getByTestId('route-result-summary')).toHaveTextContent('۲س۳۰د')
      expect(screen.getByTestId('route-result-summary')).toHaveTextContent('۵۰۰ متر')
    } finally {
      await i18n.changeLanguage('en')
    }
  })

  it('does not render the removed "wind layers at point" button anymore', () => {
    withProviders(<PathInfoPanel {...baseProps} />)
    // دکمهٔ «مشاهده لایه‌های باد در نقطه» به‌درخواست کاربر حذف شده — نباید
    // هیچ ردی از آن در پنل بماند.
    expect(screen.queryByText(/لایه‌های باد در نقطه/)).not.toBeInTheDocument()
    expect(screen.queryByText('View Wind Layers at Point')).not.toBeInTheDocument()
  })
})
