import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import type { Coordinate, Coordinate3D, WindField } from '../../../types/routing'
import type { ViewportSettings } from '../../../store/useUiStore'
import { WIND_ARROW_CONFIG } from '../../../config/mapDisplay'
import { ManualSceneView as ManualSceneView3D } from './ManualSceneView'
import type { EditTarget } from '../../../three/manual/scene-gl'
import { applyWindFields, setParticleFlowPaused, setWindOverlaysVisible, stopParticleFlow } from './windFieldLayer'

interface MapViewProps {
  mode: '2d' | '3d'
  origin: Coordinate | null
  destination: Coordinate | null
  checkpoints?: Coordinate[]
  path: Coordinate[] | null
  /** 3D path with altitude data for 3D rendering */
  path3d?: Coordinate3D[] | null
  /** میدان‌های بادِ نمایان (مرتب بر ارتفاع) — نقشهٔ حرارتی + پیکان‌ها. */
  windFields?: WindField[]
  viewport: ViewportSettings
  /** هر کلیک نقشه — صفحه تصمیم می‌گیرد مبدأ/مقصد/جایگزینی/اطلاعات نقطه است. */
  onMapClick: (coord: Coordinate) => void
  /** نقشهٔ ساخته‌شده — برای ابزارهای بیرونی (زوم سفارشی). */
  onReady?: (map: maplibregl.Map) => void
  /** صحنه فعال و پیداست؟ مخفی: MapLibre فقط resize خودش را به تعویض می‌اندازد. */
  active?: boolean
  /** برای صحنهٔ سه‌بعدی — وقتی مخفی است حلقهٔ رندر pause می‌شود. */
  paused?: boolean
  /** هدف فعال گیمبال ویرایش نقطه در صحنهٔ سه‌بعدی. */
  editTarget?: EditTarget | null
  /** حالت «افزودن چک‌پوینت» — در ۳بعدی هم با کلیک روی دشتِ زمین می‌گذارد. */
  placingPoint?: boolean
  /** جابه‌جایی نقطه از گیمبال سه‌بعدی. */
  onPointEdit?: (target: EditTarget, coord: Coordinate) => void
  /** کلیک روی گوی نشانگر سه‌بعدی — انتخاب نقطه (null = بستن گیمبال). */
  onPointPick?: (target: EditTarget | null) => void
}

const ROUTE_SOURCE_ID = 'route-line'
const ROUTE_LAYER_ID = 'route-line-layer'
const ROUTE_DOTS_SOURCE_ID = 'route-dots'
const ROUTE_DOTS_LAYER_ID = 'route-dots-layer'
// لایهٔ سفارشی ۳بعدی — فقط وقتی مسیر سه‌بعدی در دسترس است رسم می‌شود؛ لایهٔ
// line عادی در همان حالت پنهان می‌شود (خط خوابیده روی زمین دوبرابر دیده نمی‌شود).
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
      'wind-arrows': { type: 'geojson' as const, data: EMPTY_FC },
      'wind-particles': { type: 'geojson' as const, data: EMPTY_FC },
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
      {
        // پیکان‌های ثابت جهت باد — اسپرایت per-bucket با چرخش جریان؛
        // هندسه/اندازه از `WIND_ARROW_CONFIG` تا با کانفیگ یکی باشد.
        id: 'wind-arrows-layer',
        type: 'symbol',
        source: 'wind-arrows',
        layout: {
          visibility: 'none',
          'icon-image': ['get', 'icon'],
          'icon-rotate': ['get', 'direction'],
          'icon-rotation-alignment': 'map',
          'icon-allow-overlap': true,
          'icon-ignore-placement': true,
          'icon-size': [
            'interpolate',
            ['exponential', 1.6],
            ['zoom'],
            5,
            WIND_ARROW_CONFIG.iconSizeStops[0][1],
            8,
            WIND_ARROW_CONFIG.iconSizeStops[1][1],
            12,
            WIND_ARROW_CONFIG.iconSizeStops[2][1],
          ],
        },
        paint: { 'icon-opacity': WIND_ARROW_CONFIG.opacity },
      },
      {
        id: 'wind-particles-layer',
        type: 'line',
        source: 'wind-particles',
        layout: { visibility: 'none', 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          // رنگ/ضخامت هر Feature (دُم+نوک واحد) per-feature است — در حالت
          // چندلایه (۳بعدی) هر میدان بازهٔ رنگ خودش را دارد و لایه‌های بالاتر
          // کمی نازک‌ترند.
          'line-color': ['get', 'color'],
          'line-width': ['get', 'width'],
          // کدری هر ذره با عمرش — ورود/خروج نرم (ویژگی opacity هر ذره)
          'line-opacity': ['get', 'opacity'],
        },
      },
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
 * نقشهٔ اصلی — دیسپچر با نگه‌داشتن زندهٔ هر دو صحنه: ۳بعدی = صحنهٔ دست‌ساز
 * WebGL، ۲بعدی = MapLibre. هر دو mount می‌مانند و غیرفعال فقط با CSS پنهان
 * می‌شود (۲بعدی: map.resize هنگام بازگشت — ۳بعدی: pause حلقهٔ رندر)؛
 * با تعویض حالت هیچ چیز از نو ساخته/بارگذاری نمی‌شود — پیکان‌ها، مسیر و
 * موقعیت دوربین/نقشه دست‌نخورده باقی می‌مانند.
 */
