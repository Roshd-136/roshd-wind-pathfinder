import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type maplibregl from 'maplibre-gl'
import { MapView } from '../map/MapView'
import type { EditTarget } from '../../../three/manual/scene-gl'
import { PointInfoPopup } from '../map/PointInfoPopup'
import { WindSpeedLegend } from '../layers/WindSpeedLegend'
import { MobileBottomSheet } from '../../layout/MobileBottomSheet'
import { usePathfinding } from '../../../hooks/usePathfinding'
import { useWindAtPoint, useWindFields } from '../../../hooks/useWindData'
import { useRouteStore } from '../../../store/useRouteStore'
import { useUiStore } from '../../../store/useUiStore'
import type { Checkpoint, Coordinate, RouteResult, WindField, LayerVisibility } from '../../../types/routing'
import { fieldSpeedRange } from '../../../utils/windField'
import { WIND_LAYER_BANDS } from '../../../config/routing'
import { ApiError } from '../../../services/api/client'
import { PathInfoPanel } from './PathInfoPanel'
import { StepsWizard } from './StepsWizard'
import { MapTools } from '../map/MapTools'

interface RoutingMapScreenProps {
  mode: '2d' | '3d'
}

const LAYER_ALTITUDES = WIND_LAYER_BANDS.map((b) => b.fieldAltitude)

/** کلیدهای نمایش لایه‌ها — هم‌اندازهٔ باندها (۴ باند: سطحی/میانی/بالا/بالاترین).
 * پیش‌تر ۳ کلید مقابل ۴ ارتفاع نگاشت می‌شد و لایهٔ ۳۶۰۰ متری هرگز نمایش
 * داده نمی‌شد حتی با همهٔ چک‌باکس‌ها روشن. */
const LAYER_VISIBILITY_KEYS: (keyof LayerVisibility)[] = [
  'surface',
  'mid',
  'high',
  'top',
]

/**
 * پیاده‌سازی مشترک صفحات Map2D/Map3D — همان چیدمان و منطق، فقط `mode`
 * فرق می‌کند. کلیک روی نقشه بسته به گامِ ویزارد عمل می‌کند: گام ۱ =
 * مبدأ (یا جایگزینی مبدأ)، گام ۲ = مقصد (یا جایگزینی مقصد)، گام ۳ =
 * اطلاعات باد نقطه (mockup: «View wind Layers at Point»)؛ و در حالت
 * «افزودن چک‌پوینت» = گذاشتن چک‌پوینت. بازگشتِ ویزارد انتخاب‌ها را پاک
 * نمی‌کند — انتخاب فعلی سر جایش می‌ماند تا کلیک بعدی جایگزینش کند.
 */
