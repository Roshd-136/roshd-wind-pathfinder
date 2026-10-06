import type { GeoJSONSource, ImageSource, Map as MapLibreMap } from 'maplibre-gl'
import type { WindField } from '../../../types/routing'
import {
  arrowFeatures,
  colorForFieldSpeed,
  fieldSpeedRange,
  gridMeta,
  WIND_SPEED_STOPS,
} from '../../../utils/windField'

/**
 * رندر میدان باد روی MapLibre GL:
 *  ۱) نقشهٔ حرارتی «نرم» — تصویر canvas (درون‌یابی‌شده) روی image source،
 *     بدون درز سلول‌ها (نسخهٔ قبلی با سلول‌های fill شبیه «گرید سبز» بود)،
 *  ۲) پیکان‌های باد — همان زبان بصری صحنهٔ مسیریابی (`src/viz/scene3d.py`):
 *     ساقهٔ باریک با طول متناسب با سرعت باد + سرِ کوچک روی نوک. پیکان‌ها
 *     «کمی جلو می‌روند، محو می‌شوند و از نو شروع می‌کنند» تا جهت جریان
 *     دقیقاً دیده شود (قرارداد هواشناسی: `direction_deg` از کجا می‌وزد؛
 *     پیکان به سمت جریان، یعنی جهت + ۱۸۰).
 */

const FIELD_SOURCE = 'wind-field-raster'
const FIELD_LAYER = 'wind-field-layer'
const ARROW_SOURCE = 'wind-arrows'
const ARROW_LAYER = 'wind-arrows-layer'

/** تصویر نرم میدان از شبکه (canvas → dataURL) — رنگ نسبی بازهٔ میدان. */
export function buildFieldImage(field: WindField, width = 420): string {
  const range = fieldSpeedRange(field)
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
      const [r, g, b] = colorForFieldSpeed(v.speed_mps, range)
      const alpha = 80 + Math.round(70 * Math.min((v.speed_mps - range[0]) / Math.max(range[1] - range[0], 1e-6), 1))
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

// --- پیکان‌های sprite — اندازهٔ ثابت روی صفحه، چرخش با جهت باد ---
// پیکان‌ها به‌جای چندضلعیِ درجه‌ای (که با زوم غول می‌شد — همان ایراد «خیلی
// چاق»)، لایهٔ symbol با آیکون باریک ثابت‌اند: ساقهٔ نازک + سرِ کوچک، به رنگ
// سطل سرعت (رنگ نسبی بازهٔ خود میدان، مثل صحنهٔ مسیریابی).

const ARROW_IMAGE_PREFIX = 'wind-arrow-'
/** ابعاد بوم اسپرایت (پیکسل فیزیکی؛ با pixelRatio:۲ یعنی ~۲۲ پیکسل CSS). */
const ARROW_SPRITE_SIZE = 44

/** مسافتی که هر پیکان در یک چرخهٔ انیمیشن جلو می‌رود (کیلومتر). */
const ARROW_TRAVEL_KM = 3
/** طول یک چرخهٔ «حرکت + محو» (میلی‌ثانیه). */
const ARROW_CYCLE_MS = 1800
/** گام نمونه‌برداری پیکان‌ها از شبکهٔ میدان. */
const ARROW_STRIDE = 2

function kmToDegLat(km: number): number {
  return km / 111.32
}

function kmToDegLon(km: number, lat: number): number {
  return km / (111.32 * Math.max(Math.cos((lat * Math.PI) / 180), 0.2))
}

/**
 * آیکون پیکان باریک (رو به شمال) روی بوم — ساقهٔ نازک + سرِ کوچک، همان زبان
 * صحنهٔ مسیریابی؛ با SDF نیستیم چون لبهٔ تیز می‌خواهیم، پس یک اسپرایت برای هر
 * رنگ رمپ می‌سازیم و رنگ نسبی با انتخاب اسپرایت (سطل سرعت) اعمال می‌شود.
 * ساخت اسپرایت یک‌بار و کش‌شده است (فراخوانی‌های بعدی رایگان).
 */
let arrowSpritesCache: Record<string, ImageData> | null = null

function buildArrowSprites(): Record<string, ImageData> {
  if (arrowSpritesCache) return arrowSpritesCache
  const size = ARROW_SPRITE_SIZE
  const sprites: Record<string, ImageData> = {}
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  if (!ctx) return sprites
  for (const [index, stop] of WIND_SPEED_STOPS.entries()) {
    ctx.clearRect(0, 0, size, size)
    const [r, g, b] = stop.color
    const cx = size / 2
    // ساقه: از پایین بوم تا نزدیک نوک — باریک (خط ۲ پیکسلی با خط‌کشی)
    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.95)`
    ctx.lineWidth = 2.6
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(cx, size - 6)
    ctx.lineTo(cx, 10)
    ctx.stroke()
    // سرِ پیکان: مثلث توپر کوچک روی نوک
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.95)`
    ctx.beginPath()
    ctx.moveTo(cx, 2)
    ctx.lineTo(cx - 5.5, 12)
    ctx.lineTo(cx + 5.5, 12)
    ctx.closePath()
    ctx.fill()
    sprites[`${ARROW_IMAGE_PREFIX}${index}`] = ctx.getImageData(0, 0, size, size)
  }
  arrowSpritesCache = sprites
  return sprites
}

