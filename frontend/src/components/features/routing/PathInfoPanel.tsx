import { useTranslation } from 'react-i18next'
import { Check, Moon, Sun } from 'lucide-react'
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
  onCalculate: () => void
  isCalculating: boolean
  canCalculate: boolean
  result: RouteResult | null
  /** مسیر از فیکسچر نمایشی dev آمده (بدون بک‌اند) — با برچسب صریح. */
  resultIsDemo?: boolean
}

const fmt = (c: Coordinate) => `${c.lat.toFixed(3)}, ${c.lon.toFixed(3)}`

/**
 * فهرست مراحل انتخاب (مثل ناوبری Uber) — «۱. انتخاب مبدأ / ۲. انتخاب مقصد»؛
 * بعد از انتخاب هر نقطه، متن مرحله با مختصات انتخاب‌شده جایگزین می‌شود.
 */
function RouteSteps({
  origin,
  destination,
}: {
  origin: Coordinate | null
  destination: Coordinate | null
}) {
  const { t } = useTranslation()

  const steps = [
    {
      n: 1,
      done: origin !== null,
      pending: t('routing.stepOrigin'),
      doneText: `${t('routing.stepOriginDone')}: ${origin ? fmt(origin) : ''}`,
    },
    {
      n: 2,
      done: destination !== null,
      pending: t('routing.stepDestination'),
      doneText: `${t('routing.stepDestinationDone')}: ${destination ? fmt(destination) : ''}`,
    },
  ]

  return (
    <ol className="space-y-2" aria-label={t('routing.stepsTitle')}>
      {steps.map((s) => (
        <li key={s.n} className="flex items-center gap-2 text-sm">
          <span
            aria-hidden
            className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-bold ${
              s.done
                ? 'border-success bg-success/15 text-success'
                : 'border-border bg-surface-raised text-text-muted'
            }`}
          >
            {s.done ? <Check size={13} /> : s.n}
          </span>
          <span className={s.done ? 'text-text-primary' : 'text-text-muted'}>
            {s.done ? s.doneText : s.pending}
          </span>
        </li>
      ))}
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
  onCalculate,
  isCalculating,
  canCalculate,
  result,
  resultIsDemo = false,
}: PathInfoPanelProps) {
  const { t } = useTranslation()

  return (
    <Card className="flex h-full w-full flex-col gap-4 overflow-y-auto">
      <div className="flex items-start justify-between gap-2">
        <RouteSteps origin={origin} destination={destination} />
        <ThemeToggle />
      </div>

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
