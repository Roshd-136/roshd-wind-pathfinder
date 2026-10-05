import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Check, Moon, Sun, Undo2 } from 'lucide-react'
import type {
  Algorithm,
  Checkpoint,
  Coordinate,
  RouteConstraints,
  RouteResult,
} from '../../../types/routing'
import { Button } from '../../ui/Button'
import { Card } from '../../ui/Card'
import { Slider } from '../../ui/Slider'
import { useSettingsStore } from '../../../store/useSettingsStore'
import { reverseGeocode } from '../../../utils/geocode'
import { WindLayerControls, type LayerVisibility } from '../layers/WindLayerControls'
import { AlgorithmSelector } from './AlgorithmSelector'
import { AdvancedFiltersPanel } from './AdvancedFiltersPanel'
import { CheckpointManager } from './CheckpointManager'

/** کلید تم روشن/تاریک — به داخل پنل منتقل شد (نوار بالایی حذف شده است). */
function ThemeToggle() {
  const theme = useSettingsStore((s) => s.theme)
  const setTheme = useSettingsStore((s) => s.setTheme)
  const isDark = theme !== 'light'
  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
      aria-label={useTranslation().t('settings.theme')}
      title={useTranslation().t('settings.theme')}
      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-surface-raised text-text-secondary transition-colors hover:text-text-primary"
    >
      {isDark ? <Sun size={15} aria-hidden /> : <Moon size={15} aria-hidden />}
    </button>
  )
}

interface PathInfoPanelProps {
  algorithm: Algorithm
  onAlgorithmChange: (algorithm: Algorithm) => void
  layerVisibility: LayerVisibility
  onLayerVisibilityChange: (value: LayerVisibility) => void
  constraints: RouteConstraints
  onConstraintsChange: (value: RouteConstraints) => void
  origin: Coordinate | null
  destination: Coordinate | null
  checkpoints: Checkpoint[]
  onRemoveCheckpoint: (index: number) => void
  onMoveCheckpoint: (index: number, direction: -1 | 1) => void
  onPointInfo: () => void
  canPointInfo: boolean
  /** گام عقب در ویزارد انتخاب (پاک‌کردن مقصد/مبدأ به ترتیب). */
  onBack: () => void
  canBack: boolean
  onCalculate: () => void
  isCalculating: boolean
  canCalculate: boolean
  result: RouteResult | null
  /** مسیر از فیکسچر نمایشی dev آمده (بدون بک‌اند) — با برچسب صریح. */
  resultIsDemo?: boolean
}

const fmt = (c: Coordinate) => `${c.lat.toFixed(3)}, ${c.lon.toFixed(3)}`

/** نام مکان یک نقطه (استان/شهر/خیابان) — با ژئوکدینگ معکوس آزاد OSM؛
 *  در نبود شبکه به مختصات برمی‌گردد. */
function PlaceLabel({ point }: { point: Coordinate }) {
  const language = useSettingsStore((s) => s.language)
  const { data } = useQuery({
    queryKey: ['geocode', point.lat.toFixed(3), point.lon.toFixed(3), language],
    queryFn: () => reverseGeocode(point.lat, point.lon, language),
    staleTime: Infinity,
  })
  return <>{data ?? fmt(point)}</>
}

/**
 * ویزارد مراحل (مثل ناوبری Uber) — سه گام: ۱. انتخاب مبدأ، ۲. انتخاب مقصد،
 * ۳. محاسبهٔ مسیر. عنوان گام جاری با فونت بزرگ و انیمیشن جابه‌جا می‌شود و
 * فهرست کوچک وضعیت هر گام (انجام‌شده ✓/جاری/در انتظار) را نشان می‌دهد.
 */