/** سطل رنگ نسبی یک سرعت روی بازهٔ خود میدان (اندیس رمپ ۰ تا ۴). */
function relativeBucket(speed: number, range: [number, number]): number {
  const [min, max] = range
  const t = Math.min(Math.max((speed - min) / Math.max(max - min, 1e-6), 0), 1)
  return Math.min(Math.floor(t * WIND_SPEED_STOPS.length), WIND_SPEED_STOPS.length - 1)
}

/**
 * GeoJSON پیکان‌ها (نقطه + جهت + شفافیت) در فاز `phase` از چرخهٔ انیمیشن:
 * هر پیکان با اختلاف فاز خودش کمی جلو می‌رود، محو می‌شود و از نو شروع
 * می‌کند — «حرکت کوچک + سایه + تکرار» تا جهت جریان دقیقاً دیده شود.
 */
export function arrowChevronsGeoJson(field: WindField, phase = 0, stride = ARROW_STRIDE) {
  const arrows = arrowFeatures(field, stride)
  const range = fieldSpeedRange(field)
  const features = arrows.map((a, i) => {
    const t = (phase + ((i % 7) * 0.13 + Math.floor(i / 7) * 0.29)) % 1
    // حرکت کوتاه در راستای جریان (جهت هواشناسی + ۱۸۰)
    const heading = (a.direction_deg + 180) * (Math.PI / 180)
    const dx = Math.sin(heading)
    const dy = Math.cos(heading)
    const travelLat = kmToDegLat(ARROW_TRAVEL_KM) * t
    const travelLon = kmToDegLon(ARROW_TRAVEL_KM, a.lat) * t
    // محو: ورود سریع، خروج نرم — «بروز» ناگهانی ندارد
    const opacity = Math.min(1, t * 5) * (1 - t)
    return {
      type: 'Feature' as const,
      properties: {
        speed: a.speed_mps,
        heading: Number((a.direction_deg + 180).toFixed(1)),
        icon: `${ARROW_IMAGE_PREFIX}${relativeBucket(a.speed_mps, range)}`,
        fillOpacity: Number(opacity.toFixed(3)),
      },
      geometry: {
        type: 'Point' as const,
        coordinates: [a.lon + dx * travelLon, a.lat + dy * travelLat],
      },
    }
  })
  return { type: 'FeatureCollection' as const, features }
}

// پاک‌سازی انیمیشن با حذف نقشه — یک‌بار برای هر نقشه ثبت می‌شود
const removeHooked = new WeakSet<MapLibreMap>()

/** افزودن لایهٔ پیکان‌ها — بازگشت‌پذیر (idempotent): هر قطعه فقط اگر نبود اضافه می‌شود. */
export function addWindLayers(map: MapLibreMap): void {
  if (!map.getSource(ARROW_SOURCE)) {
    map.addSource(ARROW_SOURCE, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    })
  }
  // اسپرایت‌های پیکان (یک بار برای هر نقشه) — بعد از addImage لایهٔ symbol
  for (const [name, image] of Object.entries(buildArrowSprites())) {
    if (!map.hasImage(name)) {
      map.addImage(name, image, { pixelRatio: 2 })
    }
  }
  if (!map.getLayer(ARROW_LAYER)) {
    map.addLayer({
      id: ARROW_LAYER,
      type: 'symbol',
      source: ARROW_SOURCE,
      layout: {
        'symbol-placement': 'point',
        'icon-image': ['get', 'icon'],
        'icon-rotate': ['get', 'heading'],
        'icon-rotation-alignment': 'map',
        'icon-pitch-alignment': 'map',
        'icon-allow-overlap': true,
        'icon-ignore-placement': true,
        // اندازهٔ ثابت و ریز روی صفحه؛ کمی رشد نرم با زوم برای خوانایی
        'icon-size': ['interpolate', ['linear'], ['zoom'], 5, 0.5, 8, 0.8, 12, 1],
      },
      paint: {
        'icon-opacity': ['get', 'fillOpacity'],
      },
    })
  }
  if (!removeHooked.has(map)) {
    removeHooked.add(map)
    map.once('remove', stopArrowAnimation)
  }
  moveWindLayersBelowRoute(map)
}

/** میدان باد زیر خط مسیر بنشیند (خط مسیر و چک‌پوینت‌ها رو باشد). */
export function moveWindLayersBelowRoute(map: MapLibreMap): void {
  const routeLayer = 'route-line-layer' // همان ROUTE_LAYER_ID در MapView
  if (map.getLayer(ARROW_LAYER) && map.getLayer(routeLayer)) {
    map.moveLayer(ARROW_LAYER, routeLayer)
  }
  if (map.getLayer(FIELD_LAYER) && map.getLayer(ARROW_LAYER)) {
    map.moveLayer(FIELD_LAYER, ARROW_LAYER)
  }
}

