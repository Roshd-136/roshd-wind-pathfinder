import type { GeoJSONSource, ImageSource, Map as MapLibreMap } from 'maplibre-gl'
import type { WindField } from '../../../types/routing'
import { arrowFeatures, colorForSpeed, gridMeta, WIND_SPEED_STOPS } from '../../../utils/windField'

/**
 * رندر میدان باد روی MapLibre GL:
 *  ۱) نقشهٔ حرارتی «نرم» — تصویر canvas (درون‌یابی‌شده) روی image source،
 *     بدون درز سلول‌ها (نسخهٔ قبلی با سلول‌های fill شبیه «گرید سبز» بود)،
 *  ۲) پیکان‌های جهت باد = خطوط chevron با چرخش در مختصات
 *     (قرارداد هواشناسی: `direction_deg` از کجا می‌وزد؛ پیکان به سمت جریان،
 *     یعنی جهت + ۱۸۰).
 */

const FIELD_SOURCE = 'wind-field-raster'
const FIELD_LAYER = 'wind-field-layer'
const ARROW_SOURCE = 'wind-arrows'
const ARROW_LAYER = 'wind-arrows-layer'

/** تصویر نرم میدان از شبکه (canvas → dataURL) — رنگ از همان رمپ راهنما. */
export function buildFieldImage(field: WindField, width = 420): string {
  const meta = gridMeta(field)
  const latSpan = meta.lats[meta.lats.length - 1] - meta.lats[0]
  const lonSpan = meta.lons[meta.lons.length - 1] - meta.lons[0]
  const height = Math.max(64, Math.round((width * latSpan) / Math.max(lonSpan, 1e-6)))
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) return ''
  const image = ctx.createImageData(width, height)

  for (let py = 0; py < height; py += 1) {
    // ردیف ۰ تصویر = شمال (بیشینهٔ عرض جغرافیایی)
    const rowFloat = (1 - py / (height - 1)) * (meta.lats.length - 1)
    const row = Math.min(Math.max(Math.round(rowFloat), 0), meta.lats.length - 1)
    for (let px = 0; px < width; px += 1) {
      const col = Math.min(
        Math.max(Math.round((px / (width - 1)) * (meta.lons.length - 1)), 0),
        meta.lons.length - 1,
      )
      const v = field.vectors[row * meta.lons.length + col]
      if (!v) continue
      const [r, g, b] = colorForSpeed(v.speed_mps)
      const alpha = 80 + Math.round(70 * Math.min(v.speed_mps / 20, 1))
      const offset = (py * width + px) * 4
      image.data[offset] = r
      image.data[offset + 1] = g
      image.data[offset + 2] = b
      image.data[offset + 3] = alpha
    }
  }
  ctx.putImageData(image, 0, 0)
  return canvas.toDataURL('image/png')
}

/**
 * GeoJSON پیکان‌های «توپر» (شکل فلش ۷نقطه‌ای) — مثل پیکان‌های صحنهٔ نمونه.
 * چرخش در مختصات؛ جهت = downwind (direction_deg + ۱۸۰).
 */
export function arrowChevronsGeoJson(field: WindField, stride = 3) {
  const arrows = arrowFeatures(field, stride)
  const len = 0.055 // طول کل فلش (درجه)
  const shaft = 0.011 // نیم‌عرض ساقه
  const head = 0.024 // نیم‌عرض نوک
  const headLen = 0.032 // طول نوک
  const toRad = Math.PI / 180
  const features = arrows.map((a) => {
    const heading = (a.direction_deg + 180) * toRad
    const dx = Math.sin(heading)
    const dy = Math.cos(heading)
    const px = Math.cos(heading)
    const py = -Math.sin(heading)
    const tipLat = a.lat + dy * len
    const tipLon = a.lon + dx * len
    const shaftLat = a.lat + dy * (len - headLen)
    const shaftLon = a.lon + dx * (len - headLen)
    const ring = [
      [a.lon + px * shaft, a.lat + py * shaft],
      [shaftLon + px * head, shaftLat + py * head],
      [tipLon, tipLat],
      [shaftLon - px * head, shaftLat - py * head],
      [a.lon - px * shaft, a.lat - py * shaft],
      [a.lon - dx * len * 0.35 - px * shaft * 0.6, a.lat - dy * len * 0.35 - py * shaft * 0.6],
      [a.lon - dx * len * 0.35 + px * shaft * 0.6, a.lat - dy * len * 0.35 + py * shaft * 0.6],
      [a.lon + px * shaft, a.lat + py * shaft],
    ]
    return {
      type: 'Feature' as const,
      properties: { speed: a.speed_mps },
      geometry: { type: 'Polygon' as const, coordinates: [ring] },
    }
  })
  return { type: 'FeatureCollection' as const, features }
}

