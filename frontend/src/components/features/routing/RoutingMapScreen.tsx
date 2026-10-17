import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type maplibregl from 'maplibre-gl'
import { MapView } from '../map/MapView'
import type { EditTarget, PickMissKind } from '../../../three/manual/scene-gl'
import { WindSpeedLegend } from '../layers/WindSpeedLegend'
import { MobileBottomSheet } from '../../layout/MobileBottomSheet'
import { usePathfinding } from '../../../hooks/usePathfinding'
import { useWindFields } from '../../../hooks/useWindData'
import { useRouteStore } from '../../../store/useRouteStore'
import { useUiStore } from '../../../store/useUiStore'
import type { Checkpoint, Coordinate, RouteResult, WindField, LayerVisibility } from '../../../types/routing'
import { fieldSpeedRange } from '../../../utils/windField'
import { WIND_LAYER_BANDS } from '../../../config/routing'
import { ApiError } from '../../../services/api/client'
import { PathInfoPanel } from './PathInfoPanel'
import { RouteErrorDialog } from './RouteErrorDialog'
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
 * فرق می‌کند. کلیک روی نقشه/دشتِ سه‌بعدی بسته به گامِ ویزارد عمل می‌کند:
 * گام ۱ = مبدأ (یا جایگزینی مبدأ)، گام ۲ = مقصد (یا جایگزینی مقصد)؛
 * و در حالت «افزودن چک‌پوینت» = گذاشتن چک‌پوینت در هر دو نما (در ۳بعدی
 * کلیک روی دشتِ زمینِ واقعی ثبت می‌شود). بازگشتِ ویزارد انتخاب‌ها را پاک
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

  const [isDemoResult, setIsDemoResult] = useState(false)
  const pathfinding = usePathfinding()
  const { fields } = useWindFields()
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

  // حالت «افزودن چک‌پوینت»: کلیک بعدی در هر دو نما چک‌پوینت می‌گذارد
  // (بدون نگه‌داشتن). در ۲بعدی کلیک روی نقشه است؛ در ۳بعدی کلیک روی دشتِ
  // زمین واقعی — پیکان‌یابی زمینی صحنه (`pickLatLon`) مختصات را می‌دهد و
  // چک‌پوینتِ بی‌ارتفاع همان‌جا روی زمین می‌نشیند؛ ارتفاع عبور را اگر
  // خواست، بعداً با گیمبالِ همان نقطه بالا می‌کشد.
  const [placingCheckpoint, setPlacingCheckpoint] = useState(false)
  // بازخورد لحظه‌ای ثبت/شکست چک‌پوینت — «هیچ اتفاقی نیفتاد» بی‌سکوت
  // را برای کاربر و دیباگ می‌شکند؛ ثبت: «#n ثبت شد»، شکست برداشت:
  // «اینجا قابل برداشت نیست».
  const [cpFlash, setCpFlash] = useState<
    { kind: 'ok'; n: number } | { kind: 'miss'; reason: PickMissKind } | null
  >(null)
  const cpFlashTimerRef = useRef<number | null>(null)
  const scheduleCpFlashClear = (ms: number): void => {
    if (cpFlashTimerRef.current) window.clearTimeout(cpFlashTimerRef.current)
    cpFlashTimerRef.current = window.setTimeout(
      () => setCpFlash(null),
      ms,
    )
  }

  // نشانگر متقاطع روی بوم نقشه در حالت افزودن چک‌پوینت — کاربر باید بفهمد
  // کلیک بعدی «یک حالت خاص» را ثبت می‌کند. (بوم ۳بعدی افق جدید را از
  // `ManualSceneView` می‌گیرد — نشاندن نشانگر متقاطع آن‌جا هم همان prop است.)
  useEffect(() => {
    const canvas = mapRef.current?.getCanvas()
    if (!canvas) return
    canvas.style.cursor = placingCheckpoint ? 'crosshair' : ''
    return () => {
      canvas.style.cursor = ''
    }
  }, [placingCheckpoint])

  // کلیک برداشتنیِ «افزودن چک‌پوینت» در ۳بعدی که مختصات نداد (بیرون باندِ
  // پذیرش/پرتو به دشت نرسید) — بازخورد صریح، نه بی‌صدایی.
  function handlePlacingMiss(kind: PickMissKind) {
    setCpFlash({ kind: 'miss', reason: kind })
    scheduleCpFlashClear(2400)
  }

  // خروج از حالت افزودن با Esc — مثل همهٔ حالت‌های «کلیک بعدی»
  useEffect(() => {
    if (!placingCheckpoint) return
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') setPlacingCheckpoint(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [placingCheckpoint])

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
      setCpFlash({ kind: 'ok', n: checkpoints.length + 1 })
      scheduleCpFlashClear(1600)
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
    }
    // گام ۳: کلیک آزاد ناترقی است — نقشه «به‌هرجای‌خوردی» پاسخ نمی‌دهد؛
    // جابه‌جایی نقطه از همان نشانگر (یا گیمبال در ۳بعدی) انجام می‌شود.
  }

  function handleClear() {
    reset()
    setIsDemoResult(false)
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
      addingCheckpoint={placingCheckpoint}
      onToggleAddCheckpoint={() => setPlacingCheckpoint((v) => !v)}
      // در هر دو نما چک‌پوینت می‌گذاریم؛ حتی در ۳بعدی کلیک روی دشتِ زمینِ
      // واقعی مختصات واقعی می‌دهد (پیش‌تر قاعدهٔ «فقط ۲بعدی» بود و کاربر
      // در نمای ۳بعدی عملاً راهی برای گذاشتن چک‌پوینت نداشت). پیش‌شرط
      // همان است: مبدأ و مقصد باید انتخاب شده باشند — و در ۳بعدی صحنه
      // پیش از محاسبهٔ اولین مسیر هنوز mount نشده (کلیک پذنده نمی‌شود)،
      // پس آن‌جا دکمه تا برخاستنِ مسیر قطع است.
      canAddCheckpoint={
        Boolean(origin && destination) &&
        (mode !== '3d' || Boolean(result))
      }
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
          placingPoint={placingCheckpoint}
          onPointEdit={handlePointEdit}
          onPointPick={handlePointPick}
          onPickMiss={handlePlacingMiss}
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
        {placingCheckpoint && (
          // راهنمای حالت افزودن چک‌پوینت — دکمهٔ «در حال افزودن» به‌تنهایی
          // کافی نبود؛ کاربر نمی‌فهمید باید روی خودِ نقشه کلیک کند.
          <div
            role="status"
            className="absolute bottom-24 left-1/2 z-20 w-max max-w-[94vw] -translate-x-1/2 rounded-xl border border-accent/50 bg-accent/15 px-3 py-2 text-xs font-medium text-accent shadow-[var(--shadow-card)] backdrop-blur-sm"
          >
            {t('routing.checkpointPlacingHint')}
          </div>
        )}
        {cpFlash && (
          // بازخورد لحظه‌ای ثبت/شکست چک‌پوینت — پایینِ وسط (بالای راهنمای
          // مسلح؛ زیرِ بنر ویزارد نمی‌نشیند) — «هیچ‌چیز نشد» بی‌سکوت
          // را برای کاربر و دیباگ می‌شکند.
          <div
            role="status"
            className={`absolute ${placingCheckpoint ? 'bottom-36' : 'bottom-24'} left-1/2 z-20 w-max max-w-[94vw] -translate-x-1/2 rounded-xl border px-3 py-2 text-xs font-medium shadow-[var(--shadow-card)] backdrop-blur-sm ${
              cpFlash.kind === 'ok'
                ? 'border-emerald-500/50 bg-emerald-500/15 text-emerald-300'
                : 'border-amber-500/60 bg-amber-500/15 text-amber-300'
            }`}
          >
            {cpFlash.kind === 'ok'
              ? t('routing.checkpointPlaced', { n: cpFlash.n })
              : cpFlash.reason === 'sky'
                ? t('routing.checkpointPickMissSky')
                : t('routing.checkpointPickMissOutside')}
          </div>
        )}
        {routeError && (
          // خطای محاسبه در فریم جدای مودال — پیام فارسی موتور (مثل «در باند
          // ارتفاعی مسیر پروازپذیری پیدا نشد»). بنر کوچک روی نقشه قبلاً در
          // شلوغی گم می‌شد؛ کاربر خواست خطا کادر مستقل بگیرد.
          <RouteErrorDialog
            message={t('routing.routeError', { message: routeError.message })}
            onClose={() => pathfinding.reset()}
          />
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
      </div>

      {/* پنل شناور روی نقشه (دسکتاپ) — باز/جمع‌شدن با لغزش نرم به بیرون +
          محو؛ عرض ثابت می‌ماند تا محتوا هنگام انیمیشن له نشود (قبلاً با
          فشردن عرض، سریع «می‌پرید»). لغزش به سمت لبهٔ end — در RTL چپ و
          در LTR راست؛ در حالت بسته pointer-events خاموش می‌شود تا غلافِ
          پنل، نقشهٔ زیرش را برای کلیک/جابه‌جایی مسدود نکند. */}
      <div
        className={`absolute top-4 end-4 z-10 hidden max-h-[calc(100%-2rem)] w-[19.5rem] overflow-hidden md:block ${
          isControlPanelOpen ? 'pointer-events-auto' : 'pointer-events-none'
        }`}
      >
        <div
          className={`h-full transition-[translate,opacity,visibility] duration-300 ease-out will-change-transform ${
            isControlPanelOpen
              ? 'visible translate-x-0 opacity-100'
              : 'invisible opacity-0 ltr:translate-x-[110%] rtl:-translate-x-[110%]'
          }`}
          aria-hidden={!isControlPanelOpen}
        >
          {panel}
        </div>
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
