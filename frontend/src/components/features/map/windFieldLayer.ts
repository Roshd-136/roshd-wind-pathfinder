import type { WindField } from '../../../types/routing'
import { arrowFeatures, colorForSpeed, gridMeta, WIND_SPEED_STOPS } from '../../../utils/windField'

/**
 * رندر میدان باد روی Mapbox GL با هندسهٔ خالص (بدون texture/آیکون):
 *  ۱) نقشهٔ حرارتی سرعت = لایهٔ fill روی سلول‌های شبکه، رنگ داده‌محور از رمپ
 *     راهنما (همان توکن‌های `--wind-speed-*`)،
 *  ۲) پیکان‌های جهت باد = خطوط chevron با چرخش حساب‌شده در خود مختصات
 *     (قرارداد هواشناسی: `direction_deg` از کجا می‌وزد؛ پیکان به سمت جریان،
 *     یعنی جهت + ۱۸۰).
 *
 * این ترکیب روی GPU نرم‌افزاری (SwiftShader) هم سبک است؛ لایه‌های image/symbol
 * (رستر + آیکون چرخان) در محیط‌های بدون GPU سخت‌افزاری گلوگاه می‌شوند.
 */

const FIELD_SOURCE = 'wind-field-fill'
const FIELD_LAYER = 'wind-field-layer'
const ARROW_SOURCE = 'wind-arrows'
const ARROW_LAYER = 'wind-arrows-layer'

/** رنگ رمپ به‌صورت expression رنگی mapbox برای fill-color داده‌محور. */
function speedColorExpression(): unknown[] {
  const stops: unknown[] = ['interpolate', ['linear'], ['get', 'speed']]
  for (const stop of WIND_SPEED_STOPS) {
    const [r, g, b] = stop.color
    stops.push(stop.value, `rgb(${r}, ${g}, ${b})`)
  }
  return stops
}

/** GeoJSON سلول‌های شبکهٔ میدان برای لایهٔ fill (نقشهٔ حرارتی). */
export function fieldFillGeoJson(field: WindField) {
  const meta = gridMeta(field)
  // هم‌پوشانی جزئی سلول‌ها تا درز آنتی‌الیاس بین چندضلعی‌ها دیده نشود
  const halfLat = meta.latStep * 0.6
  const halfLon = meta.lonStep * 0.6
  const features = field.vectors.map((v) => ({
    type: 'Feature' as const,
    properties: { speed: v.speed_mps },
    geometry: {
      type: 'Polygon' as const,
      coordinates: [
        [
          [v.lon - halfLon, v.lat - halfLat],
          [v.lon + halfLon, v.lat - halfLat],
          [v.lon + halfLon, v.lat + halfLat],
          [v.lon - halfLon, v.lat + halfLat],
          [v.lon - halfLon, v.lat - halfLat],
        ],
      ],
    },
  }))
  return { type: 'FeatureCollection' as const, features }
}

/** GeoJSON پیکان‌های chevron — چرخش در مختصات، جهت = downwind. */
export function arrowChevronsGeoJson(field: WindField, stride = 3) {
  const arrows = arrowFeatures(field, stride)
  // طول پیکان ~۰٫۰۴ درجه (حدود ۴ کیلومتر) — در زوم‌های کاری کریدور خوانا.
  const len = 0.045
  const wing = 0.5 // نسبت بال‌های chevron
  const features = arrows.map((a) => {
    const toRad = Math.PI / 180
    const heading = (a.direction_deg + 180) * toRad // جهت جریان
    const dx = Math.sin(heading) * len
    const dy = Math.cos(heading) * len
    // نوک پیکان در جلو، دو بال به عقب
    const tipLat = a.lat + dy
    const tipLon = a.lon + dx
    const perpX = Math.cos(heading) * len * wing
    const perpY = -Math.sin(heading) * len * wing
    return {
      type: 'Feature' as const,
      properties: { speed: a.speed_mps },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [a.lon - dx / 2 - perpX / 2, a.lat - dy / 2 - perpY / 2],
          [tipLon, tipLat],
          [a.lon - dx / 2 + perpX / 2, a.lat - dy / 2 + perpY / 2],
        ],
      },
    }
  })
  return { type: 'FeatureCollection' as const, features }
}