/** پنهان/نمایان کردن لایه‌های باد (انیمیشن هنگام پنهان‌شدن می‌ایستد). */
export function setWindLayersVisible(map: MapLibreMap, visible: boolean): void {
  if (map.getLayer(ARROW_LAYER)) {
    map.setLayoutProperty(ARROW_LAYER, 'visibility', visible ? 'visible' : 'none')
  }
  if (map.getLayer(FIELD_LAYER)) {
    map.setLayoutProperty(FIELD_LAYER, 'visibility', visible ? 'visible' : 'none')
  }
  if (!visible) stopArrowAnimation()
}

// --- انیمیشن پیکان‌ها (حرکت کوتاه + محو + شروع دوباره) ---
// با requestAnimationFrame و سقف ~۳۰ فریم بر ثانیه — به‌روزرسانی ۲۵۰ فیچر
// GeoJSON در هر تیک سبک است، ولی لازم نیست ۶۰ بار در ثانیه انجام شود.
interface ArrowAnimState {
  map: MapLibreMap
  field: WindField
  raf: number
  phase: number
  lastTick: number
  lastDraw: number
}

let arrowAnim: ArrowAnimState | null = null

function drawArrows() {
  if (!arrowAnim) return
  const { map, field, phase } = arrowAnim
  try {
    const src = map.getSource(ARROW_SOURCE) as GeoJSONSource | undefined
    if (!src || !map.getLayer(ARROW_LAYER)) {
      stopArrowAnimation()
      return
    }
    src.setData(arrowChevronsGeoJson(field, phase))
  } catch {
    // نقشه حذف شده یا استایل عوض شده — انیمیشن چیزی برای کشیدن ندارد
    stopArrowAnimation()
  }
}

function tickArrows(now: number) {
  if (!arrowAnim) return
  const dt = arrowAnim.lastTick === 0 ? 0 : now - arrowAnim.lastTick
  arrowAnim.lastTick = now
  arrowAnim.phase = (arrowAnim.phase + dt / ARROW_CYCLE_MS) % 1
  // سقف ~۳۰ به‌روزرسانی در ثانیه — روان است و منابع را هدر نمی‌دهد
  if (now - arrowAnim.lastDraw >= 33) {
    arrowAnim.lastDraw = now
    drawArrows()
  }
  arrowAnim.raf = requestAnimationFrame(tickArrows)
}

function startArrowAnimation(map: MapLibreMap, field: WindField) {
  if (arrowAnim) {
    if (arrowAnim.map === map) {
      arrowAnim.field = field
      return
    }
    stopArrowAnimation()
  }
  arrowAnim = { map, field, raf: 0, phase: 0, lastTick: 0, lastDraw: 0 }
  arrowAnim.raf = requestAnimationFrame(tickArrows)
}

export function stopArrowAnimation() {
  if (arrowAnim) {
    cancelAnimationFrame(arrowAnim.raf)
    arrowAnim = null
  }
}

/** به‌روزرسانی دادهٔ میدان فعال (تصویر نرم + پیکان‌های متحرک) — بازگشت‌پذیر. */
export function updateWindField(map: MapLibreMap, field: WindField): void {
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
  if (!map.getSource(FIELD_SOURCE)) {
    map.addSource(FIELD_SOURCE, { type: 'image', ...payload })
  }
  ;(map.getSource(FIELD_SOURCE) as ImageSource).updateImage(payload)
  if (!map.getLayer(FIELD_LAYER)) {
    map.addLayer({
      id: FIELD_LAYER,
      type: 'raster',
      source: FIELD_SOURCE,
      paint: { 'raster-opacity': 0.85, 'raster-fade-duration': 0 },
    })
    moveWindLayersBelowRoute(map)
  }
  const arrowSource = map.getSource(ARROW_SOURCE) as GeoJSONSource | undefined
  arrowSource?.setData(arrowChevronsGeoJson(field, arrowAnim?.phase ?? 0))
  startArrowAnimation(map, field)
}

/**
 * اعمال میدان فعال — به‌جای گیتِ `isStyleLoaded` (که با منبع DEM ممکن است
 * مدت‌ها false بماند و همه‌چیز را قفل کند)، مستقیم تلاش می‌کنیم و روی خطا با
 * تایمر برمی‌گردیم. هر تابع زیر بازگشت‌پذیر است، پس تلاش مجدد بی‌هزینه است.
 */
export function applyWindField(map: MapLibreMap, field: WindField | null, attempt = 0): void {
  try {
    addWindLayers(map)
    if (!field) {
      setWindLayersVisible(map, false)
      return
    }
    setWindLayersVisible(map, true)
    updateWindField(map, field)
    // وقتی استایل در وضعیت نیمه‌لود (صف DEM) است، addLayer گاهی تا رندر
    // بعدی بی‌اثر می‌ماند — یک رندر صریح تضمین می‌کند لایه‌ها همان لحظه
    // دیده شوند.
    map.triggerRepaint()
  } catch {
    if (attempt < 100) {
      setTimeout(() => applyWindField(map, field, attempt + 1), 150)
    }
  }
}
