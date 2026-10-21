import { RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type {
  Algorithm,
  AltitudeMode,
  Checkpoint,
  LayerVisibility,
  RouteConstraints,
  RouteResult,
} from '../../../types/routing'
import {
  ALTITUDE_MODES,
  WIND_ALTITUDE_MAX,
  altitudeBandRange,
} from '../../../config/routing'
import { formatAltitudeM, formatDistanceKm, formatDurationHours } from '../../../utils/format'
import { useFormatLang } from '../../../hooks/useFormatLang'
import { useSettingsStore } from '../../../store/useSettingsStore'
import { Button } from '../../ui/Button'
import { Card } from '../../ui/Card'
import { Collapsible } from '../../ui/Collapsible'
import { Segmented } from '../../ui/Segmented'
import { AlgorithmSelector } from './AlgorithmSelector'
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
  addingCheckpoint: boolean
  onToggleAddCheckpoint: () => void
  canAddCheckpoint: boolean
  /** پاک‌کردن کل انتخاب‌ها — دکمه در خود پنل است (نه شناور روی نقشه). */
  onClear: () => void
  canClear: boolean
  result: RouteResult | null
  /** مسیر از فیکسچر نمایشی dev آمده (بدون بک‌اند) — با برچسب صریح. */
  resultIsDemo?: boolean
}

/**
 * حالت باند ارتفاعی از وضعیت نمایش لایه‌ها استخراج می‌شود — هر چهار لایه
 * (= «همه») یا دقیقاً یکی. حالت‌های ترکیبی که با این پنل ساخته نمی‌شوند
 * (مثلاً سطحی+میانی) هم مثل «همه» نمایش داده می‌شوند.
 */
function altitudeModeOf(v: LayerVisibility): AltitudeMode {
  const active = ALTITUDE_MODES.filter((mode) => v[mode])
  return active.length === 1 ? active[0] : 'all'
}