export function RoutingMapScreen({ mode: modeProp }: RoutingMapScreenProps) {
  // حالت نقشه از استور می‌آید تا سوییچ ۲/۳بعدی «درجا» باشد (بدون ناوبری)؛
  // prop فقط مقدار اولیهٔ صفحات مستقل است.
  const mode = useUiStore((s) => s.mapMode) || modeProp
  const { t } = useTranslation()
  const {
    origin,
    destination,
    checkpoints,
    algorithm,
    constraints,
    layerVisibility,
    result,
    wizardStep,
    setOrigin,
    setDestination,
    addCheckpoint,
    removeCheckpoint,
    setCheckpointCoord,
    moveCheckpoint,
    setAlgorithm,
    setConstraints,
    setLayerVisibility,
    setResult,
    setAlternatives,
    setWizardStep,
    reset,
  } = useRouteStore()

  const [infoPoint, setInfoPoint] = useState<Coordinate | null>(null)
  const [isDemoResult, setIsDemoResult] = useState(false)
  const pathfinding = usePathfinding()
  const { fields } = useWindFields()
  const windAtPoint = useWindAtPoint(infoPoint, fields)
  const openMobileSheet = useUiStore((s) => s.openMobileSheet)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const isControlPanelOpen = useUiStore((s) => s.isControlPanelOpen)
  const toggleControlPanel = useUiStore((s) => s.toggleControlPanel)
  const viewport = useUiStore((s) => s.viewport)

  // ————— «مسیر کهنه» —————
  // اگر مبدأ/مقصد/چک‌پوینت/الگوریتم/قیدها بعد از آخرین محاسبه عوض شده باشند،
  // مسیرِ روی صفحه دیگر معتبر نیست: دکمهٔ ویزارد «محاسبه مجدد!» می‌شود (تا
  // کاربر بداند نتیجهٔ فعلی با انتخاب فعلی ساخته نشده). بدون ابطال خودکار —
  // مسیر تا وقتی کاربر دکمه را نزده سر جایش می‌ماند.
  const pointsKey = JSON.stringify([
    origin,
    destination,
    checkpoints.map((c) => [c.lat, c.lon, c.alt ?? null]),
  ])
  const settingsKey = JSON.stringify([algorithm, constraints])
  /** کلید انتخاب‌ها هنگام آخرین محاسبه — null = هنوز محاسبه‌ای در کار نبوده. */
  const [lastCalculatedKey, setLastCalculatedKey] = useState<string | null>(null)
  const isStale =
    result !== null &&
    (lastCalculatedKey === null || lastCalculatedKey !== pointsKey + settingsKey)
  function handleCalculate() {
    if (!origin || !destination) return
    // کلید انتخاب‌ها *پیش از* شروع محاسبه قفل می‌شود — تغییرهای حین محاسبه
    // مسیر را کهنه می‌کند.
    setLastCalculatedKey(pointsKey + settingsKey)
    pathfinding.mutate(
      { origin, destination, checkpoints, algorithm, constraints },
      {
        onSuccess: (routeResult) => {
          setIsDemoResult(false)
          setResult(routeResult)
        },
        // پیش‌نمایش dev بدون بک‌اند: مسیر نمایشی واقعی کریدور (خروجی
        // `scripts/export_web_wind_fixture.py` از گراف چندلایه) با برچسب صریح.
        // فقط وقتی *بک‌اند در دسترس نیست* (خطای شبکه) — خطای HTTP واقعی
        // (مثل «در این باند مسیر پروازپذیری نیست») نباید با مسیر نمایشی
        // پوشانده شود؛ همان خطا به کاربر نشان داده می‌شود.
        onError: async (error) => {
          const isHttpError =
            error instanceof ApiError ||
            (error instanceof Error && 'status' in error)
          if (isHttpError || !import.meta.env.DEV) return
          try {
            const response = await fetch('/mock/route-demo.json')
            if (!response.ok) return
            setIsDemoResult(true)
            setResult((await response.json()) as RouteResult)
          } catch {
            // بک‌اند هم نیست، فیکسچر هم نیست — خطا به حالت خودش واگذار می‌شود
          }
        },
      },
    )
  }

  /** خطای محاسبه — زیر ویزارد نشان داده می‌شود (پیام فارسی موتور). */
  const routeError = pathfinding.error

  // جریان Uber-مانند: با کامل شدن مبدأ/مقصد، شیت «تنظیمات سفر» در موبایل بالا می‌آید
  useEffect(() => {
    if (origin && destination) openMobileSheet()
  }, [origin, destination, openMobileSheet])

  // میدان‌های باد نمایان بر اساس چک‌باکس لایه‌ها — مرتب بر ارتفاع.
  // نقشهٔ رنگی و تک‌لایهٔ ۲بعدی از اولین (پایین‌ترین) می‌آید؛ در ۳بعدی همه
  // با رنگ لایه رسم می‌شوند (مثل صحنهٔ بصری‌سازی).
  const visibleFields: WindField[] = fields
    .filter((f) =>
      LAYER_VISIBILITY_KEYS.some(
        (key, i) => f.altitude_m === LAYER_ALTITUDES[i] && layerVisibility[key],
      ),
    )
    .sort((a, b) => a.altitude_m - b.altitude_m)

  // حالت «افزودن چک‌پوینت»: کلیک بعدی روی نقشه چک‌پوینت می‌گذارد (بدون نگه‌داشتن)
  const [placingCheckpointRequested, setPlacingCheckpoint] = useState(false)
  // قاعدهٔ «چک‌پوینت فقط در ۲بعدی»: در ۳بعدی گذاشتن چک‌پوینت معنا ندارد —
  // حالتِ درخواست در ۳بعدی نادیده گرفته می‌شود (حالت مشتق، بدون اثر).
  const placingCheckpoint = placingCheckpointRequested && mode !== '3d'

  // ————— ویرایشگر نقطه در صحنهٔ سه‌بعدی (گیمبال سه‌محوره) —————
  // هدف فعال گیمبال؛ در بازگشت به ۲بعدی پنهان می‌شود (فقط در ۳بعدی معنا دارد).
  const [editTarget, setEditTarget] = useState<EditTarget | null>(null)

  /** گزارش گیمبال — نقطه در مکان تازه؛ مسیر قبلی کهنه می‌شود (دکمهٔ «محاسبه مجدد»). */
  function handlePointEdit(target: EditTarget, coord: Coordinate) {
    // ارتفاع گزارش‌شده از کشیدن محور «ارتفاع» — در چک‌پوینت ذخیره می‌شود
    // (مبدأ/مقصد فقط lat/lon می‌گیرند؛ ارتفاع مسیر توسط برنامه‌ریز تعیین می‌شود).
    const withAlt = target.altM !== undefined ? { ...coord, alt: target.altM } : coord
    if (target.kind === 'origin') {
      setOrigin(coord)
    } else if (target.kind === 'destination') {
      setDestination(coord)
    } else {
      setCheckpointCoord(target.index, withAlt as Checkpoint)
    }
  }

  /**
   * کلیک روی گوی نشانگر در صحنهٔ سه‌بعدی — گیمبال همان نقطه را می‌گیرد.
   * null (کلیک خالی) گیمبال را می‌بندد؛ سپس کلیک به جریان عادی نقشه می‌رود.
   */
  function handlePointPick(target: EditTarget | null) {
    setEditTarget(mode === '3d' ? target : null)
  }

  function handleMapClick(coord: Coordinate) {
    if (placingCheckpoint) {
      addCheckpoint(coord)
      setPlacingCheckpoint(false)
      return
    }
    // نتایج کهنه ابطال خودکار نمی‌شوند — مسیر روی صفحه می‌ماند و دکمهٔ
    // ویزارد «محاسبه مجدد!» نشان می‌دهد که انتخاب‌ها عوض شده‌اند.
    if (wizardStep === 1) {
      setOrigin(coord)
      setWizardStep(2)
    } else if (wizardStep === 2) {
      setDestination(coord)
      setWizardStep(3)
    } else {
      setInfoPoint(coord)
    }
  }

  function handleClear() {
    reset()
    setIsDemoResult(false)
    setInfoPoint(null)
    setPlacingCheckpoint(false)
    setEditTarget(null)
  }

  const canClear = Boolean(origin || destination || checkpoints.length > 0 || result)

  const panel = (
    <PathInfoPanel
      algorithm={algorithm}
      onAlgorithmChange={setAlgorithm}
      layerVisibility={layerVisibility}
      onLayerVisibilityChange={setLayerVisibility}
      constraints={constraints}
      onConstraintsChange={setConstraints}
      checkpoints={checkpoints}
      onRemoveCheckpoint={removeCheckpoint}
      onMoveCheckpoint={moveCheckpoint}
      onPointInfo={() => setInfoPoint(origin)}
      canPointInfo={Boolean(origin)}
      addingCheckpoint={placingCheckpoint}
      onToggleAddCheckpoint={() => setPlacingCheckpoint((v) => !v)}
      canAddCheckpoint={Boolean(origin && destination)}
      onClear={handleClear}
      canClear={canClear}
      result={result}
      resultIsDemo={isDemoResult}
    />
  )

  return (
    // پنل کنترل روی نقشه شناور است (مطابق mockup)؛ نوار بالایی حذف شده —
    // کلید تم داخل پنل است.
    <div className="relative h-full">
      <div className="absolute inset-0">
        <MapView
          mode={mode}
          origin={origin}
          destination={destination}
          checkpoints={checkpoints}
          path={result?.path ?? null}
          path3d={result?.path_3d ?? null}
          windFields={visibleFields}
          viewport={viewport}
          onMapClick={handleMapClick}
          onReady={(m) => {
            mapRef.current = m
          }}
          editTarget={editTarget}
          onPointEdit={handlePointEdit}
          onPointPick={handlePointPick}
        />
        {visibleFields.length > 0 && (
          // راهنمای سرعت باد — وسط پایین و پهن، دور از زوم و انتساب.
          // طیف با بازهٔ *واقعی* میدان‌های نمایان برچسب می‌خورد — رنگ‌آمیزی
          // نقشه نسبی است (کمینه → آبی، بیشینه → قرمز) و طیف ثابت ۰-۲۰
          // قبلی با آن نمی‌خواند.
          <div className="absolute bottom-4 left-1/2 z-10 w-80 -translate-x-1/2 rounded-xl border border-border bg-surface/90 p-3 shadow-[var(--shadow-card)] backdrop-blur-sm">
            <div className="mb-1 text-center text-xs font-medium text-text-secondary">
              {t('legend.title')}
            </div>
            <WindSpeedLegend
              range={visibleFields.reduce<[number, number]>(
                (acc, field) => {
                  const [min, max] = fieldSpeedRange(field)
                  return [Math.min(acc[0], min), Math.max(acc[1], max)]
                },
                [Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY],
              )}
            />
          </div>
        )}
        {routeError && (
          // خطای محاسبه — پیام موتور (مثل «در باند ارتفاعی مسیر پروازپذیری
          // پیدا نشد») زیر ویزارد دیده می‌شود؛ پیش‌تر خطاها بی‌صدا ناپدید
          // می‌شدند و کاربر نمی‌فهمید چرا مسیری نیامد.
          <div
            role="alert"
            className="absolute top-28 left-1/2 z-20 w-[24rem] max-w-[94vw] -translate-x-1/2 rounded-xl border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-danger shadow-[var(--shadow-card)] backdrop-blur-sm"
          >
            {t('routing.routeError', { message: routeError.message })}
          </div>
        )}
        {/* ویزارد مراحل — قاب وسط بالا؛ بازگشت انتخابِ گام فرود را پاک می‌کند
            (کاربر باید دوباره انتخاب کند تا «بعدی» باز شود) */}
        <StepsWizard
          origin={origin}
          destination={destination}
          hasResult={Boolean(result)}
          step={wizardStep}
          onBack={() => {
            // رفتن به گام قبل، انتخاب همان گام را پاک می‌کند: گام ۲ → مقصد،
            // گام ۳ → نتیجه (مسیر روی صفحه می‌ماند ولی «انجام‌شده» نیست).
            const prev = Math.max(1, wizardStep - 1) as 1 | 2 | 3
            if (wizardStep === 2) setDestination(null)
            else if (wizardStep === 3) {
              setResult(null)
              setAlternatives([])
              setIsDemoResult(false)
            }
            setWizardStep(prev)
          }}
          onNext={() => {
            // گام بعدی فقط وقتی گام جاری ورودی خود را دارد
            const hasInput = wizardStep === 1 ? origin !== null : wizardStep === 2 ? destination !== null : true
            if (!hasInput) return
            setWizardStep(Math.min(3, wizardStep + 1) as 1 | 2 | 3)
          }}
          canNext={wizardStep === 1 ? origin !== null : wizardStep === 2 ? destination !== null : true}
          onCalculate={handleCalculate}
          canCalculate={Boolean(origin && destination)}
          isCalculating={pathfinding.isPending}
          isStale={isStale}
        />
        {infoPoint && windAtPoint.data && (
          <PointInfoPopup samples={windAtPoint.data} onClose={() => setInfoPoint(null)} />
        )}
      </div>

      {/* پنل شناور روی نقشه (دسکتاپ) — با دکمهٔ نوار ابزار تا لبه جمع می‌شود */}
      <div
        className={`absolute top-4 z-10 hidden max-h-[calc(100%-2rem)] overflow-hidden transition-all duration-300 md:block end-4 ${
          isControlPanelOpen ? 'w-[19.5rem] opacity-100' : 'w-0 opacity-0'
        }`}
        aria-hidden={!isControlPanelOpen}
      >
        {panel}
      </div>
      <MapTools
        panelOpen={isControlPanelOpen}
        onTogglePanel={toggleControlPanel}
        onZoomIn={() => mapRef.current?.zoomIn()}
        onZoomOut={() => mapRef.current?.zoomOut()}
      />
      <MobileBottomSheet title={t('trip.title')}>{panel}</MobileBottomSheet>
    </div>
  )
}