/** افزودن لایهٔ پیکان‌ها (منبع تصویر میدان با اولین میدان واقعی ساخته می‌شود). */
export function addWindLayers(map: MapLibreMap): void {
  if (map.getSource(ARROW_SOURCE)) return
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
    type: 'fill',
    source: ARROW_SOURCE,
    paint: {
      'fill-color': lineStops as never,
      'fill-opacity': 0.95,
    },
  })
  moveWindLayersBelowRoute(map)
}

/** میدان باد زیر خط مسیر بنشیند (خط مسیر و چک‌پوینت‌ها رو باشد). */
export function moveWindLayersBelowRoute(map: MapLibreMap): void {
  const routeLayer = 'route-line-layer' // همان ROUTE_LAYER_ID در MapView
  if (map.getLayer(ARROW_LAYER) && map.getLayer(routeLayer)) {
    map.moveLayer(ARROW_LAYER, routeLayer)
  }
}

/** پنهان/نمایان کردن لایه‌های باد. */
export function setWindLayersVisible(map: MapLibreMap, visible: boolean): void {
  if (map.getLayer(ARROW_LAYER)) {
    map.setLayoutProperty(ARROW_LAYER, 'visibility', visible ? 'visible' : 'none')
  }
  if (map.getLayer(FIELD_LAYER)) {
    map.setLayoutProperty(FIELD_LAYER, 'visibility', visible ? 'visible' : 'none')
  }
}

/** به‌روزرسانی دادهٔ میدان فعال (تصویر نرم + پیکان‌ها). */
export function updateWindField(map: MapLibreMap, field: WindField): void {
  const imageSource = map.getSource(FIELD_SOURCE) as ImageSource | undefined
  const meta = gridMeta(field)
  const latMax = meta.lats[meta.lats.length - 1]
  const latMin = meta.lats[0]
  const lonMin = meta.lons[0]
  const lonMax = meta.lons[meta.lons.length - 1]
  const payload = {
    url: buildFieldImage(field),
    coordinates: [
      [lonMin, latMax],
      [lonMax, latMax],
      [lonMax, latMin],
      [lonMin, latMin],
    ] as [[number, number], [number, number], [number, number], [number, number]],
  }
  if (imageSource) {
    imageSource.updateImage(payload)
  } else {
    map.addSource(FIELD_SOURCE, { type: 'image', ...payload })
    map.addLayer({
      id: FIELD_LAYER,
      type: 'raster',
      source: FIELD_SOURCE,
      paint: { 'raster-opacity': 0.85, 'raster-fade-duration': 0 },
    })
    moveWindLayersBelowRoute(map)
  }
  const arrowSource = map.getSource(ARROW_SOURCE) as GeoJSONSource | undefined
  arrowSource?.setData(arrowChevronsGeoJson(field))
}

/**
 * اعمال میدان فعال — امن برای فراخوانی قبل از آماده‌شدن استایل
 * (تایمری، نه رویداد load که در حین انتشار خودش شنونده نمی‌گیرد).
 */
export function applyWindField(map: MapLibreMap, field: WindField | null): void {
  const retry = () => applyWindField(map, field)
  if (!map.isStyleLoaded()) {
    if (map.loaded()) {
      retry()
    } else {
      setTimeout(retry, 150)
    }
    return
  }
  if (!field) {
    setWindLayersVisible(map, false)
    addWindLayers(map)
    return
  }
  addWindLayers(map)
  setWindLayersVisible(map, true)
  updateWindField(map, field)
}