function RouteSteps({
  origin,
  destination,
  hasResult,
}: {
  origin: Coordinate | null
  destination: Coordinate | null
  hasResult: boolean
}) {
  const { t } = useTranslation()
  const step = origin === null ? 1 : destination === null ? 2 : 3

  // برچسب هر گام — برای گام‌های انجام‌شده: نام مکان (استان/شهر/خیابان)
  const steps: { n: number; done: boolean; label: ReactNode }[] = [
    {
      n: 1,
      done: origin !== null,
      label:
        origin !== null ? (
          <>
            {t('routing.stepOriginDone')}: <PlaceLabel point={origin} />
          </>
        ) : (
          t('routing.stepOrigin')
        ),
    },
    {
      n: 2,
      done: destination !== null,
      label:
        destination !== null ? (
          <>
            {t('routing.stepDestinationDone')}: <PlaceLabel point={destination} />
          </>
        ) : (
          t('routing.stepDestination')
        ),
    },
    {
      n: 3,
      done: hasResult,
      label: hasResult ? t('routing.stepComputeDone') : t('routing.stepCompute'),
    },
  ]

  return (
    <ol className="min-w-0 flex-1 space-y-2" aria-label={t('routing.stepsTitle')}>
      {steps.map((s) => {
        const isCurrent = s.n === step && !s.done
        return (
          <li key={s.n} className="flex items-center gap-2">
            <span
              aria-hidden
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
                s.done
                  ? 'border-success bg-success/15 text-success'
                  : isCurrent
                    ? 'border-accent bg-accent/15 text-accent'
                    : 'border-border bg-surface-raised text-text-muted'
              }`}
            >
              {s.done ? <Check size={12} /> : s.n}
            </span>
            <span
              key={`${s.n}-${s.done}`}
              className={`step-swap min-w-0 ${
                isCurrent
                  ? 'text-xl font-extrabold leading-tight text-text-primary'
                  : s.done
                    ? 'text-xs text-text-secondary'
                    : 'text-xs text-text-muted'
              }`}
            >
              {s.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

/**
 * پنل کنار نقشه (کنترل + نتیجه) — ترکیب مراحل انتخاب، AlgorithmSelector،
 * WindLayerControls، مدیریت چک‌پوینت، فیلترهای پیشرفته، و دکمه اصلی، مطابق
 * چیدمان mockup + چک‌لیست کامل تسک (آیتم‌های ۶، ۱۰، ۱۱). بعد از محاسبه،
 * خلاصه نتیجه هم همین‌جا نمایش داده می‌شود.
 */
export function PathInfoPanel({
  algorithm,
  onAlgorithmChange,
  layerVisibility,
  onLayerVisibilityChange,
  constraints,
  onConstraintsChange,
  origin,
  destination,
  checkpoints,
  onRemoveCheckpoint,
  onMoveCheckpoint,
  onPointInfo,
  canPointInfo,
  onBack,
  canBack,
  onCalculate,
  isCalculating,
  canCalculate,
  result,
  resultIsDemo = false,
}: PathInfoPanelProps) {
  const { t } = useTranslation()

  return (
    <Card className="flex w-full flex-col gap-4 overflow-y-auto rounded-2xl shadow-[var(--shadow-card)] md:h-full">
      <div className="flex items-center justify-between gap-1.5">
        <div className="flex items-center gap-1.5">
          {/* دکمهٔ بازگشت — جلوی کلید تم (برگشت به گام قبل ویرایش) */}
          <button
            type="button"
            onClick={onBack}
            disabled={!canBack}
            aria-label={t('routing.back')}
            title={t('routing.back')}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-surface-raised text-text-secondary transition-colors hover:text-text-primary disabled:opacity-30"
          >
            <Undo2 size={15} aria-hidden />
          </button>
          <ThemeToggle />
        </div>
      </div>
      <RouteSteps origin={origin} destination={destination} hasResult={Boolean(result)} />

      <AlgorithmSelector value={algorithm} onChange={onAlgorithmChange} />

      <WindLayerControls value={layerVisibility} onChange={onLayerVisibilityChange} />

      <div className="space-y-2 border-t border-border pt-3">
        <h3 className="text-sm font-semibold text-text-primary">{t('routing.constraints')}</h3>
        <Slider
          label={t('routing.maxWindSpeed')}
          value={constraints.max_wind_speed_mps ?? 20}
          min={0}
          max={30}
          step={1}
          onChange={(v) => onConstraintsChange({ ...constraints, max_wind_speed_mps: v })}
        />
      </div>

      <AdvancedFiltersPanel value={constraints} onChange={onConstraintsChange} />

      <div className="space-y-2 border-t border-border pt-3">
        <h3 className="text-sm font-semibold text-text-primary">{t('routing.checkpoints')}</h3>
        <CheckpointManager
          checkpoints={checkpoints}
          onRemove={onRemoveCheckpoint}
          onMove={onMoveCheckpoint}
        />
      </div>

      <div className="space-y-2 border-t border-border pt-3">
        <Button
          variant="secondary"
          className="w-full"
          onClick={onPointInfo}
          disabled={!canPointInfo}
        >
          {t('windLayers.viewAtPoint')}
        </Button>
        <p className="text-xs text-text-muted">{t('windLayers.viewAtPointHint')}</p>
      </div>

      {result && (
        <div
          className="space-y-1 rounded-md border border-border bg-surface-raised p-3 text-xs text-text-secondary"
          data-testid="route-result-summary"
        >
          {resultIsDemo && (
            <p className="mb-1 rounded bg-accent/10 px-2 py-1 text-accent">
              {t('routing.demoRoute')}
            </p>
          )}
          <div className="flex justify-between">
            <span>{t('results.layerAltitude')}</span>
            <span className="text-text-primary">{result.layer_altitude_m} m</span>
          </div>
          <div className="flex justify-between">
            <span>{t('results.distance')}</span>
            <span className="text-text-primary">{result.total_distance_km.toFixed(1)} km</span>
          </div>
          <div className="flex justify-between">
            <span>{t('results.eta')}</span>
            <span className="text-text-primary">{result.estimated_time_hours.toFixed(2)} h</span>
          </div>
        </div>
      )}

      <Button
        className="mt-auto w-full"
        onClick={onCalculate}
        disabled={!canCalculate || isCalculating}
      >
        {isCalculating ? t('common.loading') : t('routing.calculatePath')}
      </Button>
    </Card>
  )
}
