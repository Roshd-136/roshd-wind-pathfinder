import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type maplibregl from 'maplibre-gl'
import { MapView } from '../map/MapView'
import { PointInfoPopup } from '../map/PointInfoPopup'
import { WindSpeedLegend } from '../layers/WindSpeedLegend'
import { MobileBottomSheet } from '../../layout/MobileBottomSheet'
import { Button } from '../../ui/Button'
import { usePathfinding } from '../../../hooks/usePathfinding'
import { useWindAtPoint, useWindFields } from '../../../hooks/useWindData'
import { useRouteStore } from '../../../store/useRouteStore'
import { useUiStore } from '../../../store/useUiStore'
import type { Coordinate, RouteResult } from '../../../types/routing'
import { PathInfoPanel } from './PathInfoPanel'
import { StepsWizard } from './StepsWizard'
import { MapTools } from '../map/MapTools'

interface RoutingMapScreenProps {
  mode: '2d' | '3d'
}

/**
 * پیاده‌سازی مشترک صفحات Map2D/Map3D — همان چیدمان و منطق، فقط `mode`
 * فرق می‌کند. جریان روی نقشه: کلیک ۱=مبدأ، کلیک ۲=مقصد، کلیک‌های بعدی=
 * نمایش اطلاعات باد آن نقطه (mockup: «View wind Layers at Point»)، و
 * long-press=افزودن چک‌پوینت اجباری. دکمه «پاک کردن» همه را ریست می‌کند.
 * همه در `useRouteStore` نگه داشته می‌شود تا toggle دوحالته ۲/۳ بعدی
 * (ناوبری واقعی بین دو route) چیزی را از دست ندهد.
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
    setOrigin,
    setDestination,
    addCheckpoint,
    removeCheckpoint,
    moveCheckpoint,
    setAlgorithm,
    setConstraints,
    setLayerVisibility,
    setResult,
    goBackStep,
    reset,
  } = useRouteStore()

  const [infoPoint, setInfoPoint] = useState<Coordinate | null>(null)
  const [isDemoResult, setIsDemoResult] = useState(false)
  const pathfinding = usePathfinding()
  const { fields } = useWindFields()
  const windAtPoint = useWindAtPoint(infoPoint, fields)
  const openMobileSheet = useUiStore((s) => s.openMobileSheet)
  const sidebarOpen = useUiStore((s) => s.isSidebarOpen)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const isControlPanelOpen = useUiStore((s) => s.isControlPanelOpen)
  const toggleControlPanel = useUiStore((s) => s.toggleControlPanel)

  // جریان Uber-مانند: با کامل شدن مبدأ/مقصد، شیت «تنظیمات سفر» در موبایل بالا می‌آید
  useEffect(() => {
    if (origin && destination) openMobileSheet()
  }, [origin, destination, openMobileSheet])

  // لایهٔ فعال میدان باد = اولین لایهٔ قابل‌مشاهده (سطحی → میانی → بالا).
  const activeField =
    fields.find(
      (f) =>
        (layerVisibility.surface && f.altitude_m === 50) ||
        (layerVisibility.mid && f.altitude_m === 200) ||
        (layerVisibility.high && f.altitude_m === 500),
    ) ?? null

  function handleMapClick(coord: Coordinate) {
    if (!origin) {
      setOrigin(coord)
    } else if (!destination) {
      setDestination(coord)
    } else {
      setInfoPoint(coord)
    }
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
          windField={activeField}
          onMapClick={handleMapClick}
          onLongPress={addCheckpoint}
          onReady={(m) => {
            mapRef.current = m
          }}
        />
        {activeField && (
          // راهنمای سرعت باد — وسط پایین و پهن، دور از زوم و انتساب
          <div className="absolute bottom-4 left-1/2 z-10 w-80 -translate-x-1/2 rounded-xl border border-border bg-surface/90 p-3 shadow-[var(--shadow-card)] backdrop-blur-sm">
            <div className="mb-1 text-center text-xs font-medium text-text-secondary">
              {t('legend.title')}
            </div>
            <WindSpeedLegend />
          </div>
        )}
        {(origin || destination || checkpoints.length > 0) && (
          <Button
            variant="secondary"
            className={`absolute top-16 z-10 ${sidebarOpen ? "start-4" : "start-16"}`}
            onClick={reset}
          >
            {t('map.clear')}
          </Button>
        )}
        {/* ویزارد مراحل — قاب وسط بالا با اسلاید افقی */}
        <StepsWizard
          origin={origin}
          destination={destination}
          hasResult={Boolean(result)}
          onBack={() => goBackStep()}
          canBack={Boolean(destination || result || origin)}
          onCalculate={handleCalculate}
          canCalculate={Boolean(origin && destination)}
          isCalculating={pathfinding.isPending}
        />
        {infoPoint && windAtPoint.data && (
          <PointInfoPopup samples={windAtPoint.data} onClose={() => setInfoPoint(null)} />
        )}
      </div>

      {/* پنل شناور روی نقشه (دسکتاپ) — همیشه نمایان */}
      <div className="absolute top-4 z-10 hidden max-h-[calc(100%-2rem)] w-[19.5rem] md:block end-4">
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
