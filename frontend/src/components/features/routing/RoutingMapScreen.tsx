import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { MapModeToggle } from '../map/MapModeToggle'
import { MapView } from '../map/MapView'
import { PointInfoPopup } from '../map/PointInfoPopup'
import { AppHeader } from '../../layout/AppHeader'
import { MobileBottomSheet } from '../../layout/MobileBottomSheet'
import { Button } from '../../ui/Button'
import { usePathfinding } from '../../../hooks/usePathfinding'
import { useWindAtPoint } from '../../../hooks/useWindData'
import { useRouteStore } from '../../../store/useRouteStore'
import type { Coordinate } from '../../../types/routing'
import { PathInfoPanel } from './PathInfoPanel'

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
export function RoutingMapScreen({ mode }: RoutingMapScreenProps) {
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
    reset,
  } = useRouteStore()

  const [infoPoint, setInfoPoint] = useState<Coordinate | null>(null)
  const pathfinding = usePathfinding()
  const windAtPoint = useWindAtPoint(infoPoint)

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
      { onSuccess: setResult },
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
      onCalculate={handleCalculate}
      isCalculating={pathfinding.isPending}
      canCalculate={Boolean(origin && destination)}
      result={result}
    />
  )

  return (
    <div className="flex h-full flex-col">
      <AppHeader />
      <div className="relative flex flex-1 flex-col md:flex-row">
      <div className="relative flex-1">
        <MapView
          mode={mode}
          origin={origin}
          destination={destination}
          checkpoints={checkpoints}
          path={result?.path ?? null}
          onMapClick={handleMapClick}
          onLongPress={addCheckpoint}
        />
        <MapModeToggle />
        {(origin || destination || checkpoints.length > 0) && (
          <Button
            variant="secondary"
            className="absolute start-4 top-16 z-10"
            onClick={reset}
          >
            {t('map.clear')}
          </Button>
        )}
        {!origin && (
          <div className="pointer-events-none absolute inset-x-0 top-16 text-center text-sm text-text-muted">
            {t('map.selectHint')}
          </div>
        )}
        {infoPoint && windAtPoint.data && (
          <PointInfoPopup samples={windAtPoint.data} onClose={() => setInfoPoint(null)} />
        )}
      </div>

      <div className="hidden p-4 md:block">{panel}</div>
      <MobileBottomSheet>{panel}</MobileBottomSheet>
      </div>
    </div>
  )
}