export function MapView(props: MapViewProps) {
  // انیمیشن تعویض صحنه — «کوبی» ملایم روی صحنه‌ای که وارد می‌شود: بدون
  // remount؛ فقط کلاس کوبی روی کل پوششِ هر دو صحنه اعمال می‌شود.
  const [wobling, setWobling] = useState(false)
  const firstRender = useRef(true)
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }
    setWobling(true)
    const id = window.setTimeout(() => setWobling(false), 650)
    return () => window.clearTimeout(id)
  }, [props.mode])

  const is3d = props.mode === '3d'
  return (
    <div
      className={`relative h-full w-full ${wobling ? 'map-scene-wobble' : ''}`}
    >
      {/* ۲بعدی — همیشه زنده؛ در ۳بعدی فقط پنهان (display:none) */}
      <div className={is3d ? 'hidden' : 'absolute inset-0'} aria-hidden={is3d}>
        <MapLibreView {...props} mode="2d" active={!is3d} />
      </div>
      {/* ۳بعدی — همیشه زنده؛ در ۲بعدی فقط پنهان */}
      <div className={is3d ? 'absolute inset-0' : 'hidden'} aria-hidden={!is3d}>
        <MapView3D
          {...props}
          paused={!is3d}
          // گیمبال ویرایش فقط در نمای سه‌بعدی فعال معنا دارد
          editTarget={is3d ? (props.editTarget ?? null) : null}
          onPointPick={is3d ? props.onPointPick : undefined}
        />
      </div>
    </div>
  )
}

/**
 * نمای دوبعدی (MapLibre) — تمام منطق قبلی نقشهٔ ۲بعدی این‌جاست.
 */
