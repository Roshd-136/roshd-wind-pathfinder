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
 * رندر میدان باد روی MapLibre GL — **همهٔ لایه‌ها از ابتدا در استایل پایه
 * تعریف شده‌اند** (نقشهٔ رنگی، پیکان‌های سه ارتفاع) و این‌جا فقط دادهٔ
 * آن‌ها به‌روز می‌شود؛ افزودن لایه در زمان اجرا وقتی استایل در وضعیت
 * نیمه‌لود (صف DEM) است گاهی بی‌اثر می‌ماند و لایه هرگز رسم نمی‌شد — با
 * درخت لایهٔ ایستا این دسته باگ کلاً حذف شده است.
 *
 *  ۱) نقشهٔ حرارتی «نرم» — تصویر canvas با درون‌یابی دوخطی روی شبکه، رنگ
 *     نسبت به بازهٔ خود میدان (مثل صحنهٔ بصری‌سازی)،
 *  ۲) پیکان‌های باد — لایهٔ symbol با اسپرایت باریک ثابت‌اندازه که «کمی
 *     جلو می‌روند، محو می‌شوند و از نو شروع می‌کنند». در ۳بعدی همهٔ لایه‌های
 *     نمایان هم‌زمان رسم می‌شوند و رنگ هر لایه از پالت صحنهٔ مسیریابی
 *     می‌آید (در ۲بعدی تک‌لایه با رنگ سطل سرعت). قرارداد هواشناسی:
 *     `direction_deg` از کجا می‌وزد؛ پیکان به سمت جریان (جهت + ۱۸۰).
 */

const FIELD_SOURCE = 'wind-field-raster'
const FIELD_LAYER = 'wind-field-layer'
const ARROW_SOURCE_PREFIX = 'wind-arrows-'
const ARROW_LAYER_PREFIX = 'wind-arrows-layer-'
/** لایه‌های ارتفاعی باد — باید با لایه‌های تعریف‌شده در baseStyle یکی باشد. */
const WIND_ALTITUDES = [50, 200, 500] as const

/** پالت رنگ لایه‌های ارتفاعی — همان `_LAYER_PALETTE` صحنهٔ مسیریابی. */
const LAYER_COLORS: ReadonlyArray<[number, number, number]> = [
  [0x74, 0xb9, 0xff],
  [0x00, 0xce, 0xc9],
  [0xfd, 0xcb, 0x6e],
  [0xe8, 0x43, 0x93],
]

