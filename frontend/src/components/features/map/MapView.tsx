import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef } from 'react'
import type { Coordinate, WindField } from '../../../types/routing'
import type { ViewportSettings } from '../../../store/useUiStore'
import { applyWindFields, setWindOverlaysVisible } from './windFieldLayer'

interface MapViewProps {
  mode: '2d' | '3d'
  origin: Coordinate | null
  destination: Coordinate | null
  checkpoints?: Coordinate[]
  path: Coordinate[] | null
  /** میدان‌های بادِ نمایان (مرتب بر ارتفاع) — نقشهٔ حرارتی + پیکان‌ها. */
  windFields?: WindField[]
  viewport: ViewportSettings
  /** هر کلیک نقشه — صفحه تصمیم می‌گیرد مبدأ/مقصد/جایگزینی/اطلاعات نقطه است. */
  onMapClick: (coord: Coordinate) => void
  /** نقشهٔ ساخته‌شده — برای ابزارهای بیرونی (زوم سفارشی). */
  onReady?: (map: maplibregl.Map) => void
}

const ROUTE_SOURCE_ID = 'route-line'
const ROUTE_LAYER_ID = 'route-line-layer'
const ROUTE_DOTS_SOURCE_ID = 'route-dots'
const ROUTE_DOTS_LAYER_ID = 'route-dots-layer'
/** میدانِ خالی برای منبع‌های image/geojson استایل پایه. */
const EMPTY_FC = { type: 'FeatureCollection' as const, features: [] }
const EMPTY_LINE = {
  type: 'Feature' as const,
  properties: {},
  geometry: { type: 'LineString' as const, coordinates: [] },
}
/** تصویر شفاف ۱×۱ — جای‌نگهدار منبع image تا اولین به‌روزرسانی میدان. */
const TRANSPARENT_PIXEL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR4nGNgAAIAAAUAAXpeqz8AAAAASUVORK5CYII='
/** لایه‌های ارتفاعی میدان باد — همان لایه‌های UI (فیکسچرها/API). */
const WIND_ALTITUDES = [50, 200, 500] as const

const Khorasan_CENTER: [number, number] = [58.65, 36.18]

/**
 * استایل نقشه — کاشی‌های آزاد OpenStreetMap و تصویر ماهواره‌ای Esri (هر دو
 * بدون توکن) با تم هماهنگ برنامه؛ در تم تاریک با فیلتر CSS روی بوم نقشه
 * تیره می‌شود (global.css).
 *
 * **همهٔ لایه‌های پویا (نقشهٔ رنگی باد، پیکان‌های هر ارتفاع، خط مسیر) از
 * ابتدا در استایل تعریف می‌شوند** با دادهٔ خالی و `visibility: none` — هیچ
 * لایه‌ای در زمان اجرا add نمی‌شود. افزودن لایه وقتی استایل در وضعیت
 * نیمه‌لود (صف DEM) است گاهی بی‌اثر می‌ماند و لایه هرگز رسم نمی‌شد؛ با
 * درخت لایهٔ ایستا فقط داده عوض می‌شود و این دسته باگ کلاً حذف می‌شود.
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
      satellite: {
        type: 'raster',
        tiles: [
          'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        ],
        tileSize: 256,
        maxzoom: 19,
        attribution: 'Esri, Maxar, Earthstar Geographics',
      },
      // ارتفاع‌سنج آزاد AWS Terrarium — برای ترن سه‌بعدی و سایهٔ کوهستان
      terrain: {
        type: 'raster-dem',
        tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
        encoding: 'terrarium',
        tileSize: 256,
        maxzoom: 14,
      },
      'wind-field-raster': {
        type: 'image',
        url: TRANSPARENT_PIXEL,
        coordinates: [
          [0, 1],
          [1, 1],
          [1, 0],
          [0, 0],
        ],
      },
      ...Object.fromEntries(
        WIND_ALTITUDES.map((altitude) => [
          `wind-arrows-${altitude}`,
          { type: 'geojson' as const, data: EMPTY_FC },
        ]),
      ),
      'route-line': { type: 'geojson', data: EMPTY_LINE },
      'route-dots': { type: 'geojson', data: EMPTY_FC },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#e8e6e1' } },
      { id: 'satellite', type: 'raster', source: 'satellite', layout: { visibility: 'none' } },
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
      {
        id: 'wind-field-layer',
        type: 'raster',
        source: 'wind-field-raster',
        layout: { visibility: 'none' },
        paint: { 'raster-opacity': 0.85, 'raster-fade-duration': 0 },
      },
      ...WIND_ALTITUDES.map(
        (altitude) =>
          ({
            id: `wind-arrows-layer-${altitude}`,
            type: 'symbol',
            source: `wind-arrows-${altitude}`,
            layout: {
              visibility: 'none',
              'symbol-placement': 'point',
              'icon-image': ['get', 'icon'],
              'icon-rotate': ['get', 'heading'],
              // چرخش با زمین (جهت واقعی جریان روی صفحه) ولی شکل پیکان همیشه
              // رو‌به‌بیننده می‌ماند تا در ۳بعدی هم همان شکل ۲بعدی دیده شود
              'icon-rotation-alignment': 'map',
              'icon-pitch-alignment': 'viewport',
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
              'icon-size': ['interpolate', ['linear'], ['zoom'], 5, 0.6, 8, 0.95, 12, 1.15],
            },
            paint: { 'icon-opacity': ['get', 'fillOpacity'] },
          }) as maplibregl.LayerSpecification,
      ),
      {
        id: ROUTE_LAYER_ID,
        type: 'line',
        source: ROUTE_SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': '#f8fafc',
          'line-width': 4,
          'line-blur': 0.2,
        },
      },
      {
        id: ROUTE_DOTS_LAYER_ID,
        type: 'circle',
        source: ROUTE_DOTS_SOURCE_ID,
        paint: {
          'circle-radius': 3.2,
          'circle-color': '#f8fafc',
          'circle-stroke-color': 'rgba(10, 14, 26, 0.4)',
          'circle-stroke-width': 1,
        },
      },
    ],
  }
}

/**
 * نقشهٔ اصلی (MapLibre GL — بدون توکن، کاشی آزاد) — کلیک روی نقشه به صفحهٔ
 * بالادست واگذار می‌شود (مبدأ/مقصد/جایگزینی/اطلاعات نقطه). مسیر با خط سفید +
 * نقاط سفید رسم می‌شود و کادر نقشه روی مسیر تنظیم می‌گردد. حالت ۳بعدی با ترن
 * واقعی (raster-dem آزاد) + pitch فعال می‌شود — مشابه صحنهٔ بصری‌سازی پروژه.
 */