function MapLibreView({
  mode, origin, destination, checkpoints = [], path, path3d, windFields = [],
  viewport, onMapClick, onReady, active = true,
}: MapViewProps) {
  void mode
  void path3d
  // ————— حالت ۲بعدی: MapLibre —————
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  // نقشه ساخته شد؟ — اثرهای بالادست که پیش از ساختِ map اجرا می‌شوند با این
  // کلید دوباره اجرا می‌شوند؛ وگرنه اولین اعمالِ باد/مسیر بی‌صدا از دست می‌رفت.
  const [mapCreated, setMapCreated] = useState(false)
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
    if (!map) return
    applyWindFields(map, windFields, {
      multiLayer: false, // MapLibre فقط حالت ۲بعدی — لایه‌های سه‌بعدی صحنهٔ دست‌ساز
      showHeatmap: viewport.showHeatmap,
      showArrows: viewport.showArrows,
      showParticles: viewport.showParticles,
      animateWind: viewport.animateWind,
    })
  }, [windFields, mapCreated, viewport.showHeatmap, viewport.showArrows, viewport.showParticles, viewport.animateWind])

  // کلیدهای نمایش باد (تنظیمات viewport) — بدون بازسازی داده
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    setWindOverlaysVisible(map, {
      heatmap: viewport.showHeatmap,
      arrows: viewport.showArrows,
      particles: viewport.showParticles,
    })
  }, [mapCreated, viewport.showHeatmap, viewport.showArrows, viewport.showParticles])

  // توقف/ازسرگیری حرکت ذرات — کلید «حرکت ذرات باد»؛ قاب فعلی هنگام توقف ثابت می‌ماند
  useEffect(() => {
    setParticleFlowPaused(!active || !viewport.animateWind)
  }, [active, viewport.animateWind])

  // بازگشت به دید — MapLibre اندازهٔ صفرِ مخفی‌بودن را باید دوباره بخواند
  useEffect(() => {
    if (active && mapRef.current) mapRef.current.resize()
  }, [active, mapCreated])

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
    {
      ;(window as unknown as { __map?: maplibregl.Map }).__map = map
    }

    map.on('click', (e) => {
      // هر کلیک به صفحهٔ بالادست واگذار می‌شود: مبدأ/مقصد، جایگزینی انتخاب،
      // چک‌پوینت (با دکمهٔ پنل) یا اطلاعات نقطه — بسته به گامِ ویزارد.
      const coord = { lat: e.lngLat.lat, lon: e.lngLat.lng }
      handlersRef.current.onMapClick(coord)
    })

    mapRef.current = map
    setMapCreated(true)
    return () => {
      stopParticleFlow()
      map.remove()
      mapRef.current = null
    }
  }, [])

  // نقشهٔ پایهٔ دوبعدی — ۳بعدی دیگر در MapLibre نیست (صحنهٔ دست‌ساز جدا).
  // به‌جای گیتِ `isStyleLoaded` (که با منبع DEM مدت‌ها false می‌ماند) مستقیم
  // تلاش می‌کنیم و روی خطا با تایمر برمی‌گردیم.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    let cancelled = false
    let attempts = 0
    const applyMode = () => {
      if (cancelled) return
      try {
        const sat = viewport.mapStyle === 'satellite'
        map.setLayoutProperty('osm', 'visibility', sat ? 'none' : 'visible')
        map.setLayoutProperty('satellite', 'visibility', sat ? 'visible' : 'none')
        map.setPaintProperty('bg', 'background-color', '#e8e6e1')
        map.setPaintProperty('hillshade', 'hillshade-exaggeration', 0.35)
        map.setPaintProperty('hillshade', 'hillshade-shadow-color', '#473b2d')
        map.setTerrain(null)
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
  // این افکت فقط حالت ۲بعدی است — در ۳بعدی صحنهٔ دست‌ساز مسیر را خودش
  // (لولهٔ اسپلاین از path_3d) رسم می‌کند و MapLibre اصلاً mount نمی‌شود.
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
          map.fitBounds(bounds, { padding: 80, duration: 800, pitch: 0 })
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
  }, [path, mapCreated])

  // بازگشت از حالت مخفی (۲↔۳بعدی با نگه‌داشتن زنده) — بوم اندازهٔ کهنه دارد؛
  // صریح resize می‌کنیم تا نقشه به‌جای کادر صفر/کهنه، کادر واقعی را بگیرد.
  useEffect(() => {
    if (active) mapRef.current?.resize()
  }, [active])

  return <div ref={containerRef} className="h-full w-full" role="application" aria-label="map" />
}

/**
 * نمای سه‌بعدی — بومِ صحنهٔ دست‌ساز WebGL. «پیش‌فرض خاموش»: بدون مسیر
 * سه‌بعدی بوم mount نمی‌شود تا صفحهٔ سیاه/خالی دیده نشود.
 */
function MapView3D({
  origin, destination, checkpoints = [], path3d, windFields = [],
  viewport, onMapClick, paused = false, editTarget = null, placingPoint, onPointEdit, onPointPick,
}: MapViewProps) {
  const has3dPath = Boolean(path3d && path3d.length > 1)
  return (
    <div className="relative h-full w-full" role="application" aria-label="map">
      {has3dPath ? (
        <ManualSceneView3D
          origin={origin}
          destination={destination}
          checkpoints={checkpoints}
          path3d={path3d}
          windFields={windFields}
          showArrows={viewport.showArrows}
          paused={paused}
          editTarget={editTarget}
          placingPoint={placingPoint}
          onPointEdit={onPointEdit}
          onPointPick={onPointPick}
          onMapClick={onMapClick}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-surface-raised text-xs text-text-secondary">
          محاسبهٔ مسیر برای نمایش صحنهٔ سه‌بعدی لازم است
        </div>
      )}
    </div>
  )
}