/** تصویر نرم میدان از شبکه (canvas → dataURL) — درون‌یابی دوخطی + رنگ نسبی. */
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
  const nLats = meta.lats.length
  const nLons = meta.lons.length

  // نمونه‌گیری دوخطی سرعت — نوارهای تیز سلولی به گرادیان پیوسته تبدیل می‌شود
  const sampleSpeed = (gx: number, gy: number): number => {
    const x = Math.min(Math.max(gx, 0), nLons - 1)
    const y = Math.min(Math.max(gy, 0), nLats - 1)
    const x0 = Math.min(Math.floor(x), nLons - 2)
    const y0 = Math.min(Math.floor(y), nLats - 2)
    const tx = x - x0
    const ty = y - y0
    const s00 = field.vectors[y0 * nLons + x0].speed_mps
    const s01 = field.vectors[y0 * nLons + x0 + 1].speed_mps
    const s10 = field.vectors[(y0 + 1) * nLons + x0].speed_mps
    const s11 = field.vectors[(y0 + 1) * nLons + x0 + 1].speed_mps
    return (s00 * (1 - tx) + s01 * tx) * (1 - ty) + (s10 * (1 - tx) + s11 * tx) * ty
  }

  for (let py = 0; py < height; py += 1) {
    // ردیف ۰ تصویر = شمال (بیشینهٔ عرض جغرافیایی)
    const gy = (1 - py / (height - 1)) * (nLats - 1)
    for (let px = 0; px < width; px += 1) {
      const gx = (px / (width - 1)) * (nLons - 1)
      const speed = sampleSpeed(gx, gy)
      const [r, g, b] = colorForFieldSpeed(speed, range)
      const alpha = 80 + Math.round(70 * Math.min((speed - range[0]) / Math.max(range[1] - range[0], 1e-6), 1))
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

const ARROW_IMAGE_PREFIX = 'wind-arrow-'
const LAYER_IMAGE_PREFIX = 'wind-layer-arrow-'
/** ابعاد بوم اسپرایت (پیکسل فیزیکی؛ با pixelRatio:۲ یعنی ~۲۲ پیکسل CSS). */
const ARROW_SPRITE_SIZE = 44

/** مسافتی که هر پیکان در یک چرخهٔ انیمیشن جلو می‌رود (کیلومتر). */
const ARROW_TRAVEL_KM = 3
/** طول یک چرخهٔ «حرکت + محو» (میلی‌ثانیه). */
const ARROW_CYCLE_MS = 1800
/** گام نمونه‌برداری پیکان‌ها از شبکهٔ میدان (چندلایه متراکم‌تر می‌شود). */
const ARROW_STRIDE = 2
const ARROW_STRIDE_MULTILAYER = 3

function kmToDegLat(km: number): number {
  return km / 111.32
}

function kmToDegLon(km: number, lat: number): number {
  return km / (111.32 * Math.max(Math.cos((lat * Math.PI) / 180), 0.2))
}

/** رسم یک پیکان باریک رو به شمال روی ctx — ساقهٔ نازک + سرِ کوچک. */
function drawArrow(ctx: CanvasRenderingContext2D, size: number, color: [number, number, number]): void {
  const [r, g, b] = color
  const cx = size / 2
  // ساقه: از پایین بوم تا نزدیک نوک — باریک ولی پررنگ
  ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.95)`
  ctx.lineWidth = 3.5
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(cx, size - 6)
  ctx.lineTo(cx, 11)
  ctx.stroke()
  // سرِ پیکان: مثلث توپر روی نوک
  ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.95)`
  ctx.beginPath()
  ctx.moveTo(cx, 2)
  ctx.lineTo(cx - 7, 14)
  ctx.lineTo(cx + 7, 14)
  ctx.closePath()
  ctx.fill()
}

let speedSpritesCache: Record<string, ImageData> | null = null
let layerSpritesCache: Record<string, ImageData> | null = null

/** اسپرایت‌های پیکان به رنگ سطل‌های رمپ سرعت — یک‌بار ساخته و کش می‌شود. */
function buildSpeedArrowSprites(): Record<string, ImageData> {
  if (speedSpritesCache) return speedSpritesCache
  const size = ARROW_SPRITE_SIZE
  const sprites: Record<string, ImageData> = {}
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  if (!ctx) return sprites
  for (const [index, stop] of WIND_SPEED_STOPS.entries()) {
    ctx.clearRect(0, 0, size, size)
    drawArrow(ctx, size, stop.color)
    sprites[`${ARROW_IMAGE_PREFIX}${index}`] = ctx.getImageData(0, 0, size, size)
  }
  speedSpritesCache = sprites
  return sprites
}

/** اسپرایت‌های پیکان به رنگ لایه‌های ارتفاعی (پالت صحنهٔ مسیریابی). */
function buildLayerArrowSprites(): Record<string, ImageData> {
  if (layerSpritesCache) return layerSpritesCache
  const size = ARROW_SPRITE_SIZE
  const sprites: Record<string, ImageData> = {}
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  if (!ctx) return sprites
  for (const [index, color] of LAYER_COLORS.entries()) {
    ctx.clearRect(0, 0, size, size)
    drawArrow(ctx, size, color)
    sprites[`${LAYER_IMAGE_PREFIX}${index}`] = ctx.getImageData(0, 0, size, size)
  }
  layerSpritesCache = sprites
  return sprites
}

/** ثبت اسپرایت‌ها روی نقشه — بازگشت‌پذیر؛ هر کدام فقط اگر نبود اضافه می‌شود. */
function ensureArrowSprites(map: MapLibreMap): void {
  for (const [name, image] of Object.entries(buildSpeedArrowSprites())) {
    if (!map.hasImage(name)) {
      map.addImage(name, image, { pixelRatio: 2 })
    }
  }
  for (const [name, image] of Object.entries(buildLayerArrowSprites())) {
    if (!map.hasImage(name)) {
      map.addImage(name, image, { pixelRatio: 2 })
    }
  }
}

/** سطل رنگ نسبی یک سرعت روی بازهٔ خود میدان (اندیس رمپ ۰ تا ۴). */
function relativeBucket(speed: number, range: [number, number]): number {
  const [min, max] = range
  const t = Math.min(Math.max((speed - min) / Math.max(max - min, 1e-6), 0), 1)
  return Math.min(Math.floor(t * WIND_SPEED_STOPS.length), WIND_SPEED_STOPS.length - 1)
}

interface ArrowGeoJsonOptions {
  phase: number
  stride: number
  /** آیکون هر پیکان بر اساس سرعت — سطل سرعت یا رنگ لایه. */
  iconFor: (speed: number) => string
}

/**
 * GeoJSON پیکان‌ها (نقطه + جهت + شفافیت) در فاز `phase` از چرخهٔ انیمیشن:
 * هر پیکان با اختلاف فاز خودش کمی جلو می‌رود، محو می‌شود و از نو شروع
 * می‌کند — «حرکت کوچک + سایه + تکرار» تا جهت جریان دقیقاً دیده شود.
 */
export function arrowChevronsGeoJson(field: WindField, opts: ArrowGeoJsonOptions) {
  const arrows = arrowFeatures(field, opts.stride)
  const features = arrows.map((a, i) => {
    const t = (opts.phase + ((i % 7) * 0.13 + Math.floor(i / 7) * 0.29)) % 1
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
        icon: opts.iconFor(a.speed_mps),
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

/**
 * نمایش/پنهان‌سازی گروهی باد (نقشهٔ رنگی + همهٔ لایه‌های پیکان) — برای
 * کلیدهای تنظیمات «نمای نقشه».
 */
export function setWindOverlaysVisible(
  map: MapLibreMap,
  visible: { heatmap: boolean; arrows: boolean },
): void {
  if (map.getLayer(FIELD_LAYER)) {
    map.setLayoutProperty(FIELD_LAYER, 'visibility', visible.heatmap ? 'visible' : 'none')
  }
  for (const altitude of WIND_ALTITUDES) {
    const layerId = `${ARROW_LAYER_PREFIX}${altitude}`
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, 'visibility', visible.arrows ? 'visible' : 'none')
    }
  }
  if (!visible.heatmap && !visible.arrows) stopArrowAnimation()
}

// --- انیمیشن پیکان‌ها (حرکت کوتاه + محو + شروع دوباره) ---
// با requestAnimationFrame و سقف ~۳۰ فریم بر ثانیه — به‌روزرسانی چند صد فیچر
// GeoJSON در هر تیک سبک است، ولی لازم نیست ۶۰ بار در ثانیه انجام شود.
interface ArrowAnimState {
  map: MapLibreMap
  fields: WindField[]
  /** رنگ لایه‌ای فقط در حالت چندلایه (۳بعدی) استفاده می‌شود. */
  multiLayer: boolean
  raf: number
  phase: number
  lastTick: number
  lastDraw: number
}

let arrowAnim: ArrowAnimState | null = null

function drawArrows() {
  if (!arrowAnim) return
  const { map, fields, multiLayer, phase } = arrowAnim
  try {
    let drewAny = false
    fields.forEach((field, index) => {
      const layerId = `${ARROW_LAYER_PREFIX}${field.altitude_m}`
      if (!map.getLayer(layerId)) return
      const src = map.getSource(`${ARROW_SOURCE_PREFIX}${field.altitude_m}`) as
        | GeoJSONSource
        | undefined
      if (!src) return
      src.setData(
        arrowChevronsGeoJson(field, {
          phase,
          stride: multiLayer ? ARROW_STRIDE_MULTILAYER : ARROW_STRIDE,
          iconFor: multiLayer
            ? () => `${LAYER_IMAGE_PREFIX}${index % LAYER_COLORS.length}`
            : (speed) => `${ARROW_IMAGE_PREFIX}${relativeBucket(speed, fieldSpeedRange(field))}`,
        }),
      )
      drewAny = true
    })
    if (!drewAny) stopArrowAnimation()
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

function startArrowAnimation(map: MapLibreMap, fields: WindField[], multiLayer: boolean) {
  if (arrowAnim) {
    if (arrowAnim.map === map) {
      arrowAnim.fields = fields
      arrowAnim.multiLayer = multiLayer
      return
    }
    stopArrowAnimation()
  }
  arrowAnim = { map, fields, multiLayer, raf: 0, phase: 0, lastTick: 0, lastDraw: 0 }
  arrowAnim.raf = requestAnimationFrame(tickArrows)
}

export function stopArrowAnimation() {
  if (arrowAnim) {
    cancelAnimationFrame(arrowAnim.raf)
    arrowAnim = null
  }
}

/** به‌روزرسانی تصویر نرم میدان فعال (اولین لایهٔ نمایان) — منبع در استایل است. */
function updateFieldImage(map: MapLibreMap, field: WindField): void {
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
  const imageSource = map.getSource(FIELD_SOURCE) as ImageSource | undefined
  if (!imageSource) return
  // مهم: `updateImage` فقط url را عوض می‌کند و مختصات جای‌نگهدار استایل
  // باقی می‌ماند (تصویر در جای اشتباه نقش می‌بست) — مختصات را صریح ست می‌کنیم.
  imageSource.setCoordinates(payload.coordinates)
  imageSource.updateImage({ url: payload.url })
}

/**
 * اعمال میدان‌های نمایان — تک‌لایه در ۲بعدی (رنگ سطل سرعت) و همهٔ لایه‌ها
 * با رنگ لایه در ۳بعدی (مثل صحنهٔ مسیریابی). هیچ لایه‌ای add نمی‌شود —
 * لایه‌ها از ابتدا در استایل‌اند و این‌جا فقط داده و دید هرکدام تنظیم
 * می‌شود؛ روی خطا با تایمر دوباره تلاش می‌شود.
 */
export function applyWindFields(
  map: MapLibreMap,
  fields: WindField[],
  opts: {
    multiLayer: boolean
    showHeatmap: boolean
    showArrows: boolean
    attempt?: number
  } = { multiLayer: false, showHeatmap: true, showArrows: true },
): void {
  const attempt = opts.attempt ?? 0
  try {
    ensureArrowSprites(map)
    const ordered = [...fields].sort((a, b) => a.altitude_m - b.altitude_m)
    if (ordered.length > 0 && opts.showHeatmap) {
      updateFieldImage(map, ordered[0])
    }
    // نقشهٔ رنگی: فقط لایهٔ فعال (اولین نمایان) — در هر دو حالت
    if (map.getLayer(FIELD_LAYER)) {
      const heatmapVisible = ordered.length > 0 && opts.showHeatmap
      map.setLayoutProperty(FIELD_LAYER, 'visibility', heatmapVisible ? 'visible' : 'none')
    }
    // پیکان‌ها: ۲بعدی = فقط لایهٔ فعال؛ ۳بعدی = همهٔ لایه‌های نمایان.
    for (const altitude of WIND_ALTITUDES) {
      const layerId = `${ARROW_LAYER_PREFIX}${altitude}`
      if (!map.getLayer(layerId)) continue
      const field = ordered.find((f) => f.altitude_m === altitude)
      const visible = Boolean(
        field && opts.showArrows && (opts.multiLayer || field.altitude_m === ordered[0]?.altitude_m),
      )
      map.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none')
      if (field) {
        // رنگ لایه‌ای بر اساس جایگاه در فهرست نمایان‌ها — هماهنگ با drawArrows
        const layerIdx = ordered.findIndex((f) => f.altitude_m === altitude)
        const src = map.getSource(`${ARROW_SOURCE_PREFIX}${altitude}`) as GeoJSONSource
        src.setData(
          arrowChevronsGeoJson(field, {
            phase: arrowAnim?.phase ?? 0,
            stride: opts.multiLayer ? ARROW_STRIDE_MULTILAYER : ARROW_STRIDE,
            iconFor: opts.multiLayer
              ? () => `${LAYER_IMAGE_PREFIX}${layerIdx % LAYER_COLORS.length}`
              : (speed) => `${ARROW_IMAGE_PREFIX}${relativeBucket(speed, fieldSpeedRange(field))}`,
          }),
        )
      }
    }
    if (ordered.length > 0 && opts.showArrows) {
      startArrowAnimation(map, ordered, opts.multiLayer)
    } else {
      stopArrowAnimation()
    }
    // یک رندر صریح — تضمین دیده‌شدن فوری داده‌های تازه
    map.triggerRepaint()
  } catch {
    if (attempt < 100) {
      setTimeout(
        () => applyWindFields(map, fields, { ...opts, attempt: attempt + 1 }),
        150,
      )
    }
  }
}
