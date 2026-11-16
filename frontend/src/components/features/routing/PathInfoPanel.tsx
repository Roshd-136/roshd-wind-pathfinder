import { RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type {
  Algorithm,
  AltitudeMode,
  Checkpoint,
  Coordinate,
  LayerVisibility,
  RouteConstraints,
  RouteResult,
} from '../../../types/routing'
import {
  ALTITUDE_MODES,
  WIND_ALTITUDE_MAX,
  altitudeBandRange,
} from '../../../config/routing'
import { greatCircleDistanceKm } from '../../../utils/geo'
import {
  formatAltitudeM,
  formatDistanceKm,
  formatDurationHours,
  formatSpeedMps,
  toFaDigits,
} from '../../../utils/format'
import { useFormatLang } from '../../../hooks/useFormatLang'
import { Button } from '../../ui/Button'
import { Card } from '../../ui/Card'
import { Collapsible } from '../../ui/Collapsible'
import { Segmented } from '../../ui/Segmented'
import { AlgorithmSelector } from './AlgorithmSelector'
import { CheckpointManager } from './CheckpointManager'
import { PlaceLabel } from './PlaceLabel'
import { TextField } from '../../ui/TextField'

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
  /** مبدا/مقصد برای بخش «همیشه‌دید» و مقایسهٔ خط مستقیم (کامنت ۹). */
  origin: Coordinate | null
  destination: Coordinate | null
  /** سرعت میانگین باد نزدیک‌ترین لایهٔ نمایان به لایهٔ پروازِ نتیجه —
   * برای گزارهٔ «سرعت موتور ≈ سرعت باد» (کامنت ۷). */
  windSpeedAtLayer?: { altitudeM: number; speedMps: number } | null
  /** ثبت ارتفاع اجباری چک‌پوینت (کامنت ۸) — به CheckpointManager پاس می‌شود. */
  onSetCheckpointAltitude?: (index: number, alt: number | null) => void
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
 * ۱) نتیجه (بعد از محاسبه در صدر پنل)، ۲) «مبدا و مقصد» همیشه‌دید با خط
 * مستقیم هوایی (کامنت ۹ «کامنت‌های نرم‌افزار»)، ۳) «بهینه‌سازی برای»
 * به‌صورت سگمنت (معیار، مهم‌ترین انتخاب)، ۴) محدودیت‌های پرواز (حداکثر باد
 * + باند ارتفاع یکپارچه)، ۵) چک‌پوینت‌ها، ۶) تنظیمات پیشرفته (الگوریتم،
 * سرعت موتور و اجتناب از مناطق) جمع‌شونده. تنظیمات «نمایش نقشه» جای جداگانه خود را
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
  origin,
  destination,
  windSpeedAtLayer = null,
  onSetCheckpointAltitude,
}: PathInfoPanelProps) {
  void onClear
  void canClear
  const { t } = useTranslation()
  const lang = useFormatLang()

  // ————— سرعت موتور (کامنت ۷) —————
  // پیشنویسِ متنی برای اینکه نقطهٔ اعشار میانی (مثل «7.») خورده نشود.
  // `committed` مقداری است که این پیشنویس همراهِ آن معتبر است: هر بار که
  // vessel بیرونی مقدار دیگری شود (مثل رست)، پیشنویس خودبهخود بیاعتبار
  // میشود و نمایش به مقدار vessel برمیگردد — بدون اثرِ setState-in-effect.
  const [motorDraft, setMotorDraft] = useState<{
    text: string
    committed: number | null
  } | null>(null)
  const vesselSpeed = constraints.vessel?.airspeed_mps
  const motorText =
    motorDraft && motorDraft.committed === vesselSpeed
      ? motorDraft.text
      : vesselSpeed != null
        ? String(vesselSpeed)
        : ''

  function handleMotorChange(text: string) {
    const trimmed = text.trim()
    if (trimmed === '') {
      // خالی = حذف vessel — پیشفرض موتور بکاند (۲۰ m/s)
      setMotorDraft({ text, committed: null })
      const rest: RouteConstraints = { ...constraints }
      delete rest.vessel
      onConstraintsChange(rest)
      return
    }
    const value = Number(trimmed)
    if (Number.isFinite(value) && value > 0) {
      setMotorDraft({ text, committed: value })
      onConstraintsChange({
        ...constraints,
        vessel: {
          type: 'aircraft',
          airspeed_mps: value,
          induced_drag_coeff: 0.3,
          headwind_penalty_coeff: 0.25,
        },
      })
      return
    }
    // نیمهکاره/نامعتبر: پیشنویس تا وقتی vessel عوض نشده میماند —
    // آخرین مقدار معتبر میماند
    setMotorDraft({ text, committed: vesselSpeed ?? null })
  }

  // گزارهٔ «سرعت موتور ≈ سرعت باد این لایه» — اختلاف تا ۵٪ باد
  const motorMatchesWind =
    result != null &&
    windSpeedAtLayer != null &&
    vesselSpeed != null &&
    Math.abs(vesselSpeed - windSpeedAtLayer.speedMps) <=
      0.05 * windSpeedAtLayer.speedMps

  const altitudeMode = altitudeModeOf(layerVisibility)
  const band = altitudeBandRange(altitudeMode)

  // خط مستقیم هوایی و مقایسه با مسیر پیشنهادی (کامنت ۹) — پیش‌محاسبه خارج
  // از JSX تا شاخه‌بندی خوانا بماند.
  const straightKm =
    origin && destination ? greatCircleDistanceKm(origin, destination) : null
  const comparison = (() => {
    if (!result || straightKm == null || straightKm === 0) return null
    const percent = Math.round(((result.total_distance_km - straightKm) / straightKm) * 100)
    const sign = percent >= 0 ? '+' : '−'
    const magnitude = toFaDigits(String(Math.abs(percent)))
    const percentText = lang === 'fa' ? `${sign}${magnitude}٪` : `${sign}${Math.abs(percent)}%`
    return t('routing.straightVsRoute', {
      route: formatDistanceKm(result.total_distance_km, lang),
      straight: formatDistanceKm(straightKm, lang),
      percent: percentText,
    })
  })()

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
    constraints.vessel != null ||
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
        {/* عنوان پنل فقط دسکتاپ — در موبایل سربرگِ شیت «تنظیمات سفر» را
            نشان میدهد و این h2 زیرش تکرار میشد (بازخورد تست موبایل). */}
        <h2 className="max-md:hidden text-sm font-semibold text-text-primary">
          {t('routing.panelTitle')}
        </h2>
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

      {/* مبدا و مقصد — همیشه‌دید (کامنت ۹ «کامنت‌های نرم‌افزار»): کاربر
          پیش‌تر بعد از محاسبه، مبدأ/مقصدِ انتخابی و میزان انحراف مسیر از
          خط مستقیم را نمی‌دید؛ حالا نام مکان (ژئوکدینگ معکوس آزاد OSM)،
          مختصاتِ جایگزین، خط مستقیم هوایی و مقایسه با مسیر پیشنهادی
          همیشه در پنل است. */}
      <section className="space-y-1.5" data-testid="points-summary">
        <h3 className={sectionTitle}>{t('routing.pointsTitle')}</h3>
        <div className="space-y-1 text-xs">
          <div className="flex items-baseline justify-between gap-2">
            <span className="shrink-0 text-text-muted">{t('routing.origin')}</span>
            <span className="text-end text-text-primary">
              {origin ? <PlaceLabel point={origin} /> : t('routing.notSelected')}
            </span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="shrink-0 text-text-muted">{t('routing.destination')}</span>
            <span className="text-end text-text-primary">
              {destination ? <PlaceLabel point={destination} /> : t('routing.notSelected')}
            </span>
          </div>
          {straightKm != null && (
            <div className="flex items-baseline justify-between gap-2" data-testid="straight-line">
              <span className="shrink-0 text-text-muted">{t('routing.straightLine')}</span>
              <span className="text-end font-medium text-text-primary">
                {formatDistanceKm(straightKm, lang)}
              </span>
            </div>
          )}
          {comparison && (
            <p className="leading-5 text-text-muted" data-testid="straight-comparison">
              {comparison}
            </p>
          )}
          {!origin && !destination && (
            <p className="leading-5 text-text-muted">{t('routing.pickPointsHint')}</p>
          )}
        </div>
      </section>

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
          onSetAltitude={onSetCheckpointAltitude}
        />
      </section>

      {/* تنظیمات پیشرفته — الگوریتم، سرعت موتور و اجتناب از مناطق، جمع‌شونده */}
      <Collapsible title={t('routing.advancedSettings')}>
        <AlgorithmSelector value={algorithm} onChange={onAlgorithmChange} />
        {/* سرعت موتور جهانی مسیر (کامنت ۷ «کامنت‌های نرم‌افزار») — برای
            قطعههای مخالف باد؛ خالی = پیشفرض بکاند. گزارهٔ بادِ لایهٔ
            پرواز به کاربر کمک میکند مقدار را آگاهانه انتخاب کند. */}
        <div className="space-y-1.5">
          <TextField
            label={t('routing.motorSpeed')}
            type="text"
            inputMode="decimal"
            className="max-w-[12rem]"
            data-testid="motor-speed-input"
            value={motorText}
            placeholder="20"
            onChange={(event) => handleMotorChange(event.target.value)}
          />
          <p className="text-xs text-text-muted">{t('routing.motorSpeedHint')}</p>
          {result != null && windSpeedAtLayer != null && (
            <div className="rounded-md border border-border bg-surface-raised p-2" data-testid="wind-at-layer">
              <p className="text-xs text-text-secondary">
                {t('routing.windAtFlightLayer', {
                  alt: formatAltitudeM(windSpeedAtLayer.altitudeM, lang),
                  speed: formatSpeedMps(windSpeedAtLayer.speedMps, lang),
                })}
              </p>
              {motorMatchesWind && (
                <p className="mt-1 text-xs font-medium text-accent" data-testid="motor-matches-wind">
                  {t('routing.motorMatchesWind')}
                </p>
              )}
            </div>
          )}
        </div>
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
