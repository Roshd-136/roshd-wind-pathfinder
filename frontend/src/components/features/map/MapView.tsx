import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import type { Coordinate, WindField } from '../../../types/routing'
import { addWindLayers, applyWindField } from './windFieldLayer'

interface MapViewProps {
  mode: '2d' | '3d'
  origin: Coordinate | null
  destination: Coordinate | null
  checkpoints?: Coordinate[]
  path: Coordinate[] | null
  /** میدان باد لایهٔ فعال — نقشهٔ حرارتی + پیکان‌ها (اختیاری). */
  windField?: WindField | null
  onMapClick: (coord: Coordinate) => void
  /** کلیک بعد از تعیین مبدأ/مقصد — نمایش لایه‌های باد در آن نقطه. */
  onPointInfo?: (coord: Coordinate) => void
  /** long-press روی نقشه — برای افزودن چک‌پوینت یا اطلاعات نقطه. */
  onLongPress?: (coord: Coordinate) => void
}

const ROUTE_SOURCE_ID = 'route-line'
const ROUTE_LAYER_ID = 'route-line-layer'
const ROUTE_DOTS_SOURCE_ID = 'route-dots'
const ROUTE_DOTS_LAYER_ID = 'route-dots-layer'

/**
 * نقشه اصلی (Mapbox GL JS) — مطابق mockup: کلیک اول = مبدأ (پین سبز)،
 * کلیک دوم = مقصد (پین قرمز)، و اگر `path` موجود باشد رسم مسیر.
 * حالت 3D با `map.setPitch`/`setTerrain` فعال می‌شود (نیازمند DEM tiles).
 *
 * بدون توکن Mapbox، به‌جای رندر شکسته یا mock، پیام واضح نشان می‌دهد —
 * توکن باید در `.env.local` به‌عنوان `VITE_MAPBOX_TOKEN` تنظیم شود.
 */