export function MapView({
  mode,
  origin,
  destination,
  checkpoints = [],
  path,
  windFields = [],
  viewport,
  onMapClick,
  onReady,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const originMarkerRef = useRef<maplibregl.Marker | null>(null)
  const destinationMarkerRef = useRef<maplibregl.Marker | null>(null)
  const checkpointMarkersRef = useRef<maplibregl.Marker[]>([])
  // هندلر کلیک در ref نگه داشته می‌شود تا map فقط یک‌بار ساخته شود ولی
  // همیشه آخرین کلوژر را صدا بزند.
  const handlersRef = useRef({ onMapClick })
  useEffect(() => {
    handlersRef.current = { onMapClick }
  })

  // میدان‌های باد در ref نگه داشته می‌شوند تا وقتی map لایه‌هایش را افزود
  // (به‌صورت ناهمگام)، آخرین داده بلافاصله اعمال شود.
  const onReadyRef = useRef(onReady)
  useEffect(() => {
    onReadyRef.current = onReady
  })
  const windFieldsRef = useRef<WindField[]>(windFields)
  useEffect(() => {
    windFieldsRef.current = windFields
    const map = mapRef.current
    if (map) {
      applyWindFields(map, windFields, {
        multiLayer: mode === '3d',
        showHeatmap: viewport.showHeatmap,
        showArrows: viewport.showArrows,
      })
    }
  }, [windFields, mode, viewport.showHeatmap, viewport.showArrows])

  // کلیدهای نمایش باد (تنظیمات viewport) — بدون بازسازی داده
  useEffect(() => {
    const map = mapRef.current
    if (map) setWindOverlaysVisible(map, { heatmap: viewport.showHeatmap, arrows: viewport.showArrows })
  }, [viewport.showHeatmap, viewport.showArrows])

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: baseStyle(),
      center: Khorasan_CENTER,
      zoom: 7,
      attributionControl: false, // فقط یک کنترل صریح (پایین) — بدون تکرار
    })
    // انتساب OSM (الزام مجوز) — گوشهٔ پایین
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right")
    onReadyRef.current?.(map)
    // دسترسی dev برای دیباگ زندهٔ لایه‌ها (مثلاً از طریق CDP)
    if (import.meta.env.DEV) {
      ;(window as unknown as { __map?: maplibregl.Map }).__map = map
    }

    map.on('click', (e) => {
      // هر کلیک به صفحهٔ بالادست واگذار می‌شود: مبدأ/مقصد، جایگزینی انتخاب،
      // چک‌پوینت (با دکمهٔ پنل) یا اطلاعات نقطه — بسته به گامِ ویزارد.
      const coord = { lat: e.lngLat.lat, lon: e.lngLat.lng }
      handlersRef.current.onMapClick(coord)
    })

    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // حالت ۲بعدی/۳بعدی + نقشهٔ پایه — سوییچ درجا (بدون تغییر URL): در ۳بعدی
  // ترنِ واقعی با pitch و بزرگ‌نمایی ارتفاع فعال می‌شود (مثل صحنهٔ
  // بصری‌سازی) و کاشی ساده خاموش است؛ اگر کاربر نقشهٔ ماهواره‌ای انتخاب
  // کرده باشد، تصویر ماهواره‌ای روی ترن می‌نشیند. به‌جای گیتِ
  // `isStyleLoaded` (که با منبع DEM مدت‌ها false می‌ماند و سوییچ ۳بعدی را
  // فلج می‌کرد) مستقیم تلاش می‌کنیم و روی خطا با تایمر برمی‌گردیم.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    let cancelled = false
    let attempts = 0
    const applyMode = () => {
      if (cancelled) return
      try {
        const is3d = mode === '3d'
        const sat = viewport.mapStyle === 'satellite'
        map.setLayoutProperty('osm', 'visibility', !is3d && !sat ? 'visible' : 'none')
        // تصویر ماهواره‌ای حتی در ۳بعدی روی ترن می‌نشیند (ترنِ عکس‌دار)
        map.setLayoutProperty('satellite', 'visibility', sat ? 'visible' : 'none')
        // ۳بعدی مثل صحنهٔ بصری‌سازی: زمین سبز + سایهٔ قهوه‌ای کوهستان
        map.setPaintProperty('bg', 'background-color', is3d && !sat ? '#7fb069' : '#e8e6e1')
        map.setPaintProperty('hillshade', 'hillshade-exaggeration', is3d ? 0.6 : 0.35)
        map.setPaintProperty('hillshade', 'hillshade-shadow-color', is3d ? '#6b4a2f' : '#473b2d')
        if (is3d) {
          map.setTerrain({ source: 'terrain', exaggeration: 2 })
          map.easeTo({ pitch: 55, duration: 600 })
        } else {
          map.setTerrain(null)
          map.easeTo({ pitch: 0, duration: 400 })
        }
      } catch {
        // استایل هنوز کامل نیست — دوباره تلاش می‌شود
        if (attempts < 100) {
          attempts += 1
          setTimeout(applyMode, 150)
        }
      }
    }
    applyMode()
    return () => {
      cancelled = true
    }
  }, [mode, viewport.mapStyle])

  // سایهٔ کوهستان — کلید مستقل تنظیمات (در هر دو حالت)
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    let cancelled = false
    let attempts = 0
    const apply = () => {
      if (cancelled) return
      try {
        map.setLayoutProperty('hillshade', 'visibility', viewport.showHillshade ? 'visible' : 'none')
      } catch {
        if (attempts < 100) {
          attempts += 1
          setTimeout(apply, 150)
        }
      }
    }
    apply()
    return () => {
      cancelled = true
    }
  }, [viewport.showHillshade])

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
  // لایه‌ها از ابتدا در استایل پایه‌اند — این‌جا فقط داده عوض می‌شود.
  useEffect(() => {
    let cancelled = false
    let attempts = 0
    const draw = () => {
      if (cancelled) return
      const map = mapRef.current
      if (!map) return
      try {
        const source = map.getSource(ROUTE_SOURCE_ID) as maplibregl.GeoJSONSource
        source.setData({
          type: 'Feature',
          properties: {},
          geometry: {
            type: 'LineString',
            coordinates: (path ?? []).map((c) => [c.lon, c.lat]),
          },
        })
        const dots = map.getSource(ROUTE_DOTS_SOURCE_ID) as maplibregl.GeoJSONSource
        dots.setData({
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
        // وقتی استایل در وضعیت نیمه‌لود (صف DEM) است، setData گاهی تا
        // رندر بعدی بی‌اثر می‌ماند — یک رندر صریح تضمین می‌کند خط مسیر
        // همان لحظه دیده شود.
        map.triggerRepaint()
      } catch {
        // استایل هنوز کامل نیست — دوباره تلاش می‌شود
        if (attempts < 200) {
          attempts += 1
          setTimeout(draw, 150)
        }
      }
    }
    draw()
    return () => {
      cancelled = true
    }
  }, [path, mode])

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="map" />
}
