import { useTranslation } from 'react-i18next'
import type { Algorithm, Checkpoint, RouteConstraints, RouteResult } from '../../../types/routing'
import { Button } from '../../ui/Button'
import { Card } from '../../ui/Card'
import { Slider } from '../../ui/Slider'
import { WindLayerControls, type LayerVisibility } from '../layers/WindLayerControls'
import { AlgorithmSelector } from './AlgorithmSelector'
import { AdvancedFiltersPanel } from './AdvancedFiltersPanel'
import { CheckpointManager } from './CheckpointManager'

interface PathInfoPanelProps {
  algorithm: Algorithm
  onAlgorithmChange: (algorithm: Algorithm) => void
  layerVisibility: LayerVisibility
  onLayerVisibilityChange: (value: LayerVisibility) => void
  constraints: RouteConstraints
  onConstraintsChange: (value: RouteConstraints) => void
  checkpoints: Checkpoint[]
  onRemoveCheckpoint: (index: number) => void
  onMoveCheckpoint: (index: number, direction: -1 | 1) => void
  onCalculate: () => void
  isCalculating: boolean
  canCalculate: boolean
  result: RouteResult | null
}

/**
 * پنل سمت راست (کنترل + نتیجه) — ترکیب AlgorithmSelector، WindLayerControls،
 * مدیریت چک‌پوینت، فیلترهای پیشرفته، و دکمه اصلی، مطابق چیدمان mockup +
 * چک‌لیست کامل تسک (آیتم‌های ۶، ۱۰، ۱۱). بعد از محاسبه، خلاصه نتیجه هم
 * همین‌جا نمایش داده می‌شود.
 */
export function PathInfoPanel({
  algorithm,
  onAlgorithmChange,
  layerVisibility,
  onLayerVisibilityChange,
  constraints,
  onConstraintsChange,
  checkpoints,
  onRemoveCheckpoint,
  onMoveCheckpoint,
  onCalculate,
  isCalculating,
  canCalculate,
  result,
}: PathInfoPanelProps) {
  const { t } = useTranslation()

  return (
    <Card className="flex w-72 shrink-0 flex-col gap-4 overflow-y-auto">
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
        <h3 className="text-sm font-semibold text-text-primary">چک‌پوینت‌های اجباری</h3>
        <CheckpointManager
          checkpoints={checkpoints}
          onRemove={onRemoveCheckpoint}
          onMove={onMoveCheckpoint}
        />
      </div>

      {result && (
        <div
          className="space-y-1 rounded-md border border-border bg-surface-raised p-3 text-xs text-text-secondary"
          data-testid="route-result-summary"
        >
          <div className="flex justify-between">
            <span>Layer</span>
            <span className="text-text-primary">{result.layer_altitude_m} m</span>
          </div>
          <div className="flex justify-between">
            <span>Distance</span>
            <span className="text-text-primary">{result.total_distance_km.toFixed(1)} km</span>
          </div>
          <div className="flex justify-between">
            <span>ETA</span>
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
