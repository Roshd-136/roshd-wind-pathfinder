import type { GeoJSONSource, ImageSource, Map as MapLibreMap } from 'maplibre-gl'
import type { WindField } from '../../../types/routing'
import { WIND_ARROW_CONFIG, WIND_PARTICLE_CONFIG } from '../../../config/mapDisplay'
import {
  arrowFeatures,
  colorForFieldSpeed,
  fieldSpeedRange,
  gridMeta,
  sampleWindAtPoint,
  WIND_SPEED_STOPS,
} from '../../../utils/windField'

/**
 * رندر میدان باد روی MapLibre GL — **همهٔ لایه‌ها از ابتدا در استایل پایه
 * تعریف شده‌اند** (نقشهٔ رنگی، پیکان‌های جهت باد، ذرات جریان باد) و این‌جا
 * فقط دادهٔ آن‌ها به‌روز می‌شود؛ افزودن لایه در زمان اجرا وقتی استایل در
 * وضعیت نیمه‌لود (صف DEM) است گاهی بی‌اثر می‌ماند و لایه هرگز رسم نمی‌شد —
 * با درخت لایهٔ ایستا این دسته باگ کلاً حذف شده است.
 *
 *  ۱) نقشهٔ حرارتی «نرم» — تصویر canvas با **درون‌یابی دوخطی واقعی** روی
 *     شبکه (نه نزدیک‌ترین سلول) و رنگ نسبت به بازهٔ خود میدان — بدون لبهٔ
 *     کاشی‌مانند بین سلول‌ها؛
 *  ۲) **پیکان‌های جهت باد** — شبکهٔ ثابت اسپرایت (هر `stride` سلول یکی) که
 *     جهت لحظه‌ای باد را در هر سلول نشان می‌دهند؛ رنگ هر پیکان سطلِ نسبی
 *     سرعت روی بازهٔ خود میدان است (هماهنگ با طیف راهنما) و چرخش با جهت
 *     جریان. برخلاف ذرات، این پیکان‌ها همیشه دیده می‌شوند — مرجع پایدار
 *     «باد از کجا به کجا»؛
 *  ۳) **ذرات جریان باد** (سبک windy) — ذرات ریز که پیوسته در امتداد بردار
 *     محلی باد حرکت می‌کنند و ردّ کوتاه می‌گذارند. هر ذره یک شیء `Arrow`
 *     است که دُم و نوک را **در یک هندسهٔ واحد** (MultiLineString) می‌سازد؛
 *     باگ «نوک جداشده از دُم» از جنس دو-منبع-دو-setData بود و با اتحاد
 *     هندسی کلاً حذف شده — نوک و دُم همیشه در یک قاب اعمال می‌شوند.
 *     در حالت چندلایه (۳بعدی) **هر میدانِ نمایان مجموعه ذرات خودش را دارد**.
 *     قرارداد هواشناسی: `direction_deg` از کجا می‌وزد؛ پیکان/حرکت به سمت
 *     جریان (جهت + ۱۸۰).
 */