export function MapView({
  mode,
  origin,
  destination,
  checkpoints = [],
  path,
  windField = null,
  onMapClick,
  onPointInfo,
  onLongPress,
}: MapViewProps) {
  const { t } = useTranslation()
  // در بدنه کامپوننت خوانده می‌شود (نه در سطح ماژول) تا با vi.stubEnv در
  // تست و تغییر `.env.local` در حالت dev، مقدار به‌روز خوانده شود.
  const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const originMarkerRef = useRef<mapboxgl.Marker | null>(null)
  const destinationMarkerRef = useRef<mapboxgl.Marker | null>(null)
  const checkpointMarkersRef = useRef<mapboxgl.Marker[]>([])
  // هندلرهای کلیک در ref نگه داشته می‌شوند تا map فقط یک‌بار ساخته شود
  // ولی همیشه آخرین کلوژرها را صدا بزند.
  const handlersRef = useRef({ origin, destination, onMapClick, onPointInfo, onLongPress })
  useEffect(() => {
    handlersRef.current = { origin, destination, onMapClick, onPointInfo, onLongPress }
  })

  // میدان باد در ref نگه داشته می‌شود تا وقتی map لایه‌هایش را افزود (به‌صورت
  // ناهمگام بعد از load)، آخرین میدان بلافاصله اعمال شود.
  const windFieldRef = useRef<WindField | null>(windField)
  useEffect(() => {
    windFieldRef.current = windField
    const map = mapRef.current
    if (map) applyWindField(map, windField)
  }, [windField])

  useEffect(() => {
    if (!MAPBOX_TOKEN || !containerRef.current || mapRef.current) return

    mapboxgl.accessToken = MAPBOX_TOKEN
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [58.65, 36.18], // مرکز کریدور مسیریابی (مطابق میدان باد نمایشی)
      zoom: 7,
    })
    map.addControl(new mapboxgl.NavigationControl(), document.documentElement.dir === 'rtl' ? 'bottom-left' : 'bottom-right')

    // long-press: نگه‌داشتن ۵۰۰ms بدون جابه‌جایی، بعد رها کردن بدون drag.
    // اگر long-press رخ دهد، کلیک بعدی نادیده گرفته می‌شود.
    let pressTimer: ReturnType<typeof setTimeout> | null = null
    let pressStart: mapboxgl.Point | null = null
    let longPressFired = false

    const clearPress = () => {
      if (pressTimer) clearTimeout(pressTimer)
      pressTimer = null
      pressStart = null
    }

    map.on('mousedown', (e) => {
      if (e.originalEvent.button !== 0) return
      longPressFired = false
      pressStart = e.point
      pressTimer = setTimeout(() => {
        longPressFired = true
        handlersRef.current.onLongPress?.({ lat: e.lngLat.lat, lon: e.lngLat.lng })
      }, 500)
    })

    map.on('mousemove', (e) => {
      if (!pressStart || !pressTimer) return
      if (e.point.dist(pressStart) > 6) clearPress()
    })

    map.on('mouseup', clearPress)
    map.on('dragstart', clearPress)

    map.on('click', (e) => {
      // ترتیب اولویت کلیک: مبدأ → مقصد → اطلاعات نقطه (mockup: «View wind
      // Layers at Point»). چک‌پوینت با long-press اضافه می‌شود.
      if (longPressFired) {
        longPressFired = false
        return
      }
      const coord = { lat: e.lngLat.lat, lon: e.lngLat.lng }
      const h = handlersRef.current
      if (!h.origin || !h.destination) h.onMapClick(coord)
      else h.onPointInfo?.(coord)
    })

    map.on('load', () => {
      map.addSource(ROUTE_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: [] } },
      })
      // خط مسیر سفید + نقاط سفید — مطابق mockup
      map.addLayer({
        id: ROUTE_LAYER_ID,
        type: 'line',
        source: ROUTE_SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': '#f8fafc',
          'line-width': 4,
          'line-blur': 0.2,
        },
      })
      map.addSource(ROUTE_DOTS_SOURCE_ID, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: ROUTE_DOTS_LAYER_ID,
        type: 'circle',
        source: ROUTE_DOTS_SOURCE_ID,
        paint: {
          'circle-radius': 3.2,
          'circle-color': '#f8fafc',
          'circle-stroke-color': 'rgba(10, 14, 26, 0.4)',
          'circle-stroke-width': 1,
        },
      })
      // میدان باد: نقشهٔ حرارتی + پیکان‌ها (زیر خط مسیر)
      addWindLayers(map)
      applyWindField(map, windFieldRef.current)
    })

    mapRef.current = map
    return () => {
      clearPress()
      map.remove()
      mapRef.current = null
    }
  }, [MAPBOX_TOKEN])

  // pitch/bearing برای toggle حالت 3D
  useEffect(() => {
    mapRef.current?.easeTo({ pitch: mode === '3d' ? 60 : 0, duration: 400 })
  }, [mode])

  // نشانگر مبدأ
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (origin) {
      if (!originMarkerRef.current) {
        originMarkerRef.current = new mapboxgl.Marker({ color: '#22c55e' })
      }
      originMarkerRef.current.setLngLat([origin.lon, origin.lat]).addTo(map)
    } else {
      originMarkerRef.current?.remove()
    }
  }, [origin])

  // نشانگر مقصد
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (destination) {
      if (!destinationMarkerRef.current) {
        destinationMarkerRef.current = new mapboxgl.Marker({ color: '#ef4444' })
      }
      destinationMarkerRef.current.setLngLat([destination.lon, destination.lat]).addTo(map)
    } else {
      destinationMarkerRef.current?.remove()
    }
  }, [destination])

  // نشانگر چک‌پوینت‌های اجباری — با شماره ترتیب روی پین
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    checkpointMarkersRef.current.forEach((m) => m.remove())
    checkpointMarkersRef.current = checkpoints.map((cp, i) => {
      const el = document.createElement('div')
      el.className =
        'flex h-6 w-6 items-center justify-center rounded-full bg-accent text-xs font-bold text-white'
      el.textContent = String(i + 1)
      return new mapboxgl.Marker({ element: el }).setLngLat([cp.lon, cp.lat]).addTo(map)
    })
  }, [checkpoints])

  // رسم خط مسیر + نقاط سفید روی آن (مطابق mockup)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const source = map.getSource(ROUTE_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    source?.setData({
      type: 'Feature',
      properties: {},
      geometry: {
        type: 'LineString',
        coordinates: (path ?? []).map((c) => [c.lon, c.lat]),
      },
    })
    const dots = map.getSource(ROUTE_DOTS_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    dots?.setData({
      type: 'FeatureCollection',
      features: (path ?? [])
        // هر n امین نقطه تا تراکم نقاط شبیه mockup بماند
        .filter((_, i) => i % Math.max(1, Math.ceil((path?.length ?? 1) / 24)) === 0)
        .map((c) => ({
          type: 'Feature' as const,
          properties: {},
          geometry: { type: 'Point' as const, coordinates: [c.lon, c.lat] },
        })),
    })
  }, [path])

  if (!MAPBOX_TOKEN) {
    return (
      <div className="flex h-full items-center justify-center bg-bg p-6 text-center text-text-muted">
        <p>
          {t('map.tokenMissing', { code: 'VITE_MAPBOX_TOKEN' })}
          <br />
          یک توکن Mapbox در فایل <code>.env.local</code> قرار دهید.
        </p>
      </div>
    )
  }

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="map" />
}
