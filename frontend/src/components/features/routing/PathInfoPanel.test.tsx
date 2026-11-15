import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState, type ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import i18n from '../../../i18n'
import type { RouteConstraints, RouteResult } from '../../../types/routing'
import { PathInfoPanel } from './PathInfoPanel'

// ژئوکدینگ معکوس (شبکهٔ واقعی OSM) در آزمون به نتیجهٔ ثابت قفل می‌شود —
// PlaceLabel داخل پنل همان را نشان می‌دهد و آزمون به شبکه وابسته نمی‌ماند.
vi.mock('../../../utils/geocode', () => ({
  reverseGeocode: vi.fn().mockResolvedValue('Test place'),
}))

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
  origin: null,
  destination: null,
}

/** جفت آزمایشی یک‌درجهٔ عرض — خط مستقیم ≈ ۱۱۱٫۲ ک.م. */
const pickedProps = {
  ...baseProps,
  origin: { lat: 0, lon: 0 },
  destination: { lat: 0, lon: 1 },
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

  it('always shows the origin/destination section (even with no result)', async () => {
    withProviders(<PathInfoPanel {...pickedProps} />)
    // کامنت ۹ «کامنت‌های نرم‌افزار»: بخش مبدا و مقصد همیشه‌دید است، نه فقط
    // بعد از محاسبه.
    expect(screen.getByTestId('points-summary')).toBeInTheDocument()
    // برچسب ژئوکدینگ ناهمگام می‌رسد — findBy منتظرش می‌ماند.
    expect(await screen.findByText('Test place')).toBeInTheDocument()
    expect(screen.getByTestId('straight-line')).toHaveTextContent('111.2 km')
  })

  it('compares the computed route against the straight line', () => {
    withProviders(<PathInfoPanel {...pickedProps} result={sampleResult} />)
    // ۱۷۳٫۱ ک.م نسبت به ۱۱۱٫۲ ک.م ≈ ۵۶٪ دورتر
    const comparison = screen.getByTestId('straight-comparison')
    expect(comparison).toHaveTextContent('+56%')
    expect(comparison).toHaveTextContent('173.1 km')
    expect(comparison).toHaveTextContent('111.2 km')
  })

  it('renders the comparison with Persian digits and percent in fa', async () => {
    await i18n.changeLanguage('fa')
    try {
      withProviders(<PathInfoPanel {...pickedProps} result={sampleResult} />)
      expect(screen.getByTestId('straight-line')).toHaveTextContent('۱۱۱٫۲ ک.م')
      expect(screen.getByTestId('straight-comparison')).toHaveTextContent('+۵۶٪')
    } finally {
      await i18n.changeLanguage('en')
    }
  })

  it('shows the picking hint and no straight-line row while points are missing', () => {
    withProviders(<PathInfoPanel {...baseProps} />)
    expect(screen.getByTestId('points-summary')).toHaveTextContent('Not selected')
    expect(screen.getByTestId('points-summary')).toHaveTextContent('Click the map')
    expect(screen.queryByTestId('straight-line')).not.toBeInTheDocument()
    expect(screen.queryByTestId('straight-comparison')).not.toBeInTheDocument()
  })

  it('has no straight-line row until both points are chosen', () => {
    withProviders(<PathInfoPanel {...pickedProps} destination={null} />)
    expect(screen.queryByTestId('straight-line')).not.toBeInTheDocument()
  })

  // ————— سرعت موتور (کامنت ۷) —————

  const advancedToggle = () => screen.getByRole('button', { name: 'Advanced settings' })
  const motorInput = () => screen.getByLabelText('Motor speed (m/s)')

  const emptyConstraints: RouteConstraints = {
    criterion: 'time',
    altitude_range_m: null,
    max_wind_speed_mps: null,
    avoid_zones: [],
  }

  /**
   * شبیه‌سازی والد واقعی: `constraints` از استور برمی‌گردد تا پیشنویسِ
   * ورودی سرعت موتور با vessel همگام بماند (رفتار واقعی RoutingMapScreen) —
   * بدون این، ورودی کنترل‌شده در آزمون با مقدار خودش همگام نمی‌شود.
   */
  function MotorHarness(props: {
    initialConstraints: RouteConstraints
    onConstraintsChange: (c: RouteConstraints) => void
    result?: RouteResult | null
    windSpeedAtLayer?: { altitudeM: number; speedMps: number } | null
  }) {
    const [constraints, setConstraints] = useState(props.initialConstraints)
    return (
      <PathInfoPanel
        {...baseProps}
        constraints={constraints}
        onConstraintsChange={(c) => {
          setConstraints(c)
          props.onConstraintsChange(c)
        }}
        result={props.result ?? null}
        windSpeedAtLayer={props.windSpeedAtLayer ?? null}
      />
    )
  }

  it('writes the motor speed into constraints.vessel (comment 7)', async () => {
    const user = userEvent.setup()
    const onConstraintsChange = vi.fn()
    withProviders(
      <MotorHarness
        initialConstraints={emptyConstraints}
        onConstraintsChange={onConstraintsChange}
      />,
    )
    await user.click(advancedToggle())
    await user.type(motorInput(), '18')
    expect(onConstraintsChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        vessel: {
          type: 'aircraft',
          airspeed_mps: 18,
          induced_drag_coeff: 0.3,
          headwind_penalty_coeff: 0.25,
        },
      }),
    )
  })

  it('clearing the input drops vessel so the backend engine default applies', async () => {
    const user = userEvent.setup()
    const onConstraintsChange = vi.fn()
    withProviders(
      <MotorHarness
        initialConstraints={{
          ...emptyConstraints,
          vessel: {
            type: 'aircraft',
            airspeed_mps: 20,
            induced_drag_coeff: 0.3,
            headwind_penalty_coeff: 0.25,
          },
        }}
        onConstraintsChange={onConstraintsChange}
      />,
    )
    await user.click(advancedToggle())
    expect(motorInput()).toHaveValue('20')
    await user.clear(motorInput())
    const last = onConstraintsChange.mock.lastCall?.[0] as RouteConstraints
    expect(last).not.toHaveProperty('vessel')
  })

  it('shows wind speed at the flight layer and the ≈ badge when motor matches', async () => {
    const user = userEvent.setup()
    withProviders(
      <MotorHarness
        initialConstraints={emptyConstraints}
        onConstraintsChange={vi.fn()}
        result={sampleResult}
        windSpeedAtLayer={{ altitudeM: 1500, speedMps: 7.1 }}
      />,
    )
    await user.click(advancedToggle())
    expect(screen.getByTestId('wind-at-layer')).toHaveTextContent(
      'Wind speed at 1,500 m: 7.1 m/s',
    )
    await user.type(motorInput(), '7')
    // |۷ − ۷٫۱| = ۰٫۱ ≤ ۵٪ × ۷٫۱ — نشانِ «تقریباً برابر» دیده می‌شود
    expect(screen.getByTestId('motor-matches-wind')).toBeInTheDocument()
  })

  it('does not show the ≈ badge when the motor speed clearly differs from wind', async () => {
    const user = userEvent.setup()
    withProviders(
      <MotorHarness
        initialConstraints={emptyConstraints}
        onConstraintsChange={vi.fn()}
        result={sampleResult}
        windSpeedAtLayer={{ altitudeM: 1500, speedMps: 7.1 }}
      />,
    )
    await user.click(advancedToggle())
    await user.type(motorInput(), '15')
    expect(screen.queryByTestId('motor-matches-wind')).not.toBeInTheDocument()
  })

  it('enables the unified reset once a motor speed is set', () => {
    withProviders(
      <PathInfoPanel
        {...baseProps}
        constraints={{
          ...emptyConstraints,
          vessel: {
            type: 'aircraft',
            airspeed_mps: 20,
            induced_drag_coeff: 0.3,
            headwind_penalty_coeff: 0.25,
          },
        }}
      />,
    )
    expect(screen.getByRole('button', { name: 'Reset filters' })).toBeEnabled()
  })
})