const FIELD_SOURCE = 'wind-field-raster'
const FIELD_LAYER = 'wind-field-layer'
const ARROW_SOURCE = 'wind-arrows'
const ARROW_LAYER = 'wind-arrows-layer'
const PARTICLE_SOURCE = 'wind-particles'
const PARTICLE_LAYER = 'wind-particles-layer'

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

  const nLon = meta.lons.length
  const nLat = meta.lats.length
  /** سرعت در مختصات شبکه‌ای پیوسته (fx, fy) با درون‌یابی دوخطی واقعی —
   * پیش‌تر نزدیک‌ترین سلول برمی‌گشت و هر سلول یک «کاشی» رنگ یکدست می‌شد. */
  const speedAt = (fx: number, fy: number): number => {
    const cx = Math.min(Math.max(fx, 0), nLon - 1)
    const cy = Math.min(Math.max(fy, 0), nLat - 1)
    const c0 = Math.floor(cx)
    const r0 = Math.floor(cy)
    const c1 = Math.min(c0 + 1, nLon - 1)
    const r1 = Math.min(r0 + 1, nLat - 1)
    const tx = cx - c0
    const ty = cy - r0
    const s00 = lookupSpeed(r0, c0)
    const s01 = lookupSpeed(r0, c1)
    const s10 = lookupSpeed(r1, c0)
    const s11 = lookupSpeed(r1, c1)
    return (s00 * (1 - tx) + s01 * tx) * (1 - ty) + (s10 * (1 - tx) + s11 * tx) * ty
  }
  const lookupSpeed = (row: number, col: number): number => {
    const v = field.vectors[row * nLon + col]
    return v ? v.speed_mps : (range[0] + range[1]) / 2
  }

  for (let py = 0; py < height; py += 1) {
    // ردیف ۰ تصویر = شمال (بیشینهٔ عرض جغرافیایی) — fy بر حسب ایندکس شبکه
    const fy = (1 - py / (height - 1)) * (nLat - 1)
    for (let px = 0; px < width; px += 1) {
      const fx = (px / (width - 1)) * (nLon - 1)
      const speed = speedAt(fx, fy)
      const [r, g, b] = colorForFieldSpeed(speed, range)
      const alpha =
        80 + Math.round(70 * Math.min((speed - range[0]) / Math.max(range[1] - range[0], 1e-6), 1))
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

/** به‌روزرسانی تصویر نرم میدان فعال — منبع در استایل است. */
function updateFieldImage(map: MapLibreMap, field: WindField): void {
  const meta = gridMeta(field)
  const latMax = meta.lats[meta.lats.length - 1]
  const latMin = meta.lats[0]
  const lonMin = meta.lons[0]
  const lonMax = meta.lons[meta.lons.length - 1]
  const imageSource = map.getSource(FIELD_SOURCE) as ImageSource | undefined
  if (!imageSource) return
  // مهم: `updateImage` فقط url را عوض می‌کند و مختصات جای‌نگهدار استایل
  // باقی می‌ماند (تصویر در جای اشتباه نقش می‌بست) — مختصات را صریح ست می‌کنیم.
  imageSource.setCoordinates([
    [lonMin, latMax],
    [lonMax, latMax],
    [lonMax, latMin],
    [lonMin, latMin],
  ])
  imageSource.updateImage({ url: buildFieldImage(field) })
}

// ---------------------------------------------------------------------------
// پیکان‌های ثابت جهت باد — شبکهٔ اسپرایت روی سلول‌های میدان. هر اسپرایت رو به
// شمال رسم می‌شود و چرخش نماد با جهت جریان (جهت هواشناسی + ۱۸۰) اعمال می‌شود؛
// رنگ هر پیکان سطل نسبی سرعت روی بازهٔ خود میدان است تا با نقشهٔ رنگی و طیف
// راهنما هم‌خوان بماند.
// ---------------------------------------------------------------------------

const ARROW_IMAGE_PREFIX = 'wind-arrow-'

/** رسم پیکان رو به شمال روی ctx — بر پایهٔ هندسهٔ `WIND_ARROW_CONFIG`. */
function drawArrow(
  ctx: CanvasRenderingContext2D,
  size: number,
  color: [number, number, number],
): void {
  const [r, g, b] = color
  const cx = size / 2
  const geo = WIND_ARROW_CONFIG.geometry
  const span = (geo.baseY - geo.tipY) * size
  const top = (size - span) / 2
  const tipY = top
  const headBaseY = top + (geo.headBaseY - geo.tipY) * size
  const shaftTopY = top + (geo.shaftTopY - geo.tipY) * size
  const baseY = top + (geo.baseY - geo.tipY) * size
  const headHalf = geo.headHalfWidth * size
  const shaftHalf = WIND_ARROW_CONFIG.shaftWidth / 2
  // ساقه: مستطیل دقیق (بدون خطای lineCap در طول)
  ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.98)`
  ctx.fillRect(cx - shaftHalf, shaftTopY, shaftHalf * 2, baseY - shaftTopY)
  // سرِ پیکان: مثلث توپر
  ctx.beginPath()
  ctx.moveTo(cx, tipY)
  ctx.lineTo(cx - headHalf, headBaseY)
  ctx.lineTo(cx + headHalf, headBaseY)
  ctx.closePath()
  ctx.fill()
}

let arrowSpritesCache: Record<string, ImageData> | null = null

/** اسپرایت‌های پیکان به رنگ سطل‌های رمپ سرعت — یک‌بار ساخته و کش می‌شود. */
function buildArrowSprites(): Record<string, ImageData> {
  if (arrowSpritesCache) return arrowSpritesCache
  const size = WIND_ARROW_CONFIG.spriteSize
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
  arrowSpritesCache = sprites
  return sprites
}

/** ثبت اسپرایت‌ها روی نقشه — بازگشت‌پذیر؛ هر کدام فقط اگر نبود اضافه می‌شود. */
function ensureArrowImages(map: MapLibreMap): void {
  for (const [name, image] of Object.entries(buildArrowSprites())) {
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

/** به‌روزرسانی شبکهٔ پیکان‌های جهت باد برای میدان فعال — منبع در استایل است. */
function updateArrowLayer(map: MapLibreMap, field: WindField): void {
  ensureArrowImages(map)
  const source = map.getSource(ARROW_SOURCE) as GeoJSONSource | undefined
  if (!source) return
  const range = fieldSpeedRange(field)
  const features = arrowFeatures(field, WIND_ARROW_CONFIG.stride).map((arrow) => ({
    type: 'Feature' as const,
    properties: {
      // چرخش نماد = جهت جریان (هواشناسی + ۱۸۰) — اسپرایت رو به شمال است
      direction: Number(((arrow.direction_deg + 180) % 360).toFixed(1)),
      icon: `${ARROW_IMAGE_PREFIX}${relativeBucket(arrow.speed_mps, range)}`,
    },
    geometry: { type: 'Point' as const, coordinates: [arrow.lon, arrow.lat] },
  }))
  source.setData({ type: 'FeatureCollection', features })
}

// ---------------------------------------------------------------------------
// ذرات جریان باد — ذرات ریز که پیوسته در امتداد بردار محلی باد حرکت می‌کنند
// و ردّ کوتاه می‌گذارند. هر ذره یک **شیء Arrow** است: جابه‌جایی، رنگ و
// هندسهٔ دُم+نوک همه در یک کلاس؛ نوک فلش دو بالِ شُکاف در همان MultiLineString
// ردّ است، پس در یک setData با دُم اعمال می‌شود و هرگز از آن جدا نمی‌افتد.
// ---------------------------------------------------------------------------

/** حاصل‌جمع نرمال‌شدهٔ دو بردار جغرافیایی (lon/lat مستقیم — صرفاً نمایشی). */
function unitDir(dx: number, dy: number): [number, number] {
  const len = Math.hypot(dx, dy)
  return len > 1e-12 ? [dx / len, dy / len] : [0, 1]
}

/**
 * کلاس Arrow — یک ذرهٔ باد: دُم (ردّ نقاط) + نوک فلش (دو بالِ شُکاف) در
 * **یک هندسهٔ MultiLineString**. مسئولیت وضعیت (موقعیت، عمر، رنگ) و شکل
 * (هندسهٔ ردّ و نوک) هر دو در همین کلاس است — برخلاف نسخهٔ قبلی که نوک،
 * لایهٔ symbol جدا با sprite و setData مستقل بود و در قاب جدا اعمال می‌شد.
 */
export class WindArrow {
  lon: number
  lat: number
  /** ردّ ذره — آخرین نقاط مسیر، سرِ ردّ = آخرین عنصر. */
  trail: [number, number][]
  ageMs: number
  lifetimeMs: number
  /** سرعت محلی آخرین نمونه — برای رنگ ردّ. */
  speedMps: number
  /** رنگ ردّ — نسبت به بازهٔ میدان خود ذره (در هر tick به‌روز می‌شود). */
  color = 'rgb(37, 99, 235)'
  /** ضخامت ردّ — لایه‌های بالاتر کمی نازک‌تر تا لایه‌ها قابل تفکیک باشند. */
  widthPx: number
  /** کدری عمر ذره (۰ تا ۱) — ورود نرم/خروج نرم. */
  opacity = 0

  constructor(lon: number, lat: number, lifetimeMs: number, widthPx: number) {
    this.lon = lon
    this.lat = lat
    this.lifetimeMs = lifetimeMs
    this.widthPx = widthPx
    this.trail = [[lon, lat]]
    this.ageMs = 0
    this.speedMps = 0
  }

  /** جابه‌جایی به سمت جریان + ثبت نقطهٔ جدید در ردّ. */
  advance(
    headingRad: number,
    distDeg: number,
    dtMs: number,
    bbox: { lonMin: number; latMin: number; lonMax: number; latMax: number },
    trailPoints: number,
  ): boolean {
    this.lon += Math.sin(headingRad) * distDeg
    this.lat += Math.cos(headingRad) * distDeg
    this.ageMs += dtMs
    const outOfField =
      this.lon < bbox.lonMin ||
      this.lon > bbox.lonMax ||
      this.lat < bbox.latMin ||
      this.lat > bbox.latMax
    if (outOfField || this.ageMs > this.lifetimeMs) {
      this.respawn(bbox)
      return true
    }
    this.trail.push([this.lon, this.lat])
    while (this.trail.length > trailPoints) this.trail.shift()
    return false
  }

  /** تولد دوبارهٔ بی‌سروصدا در جای تازه — ردّ از یک نقطه شروع می‌شود. */
  respawn(bbox: { lonMin: number; latMin: number; lonMax: number; latMax: number }): void {
    this.lon = bbox.lonMin + Math.random() * (bbox.lonMax - bbox.lonMin)
    this.lat = bbox.latMin + Math.random() * (bbox.latMax - bbox.latMin)
    this.ageMs = 0
    this.trail = [[this.lon, this.lat]]
  }

  /** ضریب محو ذره در طول عمر — ورود نرم و خروج نرم (سبک windy). */
  private opacityNow(): number {
    const life = Math.min(this.ageMs / this.lifetimeMs, 1)
    const { inFraction, outFraction, baseOpacity } = WIND_PARTICLE_CONFIG.fade
    const fadeIn = Math.min(life / inFraction, 1)
    const fadeOut = Math.min((1 - life) / outFraction, 1)
    return Math.max(0, Math.min(fadeIn, fadeOut)) * baseOpacity
  }

  /**
   * هندسهٔ واحد دُم + نوک. نوک = دو بالِ شُکاف که از **نقطهٔ سر ردّ** رو به
   * عقب باز می‌شوند؛ طول هر بال نسبت به گام آخر ذره (سرعت نمایشی فعلی) —
   * در ذرهٔ کند کوچک، در ذرهٔ تند بزرگ‌تر، با سقف مطلق. چون بال‌ها عضو همان
   * MultiLineString ردّ‌اند، «نوک جداشده از دُم» از نظر ساختاری ممکن نیست.
   */
  geometry(): {
    color: string
    width: number
    opacity: number
    lines: [number, number][][]
  } {
    const lines: [number, number][][] = [this.trail]
    if (this.trail.length >= 2) {
      const head = this.trail[this.trail.length - 1]
      const prev = this.trail[this.trail.length - 2]
      const [ux, uy] = unitDir(head[0] - prev[0], head[1] - prev[1])
      const step = Math.hypot(head[0] - prev[0], head[1] - prev[1])
      const len = Math.min(step * WIND_PARTICLE_CONFIG.head.lengthFactor, WIND_PARTICLE_CONFIG.head.maxLenDeg)
      const spread = (WIND_PARTICLE_CONFIG.head.spreadDeg * Math.PI) / 180
      const backX = -ux * Math.cos(spread)
      const backY = -uy * Math.cos(spread)
      const wing = len * Math.sin(spread)
      // بال‌ها از نقطهٔ سر ردّ به عقب-چپ و عقب-راست؛ در سرِ ردّ به هم می‌رسند
      lines.push([
        [head[0] + backX * len - uy * wing, head[1] + backY * len + ux * wing],
        head,
        [head[0] + backX * len + uy * wing, head[1] + backY * len - ux * wing],
      ])
    }
    return { color: this.color, width: this.widthPx, opacity: this.opacityNow(), lines }
  }
}

/** PRNG قطعی (mulberry32) — همان seed همیشه همان جریان را می‌سازد. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = Math.imul(t ^ (t >>> 7), 61 | t)
    t = t + 0x6e2d1ffc | 0
    a = (a ^ (t >>> 15)) >>> 0
    return t / 4294967296
  }
}

function fieldBbox(
  field: WindField,
): { lonMin: number; latMin: number; lonMax: number; latMax: number } {
  const meta = gridMeta(field)
  return {
    lonMin: meta.lons[0],
    latMin: meta.lats[0],
    lonMax: meta.lons[meta.lons.length - 1],
    latMax: meta.lats[meta.lats.length - 1],
  }
}

const WIND_PARTICLE_RAMP: ReadonlyArray<{ t: number; color: string }> = [
  { t: 0, color: 'rgb(37, 99, 235)' },
  { t: 0.25, color: 'rgb(34, 197, 94)' },
  { t: 0.5, color: 'rgb(234, 179, 8)' },
  { t: 0.75, color: 'rgb(249, 115, 22)' },
  { t: 1, color: 'rgb(239, 68, 68)' },
]

/** رنگ رمپ برای t ∈ [0,1] — درون‌یابی خطی بین دو توقف مجاور. */
function rampColorFor(t: number): string {
  const clamped = Math.min(Math.max(t, 0), 1)
  for (let i = 0; i < WIND_PARTICLE_RAMP.length - 1; i += 1) {
    const a = WIND_PARTICLE_RAMP[i]
    const b = WIND_PARTICLE_RAMP[i + 1]
    if (clamped <= b.t) {
      const f = (clamped - a.t) / Math.max(b.t - a.t, 1e-6)
      const mix = (s: string, e: string) => {
        const ps = s.match(/\d+/g)?.map(Number) ?? [255, 255, 255]
        const pe = e.match(/\d+/g)?.map(Number) ?? [255, 255, 255]
        return `rgb(${Math.round(ps[0] + (pe[0] - ps[0]) * f)}, ${Math.round(
          ps[1] + (pe[1] - ps[1]) * f,
        )}, ${Math.round(ps[2] + (pe[2] - ps[2]) * f)})`
      }
      return mix(a.color, b.color)
    }
  }
  return WIND_PARTICLE_RAMP[WIND_PARTICLE_RAMP.length - 1].color
}

/** به‌روزرسانی رنگ/ضخامت ذره — رنگ نسبت به بازهٔ میدانِ خودش. */
function styleArrow(arrow: WindArrow, field: WindField, layerIndex: number): void {
  const [min, max] = fieldSpeedRange(field)
  const t = Math.min(Math.max((arrow.speedMps - min) / Math.max(max - min, 1e-6), 0), 1)
  arrow.color = rampColorFor(t)
  // لایه‌های بالاتر کمی نازک‌تر — تفکیک بصری لایه‌ها روی هم
  arrow.widthPx = WIND_PARTICLE_CONFIG.trailWidth * (1 - layerIndex * 0.2)
}

/** GeoJSON واحد دُم+نوک — هر ذره یک Feature با MultiLineString. */
function arrowGeoJson(layers: LayerParticles[]) {
  return {
    type: 'FeatureCollection' as const,
    features: layers.flatMap(({ arrows }) =>
      arrows.map((a) => {
        const geom = a.geometry()
        return {
          type: 'Feature' as const,
          properties: { color: geom.color, width: geom.width, opacity: geom.opacity },
          geometry: { type: 'MultiLineString' as const, coordinates: geom.lines },
        }
      }),
    ),
  }
}

interface LayerParticles {
  field: WindField
  arrows: WindArrow[]
}

interface FlowState {
  map: MapLibreMap
  /** میدان‌های فعال با ذراتشان — در ۳بعدی چندلایه، بیش از یکی. */
  layers: LayerParticles[]
  timer: ReturnType<typeof setInterval>
  lastTick: number
  prng: () => number
  /** توقف حرکت — قاب فعلی بدون پیش‌بردن زمان روی نقشه می‌ماند (کلید تنظیمات نما). */
  paused: boolean
}

let flow: FlowState | null = null
/** ترجیح توقف حرکت ذرات — در ساخت دوبارهٔ جریان (تغییر میدان/بازگشت لایه) حفظ می‌شود. */
let flowPaused = false

/** رندر یک‌بارهٔ وضعیت فعلی ذرات، بدون پیش‌بردن زمان — برای حالت توقف حرکت. */
function renderFrozenFlow(): void {
  if (!flow) return
  try {
    for (const { field, arrows } of flow.layers) {
      const li = flow.layers.indexOf(flow.layers.find((l) => l.field === field) ?? flow.layers[0])
      for (const a of arrows) {
        // در حالت توقف هم رنگ ذره از میدانِ فعلی نمونه‌برداری می‌شود تا با
        // تغییر لایهٔ ارتفاع، قاب ثابت رنگ درست بگیرد
        a.speedMps = sampleWindAtPoint(field, a.lat, a.lon).speed_mps
        styleArrow(a, field, li)
      }
    }
    const src = flow.map.getSource(PARTICLE_SOURCE) as GeoJSONSource | undefined
    if (!src) return
    src.setData(arrowGeoJson(flow.layers))
  } catch {
    // نقشه حذف شده یا استایل عوض شده — کاری نمی‌کنیم
  }
}

/** کلید پایداری جریان — با تغییر مجموعهٔ ارتفاع‌ها جریان از نو ساخته می‌شود. */
function layerKey(layers: LayerParticles[]): string {
  return layers.map((l) => l.field.altitude_m).join(',')
}

function startParticleFlow(
  map: MapLibreMap,
  fields: WindField[],
  countPerField?: number,
): void {
  const layers: LayerParticles[] = []
  const prng = mulberry32(WIND_PARTICLE_CONFIG.seed)
  const count = countPerField ?? WIND_PARTICLE_CONFIG.count
  for (const field of fields) {
    const bbox = fieldBbox(field)
    const arrows: WindArrow[] = []
    for (let i = 0; i < count; i += 1) {
      const lon = bbox.lonMin + prng() * (bbox.lonMax - bbox.lonMin)
      const lat = bbox.latMin + prng() * (bbox.latMax - bbox.latMin)
      const lifetime = WIND_PARTICLE_CONFIG.lifetimeMs * (0.5 + prng() * 0.5)
      const widthPx = WIND_PARTICLE_CONFIG.trailWidth
      const arrow = new WindArrow(lon, lat, lifetime, widthPx)
      styleArrow(arrow, field, layers.length)
      arrows.push(arrow)
    }
    layers.push({ field, arrows })
  }
  if (layerKey(layers) === layerKey(flow?.layers ?? [])) {
    // همان میدان‌ها — جریان قبلی را نگه دار (ذرات جای نپَرند)
    return
  }
  stopParticleFlow()
  flow = {
    map,
    layers,
    timer: setInterval(tickFlow, WIND_PARTICLE_CONFIG.tickMs),
    lastTick: performance.now(),
    prng,
    paused: flowPaused,
  }
  // در حالت توقف فقط یک قاب رسم می‌شود؛ ازسرگیری از همان ذرات ادامه می‌یابد
  if (flow.paused) renderFrozenFlow()
  else tickFlow()
}

/** توقف/ازسرگیری حرکت ذرات — هنگام توقف، قاب فعلی ثابت روی نقشه می‌ماند. */
export function setParticleFlowPaused(paused: boolean): void {
  flowPaused = paused
  if (!flow) return
  flow.paused = paused
  // پس از ازسرگیری، فاصلهٔ زمانیِ توقف نباید یک‌جا جابه‌جا شود
  if (!paused) flow.lastTick = performance.now()
}

export function stopParticleFlow(): void {
  if (flow) {
    clearInterval(flow.timer)
    flow = null
  }
}

/** نمایش/پنهان‌سازی گروهی باد (نقشهٔ رنگی + پیکان‌های جهت + ذرات جریان). */
export function setWindOverlaysVisible(
  map: MapLibreMap,
  visible: { heatmap: boolean; arrows: boolean; particles: boolean },
): void {
  if (map.getLayer(FIELD_LAYER)) {
    map.setLayoutProperty(FIELD_LAYER, 'visibility', visible.heatmap ? 'visible' : 'none')
  }
  if (map.getLayer(ARROW_LAYER)) {
    map.setLayoutProperty(ARROW_LAYER, 'visibility', visible.arrows ? 'visible' : 'none')
  }
  if (map.getLayer(PARTICLE_LAYER)) {
    map.setLayoutProperty(PARTICLE_LAYER, 'visibility', visible.particles ? 'visible' : 'none')
  }
  if (!visible.particles) stopParticleFlow()
}

function tickFlow(): void {
  if (!flow) return
  // در حالت توقف، آخرین قاب سر جای خودش می‌ماند — ذرات ثابت دیده می‌شوند
  if (flow.paused) return
  const { map, layers } = flow
  try {
    const src = map.getSource(PARTICLE_SOURCE) as GeoJSONSource | undefined
    if (!src || !map.getSource(FIELD_SOURCE)) {
      stopParticleFlow()
      return
    }
    const now = performance.now()
    const dtMs = Math.min(now - flow.lastTick, 120)
    flow.lastTick = now
    const dtSec = dtMs / 1000

    for (let li = 0; li < layers.length; li += 1) {
      const { field, arrows } = layers[li]
      const bbox = fieldBbox(field)
      for (const a of arrows) {
        const sample = sampleWindAtPoint(field, a.lat, a.lon)
        const heading = (sample.direction_deg + 180) * (Math.PI / 180)
        // حرکت نمایشی: هر m/s باد → چند صدم درجه در ثانیه (از کانفیگ)
        const dist = sample.speed_mps * WIND_PARTICLE_CONFIG.degPerSecPerMps * dtSec
        const respawned = a.advance(heading, dist, dtMs, bbox, WIND_PARTICLE_CONFIG.trailPoints)
        if (!respawned) a.speedMps = sample.speed_mps
        styleArrow(a, field, li)
      }
    }
    // **یک setData برای دُم+نوک** — هندسهٔ واحد هر ذره در یک قاب اعمال می‌شود
    src.setData(arrowGeoJson(layers))
  } catch {
    // نقشه حذف شده یا استایل عوض شده — جریان چیزی برای رسم ندارد
    stopParticleFlow()
  }
}

/**
 * اعمال میدان‌های نمایان — نقشهٔ رنگی روی لایهٔ فعال، پیکان‌های جهت باد روی
 * میدان فعال و جریان ذرات روی میدان‌های نمایان. در حالت چندلایه (۳بعدی)
 * **هر میدان مجموعه ذرات خودش** را دارد (رنگ/سطل نسبت به بازهٔ همان میدان)؛
 * در ۲بعدی فقط پایین‌ترین. هیچ لایه‌ای add نمی‌شود — لایه‌ها از ابتدا در
 * استایل‌اند و این‌جا فقط داده و دید هرکدام تنظیم می‌شود؛ روی خطا با تایمر
 * دوباره تلاش می‌شود.
 */
export function applyWindFields(
  map: MapLibreMap,
  fields: WindField[],
  opts: {
    multiLayer: boolean
    showHeatmap: boolean
    /** پیکان‌های ثابت جهت باد */
    showArrows: boolean
    /** ذرات جریان باد */
    showParticles: boolean
    /** حرکت ذرات — false: قاب ثابت (کلید «حرکت ذرات باد» در تنظیمات نما) */
    animateWind?: boolean
    particleCount?: number
    attempt?: number
  } = { multiLayer: false, showHeatmap: true, showArrows: true, showParticles: true },
): void {
  const attempt = opts.attempt ?? 0
  // ترجیح حرکت از تنظیمات نما — ساخت/بازسازی جریان آن را رعایت می‌کند
  flowPaused = opts.animateWind === false
  try {
    const ordered = [...fields].sort((a, b) => a.altitude_m - b.altitude_m)
    const active = ordered[0]
    if (active && opts.showHeatmap) {
      updateFieldImage(map, active)
    }
    if (map.getLayer(FIELD_LAYER)) {
      const heatmapVisible = Boolean(active) && opts.showHeatmap
      map.setLayoutProperty(FIELD_LAYER, 'visibility', heatmapVisible ? 'visible' : 'none')
    }
    // پیکان‌های جهت باد: در ۲بعدی روی میدان فعال (پایین‌ترین نمایان)؛ دادهٔ
    // شبکه فقط وقتی لایه دیده می‌شود ساخته می‌شود.
    if (map.getLayer(ARROW_LAYER)) {
      const arrowsVisible = Boolean(active) && opts.showArrows
      map.setLayoutProperty(ARROW_LAYER, 'visibility', arrowsVisible ? 'visible' : 'none')
      if (arrowsVisible && active) {
        updateArrowLayer(map, active)
      }
    }
    // ذرات جریان: در ۳بعدی همهٔ میدان‌های نمایان، در ۲بعدی فقط پایین‌ترین؛
    // رنگ/ضخامت per-feature است (ویژگی color/width هر Feature واحد دُم+نوک).
    if (map.getLayer(PARTICLE_LAYER)) {
      const particleFields = opts.multiLayer ? ordered : active ? [active] : []
      const particlesVisible = particleFields.length > 0 && opts.showParticles
      map.setLayoutProperty(PARTICLE_LAYER, 'visibility', particlesVisible ? 'visible' : 'none')
      if (particlesVisible) {
        startParticleFlow(map, particleFields, opts.particleCount)
      } else {
        stopParticleFlow()
      }
    } else if (attempt < 100 && fields.length > 0) {
      // استایل هنوز کاملاً لود نشده — کمی بعد دوباره تلاش می‌کنیم
      setTimeout(() => {
        applyWindFields(map, fields, { ...opts, attempt: attempt + 1 })
      }, 100)
    }
  } catch {
    if (attempt < 100) {
      setTimeout(() => {
        applyWindFields(map, fields, { ...opts, attempt: attempt + 1 })
      }, 100)
    }
  }
}
