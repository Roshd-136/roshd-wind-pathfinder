import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
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

const Khorasan_CENTER: [number, number] = [58.65, 36.18]

/**
 * استایل نقشه — کاشی‌های آزاد OpenStreetMap (بدون نیاز به هیچ توکن/کلید) با
 * تم هماهنگ برنامه؛ در تم تاریک با فیلتر CSS روی بوم نقشه تیره می‌شود
 * (global.css). مشابه Google Maps اما آزاد و خودمیزبان از نظر کلید.
 */
function baseStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        maxzoom: 19,
        attribution: '© OpenStreetMap contributors',
      },
      // ارتفاع‌سنج آزاد AWS Terrarium — برای ترن سه‌بعدی و سایهٔ کوهستان
      terrain: {
        type: 'raster-dem',
        tiles: ['https://demotiles.maplibre.org/terrain-tiles/{z}/{x}/{y}.png'],
        encoding: 'terrarium',
        tileSize: 256,
        maxzoom: 12,
      },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#e8e6e1' } },
      { id: 'osm', type: 'raster', source: 'osm' },
      {
        id: 'hillshade',
        type: 'hillshade',
        source: 'terrain',
        paint: {
          'hillshade-exaggeration': 0.35,
          'hillshade-shadow-color': '#473b2d',
        },
      },
    ],
  }
}

/**
 * نقشهٔ اصلی (MapLibre GL — بدون توکن، کاشی آزاد OSM) — کلیک اول = مبدأ
 * (پین سبز)، کلیک دوم = مقصد (پین قرمز)، مسیر با خط سفید + نقاط سفید رسم
 * می‌شود و کادر نقشه روی مسیر تنظیم می‌گردد. حالت ۳بعدی با ترن واقعی
 * (raster-dem آزاد) + pitch فعال می‌شود — مشابه صحنهٔ بصری‌سازی پروژه.
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
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const originMarkerRef = useRef<maplibregl.Marker | null>(null)
  const destinationMarkerRef = useRef<maplibregl.Marker | null>(null)
  const checkpointMarkersRef = useRef<maplibregl.Marker[]>([])
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
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle(),
      center: Khorasan_CENTER,
      zoom: 7,
      attributionControl: { compact: true },
    })
    map.addControl(new maplibregl.NavigationControl(), document.documentElement.dir === 'rtl' ? 'bottom-right' : 'bottom-left')

    // long-press: نگه‌داشتن ۵۰۰ms بدون جابه‌جایی، بعد رها کردن بدون drag.
    // اگر long-press رخ دهد، کلیک بعدی نادیده گرفته می‌شود.
    let pressTimer: ReturnType<typeof setTimeout> | null = null
    let pressStart: maplibregl.Point | null = null
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
  }, [])

  // حالت ۲بعدی/۳بعدی — سوییچ درجا (بدون تغییر URL): در ۳بعدی فقط ترنِ
  // واقعی + آب (کاشی خیابان خاموش) با pitch و بزرگ‌نمایی ارتفاع، مشابه
  // صحنهٔ بصری‌سازی پروژه. setTerrain قبل از آماده‌شدن استایل خطا می‌دهد —
  // با رویداد load همگام می‌شود.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const applyMode = () => {
      try {
        const is3d = mode === '3d'
        map.setLayoutProperty('osm', 'visibility', is3d ? 'none' : 'visible')
        map.setPaintProperty('bg', 'background-color', is3d ? '#123a5c' : '#e8e6e1')
        // در ۳بعدی فقط ترن (سایهٔ کوهستان خاموش — دو برابر شدن هزینهٔ GPU)
        map.setLayoutProperty('hillshade', 'visibility', is3d ? 'none' : 'visible')
        if (is3d) {
          map.setTerrain({ source: 'terrain', exaggeration: 1.2 })
          map.easeTo({ pitch: 50, duration: 600 })
        } else {
          map.setTerrain(null)
          map.easeTo({ pitch: 0, duration: 400 })
        }
      } catch {
        // استایل هنوز کامل نیست — در رویداد load دوباره اعمال می‌شود
      }
    }
    if (map.isStyleLoaded()) applyMode()
    else map.once('load', applyMode)
  }, [mode])

  // نشانگر مبدأ
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (origin) {
      if (!originMarkerRef.current) {
        originMarkerRef.current = new maplibregl.Marker({ color: '#22c55e' })
      }
      originMarkerRef.current.setLngLat([origin.lon, origin.lat]).addTo(map)
    } else {
      originMarkerRef.current?.remove()
      originMarkerRef.current = null
    }
  }, [origin])

  // نشانگر مقصد
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (destination) {
      if (!destinationMarkerRef.current) {
        destinationMarkerRef.current = new maplibregl.Marker({ color: '#ef4444' })
      }
      destinationMarkerRef.current.setLngLat([destination.lon, destination.lat]).addTo(map)
    } else {
      destinationMarkerRef.current?.remove()
      destinationMarkerRef.current = null
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
      return new maplibregl.Marker({ element: el }).setLngLat([cp.lon, cp.lat]).addTo(map)
    })
  }, [checkpoints])

  // رسم خط مسیر + نقاط سفید روی آن (مطابق mockup) + تنظیم کادر روی مسیر.
  // اگر استایل هنوز آماده نیست، به‌جای ردشدنِ بی‌صدا، با تایمر دوباره تلاش
  // می‌شود (باگ قبلی: مسیر محاسبه‌شده گاهی رسم نمی‌شد).
  useEffect(() => {
    let cancelled = false
    let attempts = 0
    const draw = () => {
      if (cancelled) return
      const map = mapRef.current
      if (!map) return
      if (!map.isStyleLoaded()) {
        if (attempts < 100) {
          attempts += 1
          setTimeout(draw, 150)
        }
        return
      }
      const source = map.getSource(ROUTE_SOURCE_ID) as maplibregl.GeoJSONSource | undefined
      source?.setData({
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: (path ?? []).map((c) => [c.lon, c.lat]),
        },
      })
      const dots = map.getSource(ROUTE_DOTS_SOURCE_ID) as maplibregl.GeoJSONSource | undefined
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
      // پس از محاسبه، کادر نقشه روی مسیر تنظیم شود
      if (path && path.length > 1) {
        const lons = path.map((c) => c.lon)
        const lats = path.map((c) => c.lat)
        const bounds = new maplibregl.LngLatBounds(
          [Math.min(...lons), Math.min(...lats)],
          [Math.max(...lons), Math.max(...lats)],
        )
        map.fitBounds(bounds, { padding: 80, duration: 800, pitch: mode === '3d' ? 60 : 0 })
      }
    }
    draw()
    return () => {
      cancelled = true
    }
  }, [path, mode])

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="map" />
}
