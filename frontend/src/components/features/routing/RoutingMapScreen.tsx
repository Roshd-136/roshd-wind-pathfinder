import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type maplibregl from 'maplibre-gl'
import { MapView } from '../map/MapView'
import { PointInfoPopup } from '../map/PointInfoPopup'
import { WindSpeedLegend } from '../layers/WindSpeedLegend'
import { MobileBottomSheet } from '../../layout/MobileBottomSheet'
import { usePathfinding } from '../../../hooks/usePathfinding'
import { useWindAtPoint, useWindFields } from '../../../hooks/useWindData'
import { useRouteStore } from '../../../store/useRouteStore'
import { useUiStore } from '../../../store/useUiStore'
import type { Coordinate, RouteResult, WindField } from '../../../types/routing'
import { PathInfoPanel } from './PathInfoPanel'
import { StepsWizard } from './StepsWizard'
import { MapTools } from '../map/MapTools'

interface RoutingMapScreenProps {
  mode: '2d' | '3d'
}

/** لایه‌های باد در بازهٔ هر چک‌باکس (AGL) — برای فیلتر میدان‌های نمایان. */
const LAYER_ALTITUDES = [50, 200, 500] as const

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
    moveCheckpoint,
    setAlgorithm,
    setConstraints,
    setLayerVisibility,
    setResult,
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

  // جریان Uber-مانند: با کامل شدن مبدأ/مقصد، شیت «تنظیمات سفر» در موبایل بالا می‌آید
  useEffect(() => {
    if (origin && destination) openMobileSheet()
  }, [origin, destination, openMobileSheet])

  // میدان‌های باد نمایان بر اساس چک‌باکس لایه‌ها — مرتب بر ارتفاع.
  // نقشهٔ رنگی و تک‌لایهٔ ۲بعدی از اولین (پایین‌ترین) می‌آید؛ در ۳بعدی همه
  // با رنگ لایه رسم می‌شوند (مثل صحنهٔ بصری‌سازی).
  const visibleFields: WindField[] = fields
    .filter((f) =>
      LAYER_ALTITUDES.some(
        (a, i) =>
          f.altitude_m === a &&
          (i === 0
            ? layerVisibility.surface
            : i === 1
              ? layerVisibility.mid
              : layerVisibility.high),
      ),
    )
    .sort((a, b) => a.altitude_m - b.altitude_m)

  // حالت «افزودن چک‌پوینت»: کلیک بعدی روی نقشه چک‌پوینت می‌گذارد (بدون نگه‌داشتن)
  const [placingCheckpoint, setPlacingCheckpoint] = useState(false)

  function handleMapClick(coord: Coordinate) {
    if (placingCheckpoint) {
      addCheckpoint(coord)
      setPlacingCheckpoint(false)
      return
    }
    // نتایج کهنه بعد از تغییر نقاط اعتبار ندارند — پاک می‌شوند؛ خودِ
    // انتخاب‌ها سر جایشان می‌مانند (جایگزینی، نه حذف).
    const invalidate = () => {
      if (result) setResult(null)
      setIsDemoResult(false)
    }
    if (wizardStep === 1) {
      invalidate()
      setOrigin(coord)
      setWizardStep(2)
    } else if (wizardStep === 2) {
      invalidate()
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
  }

  function handleCalculate() {
    if (!origin || !destination) return
    pathfinding.mutate(
      { origin, destination, checkpoints, algorithm, constraints },
      {
        onSuccess: (routeResult) => {
          setIsDemoResult(false)
          setResult(routeResult)
        },
        // پیش‌نمایش dev بدون بک‌اند: مسیر نمایشی واقعی کریدور (خروجی
        // `scripts/export_web_wind_fixture.py` از گراف چندلایه) با برچسب صریح.
        onError: async () => {
          if (!import.meta.env.DEV) return
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
          windFields={visibleFields}
          viewport={viewport}
          onMapClick={handleMapClick}
          onReady={(m) => {
            mapRef.current = m
          }}
        />
        {visibleFields.length > 0 && (
          // راهنمای سرعت باد — وسط پایین و پهن، دور از زوم و انتساب
          <div className="absolute bottom-4 left-1/2 z-10 w-80 -translate-x-1/2 rounded-xl border border-border bg-surface/90 p-3 shadow-[var(--shadow-card)] backdrop-blur-sm">
            <div className="mb-1 text-center text-xs font-medium text-text-secondary">
              {t('legend.title')}
            </div>
            <WindSpeedLegend />
          </div>
        )}
        {/* ویزارد مراحل — قاب وسط بالا؛ بازگشت انتخاب را پاک نمی‌کند */}
        <StepsWizard
          origin={origin}
          destination={destination}
          hasResult={Boolean(result)}
          step={wizardStep}
          onBack={() => setWizardStep(Math.max(1, wizardStep - 1) as 1 | 2 | 3)}
          onNext={() => setWizardStep(Math.min(3, wizardStep + 1) as 1 | 2 | 3)}
          onCalculate={handleCalculate}
          canCalculate={Boolean(origin && destination)}
          isCalculating={pathfinding.isPending}
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