/** افزودن source/لایه‌های میدان باد (فقط پس از «load»). */
export function addWindLayers(map: mapboxgl.Map): void {
  if (map.getSource(FIELD_SOURCE)) return
  map.addSource(FIELD_SOURCE, {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  map.addLayer({
    id: FIELD_LAYER,
    type: 'fill',
    source: FIELD_SOURCE,
    paint: {
      'fill-color': speedColorExpression() as never,
      'fill-opacity': ['interpolate', ['linear'], ['get', 'speed'], 0, 0.35, 20, 0.6],
    },
  })

  map.addSource(ARROW_SOURCE, {
    type: 'geojson',
    data: { type: 'FeatureCollection', features: [] },
  })
  const lineStops: unknown[] = ['interpolate', ['linear'], ['get', 'speed']]
  for (const stop of WIND_SPEED_STOPS) {
    const [r, g, b] = stop.color
    lineStops.push(stop.value, `rgb(${r}, ${g}, ${b})`)
  }
  map.addLayer({
    id: ARROW_LAYER,
    type: 'line',
    source: ARROW_SOURCE,
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': lineStops as never,
      'line-width': 2,
      'line-opacity': 0.95,
    },
  })
  moveWindLayersBelowRoute(map)
}

/** میدان باد زیر خط مسیر بنشیند (خط مسیر و چک‌پوینت‌ها رو باشد). */
export function moveWindLayersBelowRoute(map: mapboxgl.Map): void {
  const routeLayer = 'route-line-layer' // همان ROUTE_LAYER_ID در MapView
  if (map.getLayer(FIELD_LAYER) && map.getLayer(routeLayer)) {
    map.moveLayer(FIELD_LAYER, routeLayer)
  }
  if (map.getLayer(ARROW_LAYER) && map.getLayer(FIELD_LAYER)) {
    map.moveLayer(ARROW_LAYER, FIELD_LAYER)
  }
}

/** حذف لایه‌های باد (وقتی هیچ لایه‌ای فعال نیست). */
export function setWindLayersVisible(map: mapboxgl.Map, visible: boolean): void {
  if (map.getLayer(FIELD_LAYER)) {
    map.setLayoutProperty(FIELD_LAYER, 'visibility', visible ? 'visible' : 'none')
  }
  if (map.getLayer(ARROW_LAYER)) {
    map.setLayoutProperty(ARROW_LAYER, 'visibility', visible ? 'visible' : 'none')
  }
}

/** به‌روزرسانی دادهٔ میدان فعال. */
export function updateWindField(map: mapboxgl.Map, field: WindField): void {
  const fillSource = map.getSource(FIELD_SOURCE) as mapboxgl.GeoJSONSource | undefined
  fillSource?.setData(fieldFillGeoJson(field))
  const arrowSource = map.getSource(ARROW_SOURCE) as mapboxgl.GeoJSONSource | undefined
  arrowSource?.setData(arrowChevronsGeoJson(field))
}

/**
 * اعمال میدان فعال: منبع/لایه‌ها فقط روی استایلِ آماده ساخته می‌شوند؛ اگر
 * هنوز «load» نخورده، هندلر load خودش میدان موجود را اعمال می‌کند. با
 * `null` لایه‌ها پنهان می‌شوند.
 */
/**
 * اجرای تابع پس از آماده‌شدن استایل — بر پایهٔ تایمر، نه رویداد «load»:
 * اگر applyWindField خودش داخل هندلر load صدا زده شود، ثبت شنوندهٔ تازه روی
 * همان رویدادِ در حال انتشار هرگز اجرا نمی‌شود.
 */
function whenStyleReady(map: mapboxgl.Map, fn: () => void, tries = 100): void {
  if (map.isStyleLoaded() || map.loaded()) {
    fn()
    return
  }
  if (tries > 0) {
    setTimeout(() => whenStyleReady(map, fn, tries - 1), 150)
  }
}

export function applyWindField(map: mapboxgl.Map, field: WindField | null): void {
  if (!map.isStyleLoaded() && !map.loaded()) {
    whenStyleReady(map, () => applyWindField(map, field))
    return
  }
  if (!map.getSource(FIELD_SOURCE)) {
    if (!field) return
    addWindLayers(map)
  }
  setWindLayersVisible(map, field !== null)
  if (field) updateWindField(map, field)
}

/** رنگ RGB یک سرعت — برای تست/ابزارهای جانبی (خارج از نقشه). */
export function speedColor(speedMps: number): [number, number, number] {
  return colorForSpeed(speedMps)
}