/**
 * پنل تنظیمات مسیر — بازطراحی‌شده با سلسله‌مراتبِ تصمیم کاربر:
 * ۱) نتیجه (بعد از محاسبه در صدر پنل)، ۲) «بهینه‌سازی برای» به‌صورت سگمنت
 * (معیار، مهم‌ترین انتخاب)، ۳) محدودیت‌های پرواز (حداکثر باد + باند ارتفاع
 * یکپارچه)، ۴) چک‌پوینت‌ها، ۵) تنظیمات پیشرفته (الگوریتم
 * و اجتناب از مناطق) جمع‌شونده. تنظیمات «نمایش نقشه» جای جداگانه خود را
 * دارد (پاپ‌آور نوار ابزار) و در این پنل تکرار نمی‌شود.
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
  addingCheckpoint,
  onToggleAddCheckpoint,
  canAddCheckpoint,
  onClear,
  canClear,
  result,
  resultIsDemo = false,
}: PathInfoPanelProps) {
  void onClear
  void canClear
  const { t } = useTranslation()
  const lang = useFormatLang()
  // جهتِ چیدمانِ طیف‌نما — در فارسی (راست‌به‌چپ) نقطهٔ شروعِ سفید، راست است.
  const language = useSettingsStore((s) => s.language)
  const isRtl = language === 'fa'

  const altitudeMode = altitudeModeOf(layerVisibility)
  const band = altitudeBandRange(altitudeMode)

  /** رست‌کردن کامل فیلترها (پیش‌فرض‌ها) — بدون دست‌زدن به مبدأ/مقصد و نتیجه. */
  function handleReset() {
    onConstraintsChange({
      criterion: 'time',
      altitude_range_m: null,
      max_wind_speed_mps: null,
      avoid_zones: [],
    })
    onLayerVisibilityChange({ surface: true, mid: true, high: true, top: true })
    onAlgorithmChange('a_star')
  }

  /** رست فقط وقتی معنا دارد که چیزی برای برگرداندن وجود دارد. */
  const canReset =
    algorithm !== 'a_star' ||
    (constraints.criterion ?? 'time') !== 'time' ||
    constraints.altitude_range_m != null ||
    constraints.max_wind_speed_mps != null ||
    Boolean(constraints.avoid_zones?.length) ||
    ALTITUDE_MODES.some((mode) => !layerVisibility[mode])

  // باند ارتفاع یکپارچه: هم فیلتر نمایش لایه‌ها و هم محدودهٔ ارتفاعِ
  // درخواست مسیر را با هم تنظیم می‌کند — دو کنترلِ هم‌پوشان قبلی یکی شد.
  function applyAltitudeMode(mode: AltitudeMode) {
    onLayerVisibilityChange({
      surface: mode === 'all' || mode === 'surface',
      mid: mode === 'all' || mode === 'mid',
      high: mode === 'all' || mode === 'high',
      top: mode === 'all' || mode === 'top',
    })
    onConstraintsChange({ ...constraints, altitude_range_m: altitudeBandRange(mode) })
  }

  const sectionTitle = 'text-xs font-semibold text-text-muted'

  return (
    <Card className="no-scrollbar flex max-h-[calc(100vh-2rem)] w-full flex-col gap-4 overflow-y-auto rounded-2xl shadow-[var(--shadow-card)]">
      {/* سربرگ — عنوان پنل + بازنشانی صریحِ برچسب‌دار. یک دکمه، یک کار:
          کل انتخاب‌ها (مبدأ/مقصد/چک‌پوینت/نتیجه) پاک می‌شود؛ دکمهٔ icon-only
          قبلی و «بازنشانی فیلترها» در بخش پیشرفته، دو کار مستقل و گمراه‌کننده
          داشتند — دو دکمهٔ مشابه با دو معنا. حالا فقط همین یکی است. */}
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-text-primary">{t('routing.panelTitle')}</h2>
        <Button
          variant="outline"
          className="shrink-0 !px-2 !py-1.5"
          onClick={handleReset}
          disabled={!canReset}
          title={t('routing.resetFilters')}
          aria-label={t('routing.resetFilters')}
        >
          <RefreshCw size={14} aria-hidden />
        </Button>
      </div>

      {/* خلاصه نتیجه — بعد از محاسبه، مهم‌ترین اطلاعات بالای پنل است */}
      {result && (
        <div
          className="rounded-xl border border-border bg-surface-raised p-3 shadow-[inset_0_1px_3px_rgba(0,0,0,0.25)]"
          data-testid="route-result-summary"
        >
          {resultIsDemo && (
            <p className="mb-2 rounded bg-accent/10 px-2 py-1 text-xs text-accent">
              {t('routing.demoRoute')}
            </p>
          )}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <div className="text-sm font-bold text-text-primary">
                {formatDistanceKm(result.total_distance_km, lang)}
              </div>
              <div className="text-xs text-text-muted">{t('results.distance')}</div>
            </div>
            <div>
              <div className="text-sm font-bold text-text-primary">
                {formatDurationHours(result.estimated_time_hours, lang)}
              </div>
              <div className="text-xs text-text-muted">{t('results.eta')}</div>
            </div>
            <div>
              <div className="text-sm font-bold text-text-primary">
                {formatAltitudeM(result.layer_altitude_m, lang)}
              </div>
              <div className="text-xs text-text-muted">{t('results.layerAltitude')}</div>
            </div>
          </div>
          {/* طیف‌نمای «مقابله با باد» — زیرِ سه مقدارِ جزئیات. همین رمپ
              (سفید ۰٪ همسو با باد تا سرخ ۱۰۰٪ روبه‌باد کامل) رنگِ خط/لولهٔ
              مسیر را در هر دو نما می‌سازد. */}
          <div className="mt-3 border-t border-border pt-2">
            <p className="mb-1 text-center text-[10px] font-medium text-text-secondary">
              {t('routing.fightLegendTitle')}
            </p>
            <div
              className="h-2.5 w-full rounded-full ring-1 ring-border"
              style={{
                // توقف‌های میانی همان گامای رمپ در windFight.ts — پس طیف‌نما
                // دقیقاً همان رنگی است که خط/لوله به خود می‌گیرد.
                background: isRtl
                  ? 'linear-gradient(to left, #ffffff, #eb8383 20%, #e66262 40%, #e24a4a 60%, #df3636 80%, #dc2626)'
                  : 'linear-gradient(to right, #ffffff, #eb8383 20%, #e66262 40%, #e24a4a 60%, #df3636 80%, #dc2626)',
              }}
              aria-hidden
            />
            <div className="mt-1 flex justify-between text-[10px] text-text-muted">
              <span>{t('routing.fightZero')}</span>
              <span>{t('routing.fightHundred')}</span>
            </div>
          </div>
        </div>
      )}

      {/* بهینه‌سازی برای — مهم‌ترین انتخاب مسیر، سگمنت سه‌گزینه‌ای */}
      <section className="space-y-2">
        <h3 className={sectionTitle}>{t('routing.optimizeFor')}</h3>
        <Segmented
          ariaLabel={t('routing.optimizeFor')}
          value={constraints.criterion ?? 'time'}
          onChange={(criterion) => onConstraintsChange({ ...constraints, criterion })}
          options={[
            { value: 'time', label: t('routing.optimizeTime') },
            { value: 'energy', label: t('routing.optimizeEnergy') },
            { value: 'balanced', label: t('routing.optimizeBalanced') },
          ]}
        />
      </section>

      {/* محدودیت‌های پرواز — باند ارتفاع یکپارچه */}
      <section className="space-y-3 border-t border-border pt-3">
        <h3 className={sectionTitle}>{t('routing.flightLimits')}</h3>
        <div className="space-y-1.5">
          <Segmented
            ariaLabel={t('routing.altitudeBandLabel')}
            value={altitudeMode}
            onChange={applyAltitudeMode}
            options={[
              { value: 'all', label: t('routing.altitudeAll') },
              { value: 'surface', label: t('routing.altitudeSurface') },
              { value: 'mid', label: t('routing.altitudeMid') },
              { value: 'high', label: t('routing.altitudeHigh') },
              { value: 'top', label: t('routing.altitudeTop') },
            ]}
          />
          <p className="text-xs text-text-muted">
            {band
              ? t('routing.altitudeBand', { min: band[0], max: band[1] })
              : t('routing.altitudeAllHint', { max: WIND_ALTITUDE_MAX })}
          </p>
        </div>
      </section>

      {/* چک‌پوینت‌های اجباری */}
      <section className="space-y-2 border-t border-border pt-3">
        <h3 className={sectionTitle}>{t('routing.checkpoints')}</h3>
        <CheckpointManager
          checkpoints={checkpoints}
          onRemove={onRemoveCheckpoint}
          onMove={onMoveCheckpoint}
          adding={addingCheckpoint}
          onToggleAdd={onToggleAddCheckpoint}
          canAdd={canAddCheckpoint}
        />
      </section>

      {/* تنظیمات پیشرفته — الگوریتم و اجتناب از مناطق، جمع‌شونده */}
      <Collapsible title={t('routing.advancedSettings')}>
        <AlgorithmSelector value={algorithm} onChange={onAlgorithmChange} />
        {/* ترسیم مناطق ممنوعه هنوز پیاده‌سازی نشده — به‌جای چک‌باکس بی‌اثر،
            وضعیت صادقانه «به‌زودی» نمایش داده می‌شود */}
        <div className="rounded-md border border-dashed border-border p-2.5">
          <p className="text-xs font-medium text-text-secondary">{t('routing.avoidZones')}</p>
          <p className="mt-1 text-xs text-text-muted">{t('routing.avoidZonesHint')}</p>
          <span className="mt-1.5 inline-block rounded bg-accent/10 px-1.5 py-0.5 text-xs text-accent">
            {t('routing.comingSoon')}
          </span>
        </div>
        {/* تن‌ها الگوریتم و مناطق؛ رست یک‌پارچه در سربرگ پنل است — دو کنترل
            مشابه با دو معنا، همان گیج‌کنندگی که کاربر گزارش کرد. */}
      </Collapsible>
    </Card>
  )
}
