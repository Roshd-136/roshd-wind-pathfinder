import type { GeoJSONSource, ImageSource, Map as MapLibreMap } from 'maplibre-gl'
import type { WindField } from '../../../types/routing'
import { WIND_PARTICLE_CONFIG } from '../../../config/mapDisplay'
import {
  colorForFieldSpeed,
  fieldSpeedRange,
  gridMeta,
  sampleWindAtPoint,
} from '../../../utils/windField'

/**
 * رندر میدان باد روی MapLibre GL — **همهٔ لایه‌ها از ابتدا در استایل پایه
 * تعریف شده‌اند** (نقشهٔ رنگی، ذرات جریان باد) و این‌جا فقط دادهٔ آن‌ها
 * به‌روز می‌شود؛ افزودن لایه در زمان اجرا وقتی استایل در وضعیت نیمه‌لود
 * (صف DEM) است گاهی بی‌اثر می‌ماند و لایه هرگز رسم نمی‌شد — با درخت لایهٔ
 * ایستا این دسته باگ کلاً حذف شده است.
 *
 *  ۱) نقشهٔ حرارتی «نرم» — تصویر canvas با درون‌یابی دوخطی روی شبکه، رنگ
 *     نسبت به بازهٔ خود میدان (مثل صحنهٔ بصری‌سازی)،
 *  ۲) **ذرات جریان باد** (سبک windy) — ذرات ریز که پیوسته در امتداد بردار
 *     محلی باد حرکت می‌کنند و ردّ کوتاه می‌گذارند؛ رنگ نسبت به بازهٔ میدان.
 *     قرارداد هواشناسی: `direction_deg` از کجا می‌وزد؛ حرکت به سمت جریان
 *     (جهت + ۱۸۰).
 */

const FIELD_SOURCE = 'wind-field-raster'
const FIELD_LAYER = 'wind-field-layer'
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
      const alpha =
        80 +
        Math.round(70 * Math.min((v.speed_mps - range[0]) / Math.max(range[1] - range[0], 1e-6), 1))
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
// ذرات جریان باد — ذرات ریز که پیوسته در امتداد بردار محلی باد حرکت می‌کنند
// و ردّ کوتاه می‌گذارند. جایگزین پیکان‌های چشمک‌زن (بازخورد: انیمیشن
// همزمان/تصادفی هر دو بد بودند). حرکت پیوسته و روان است؛ ذره در پایان عمر
// یا خروج از میدان، بی‌سروصدا جای خود را با ذرهٔ تازه عوض می‌کند.
// ---------------------------------------------------------------------------

interface Particle {
  lon: number
  lat: number
  /** ردّ ذره — آخرین نقاط مسیر برای رسم خط کوتاه. */
  trail: [number, number][]
  ageMs: number
  lifetimeMs: number
  /** سرعت محلی آخرین نمونه — برای رنگ ردّ. */
  speedMps: number
}

interface FlowState {
  map: MapLibreMap
  field: WindField
  particles: Particle[]
  timer: ReturnType<typeof setInterval>
  lastTick: number
  prng: () => number
}

let flow: FlowState | null = null

/** PRNG قطعی (mulberry32) — همان seed همیشه همان جریان را می‌سازد. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
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

function respawnParticle(p: Particle, prng: () => number, field: WindField): void {
  const bbox = fieldBbox(field)
  p.lon = bbox.lonMin + prng() * (bbox.lonMax - bbox.lonMin)
  p.lat = bbox.latMin + prng() * (bbox.latMax - bbox.latMin)
  p.ageMs = 0
  p.lifetimeMs = WIND_PARTICLE_CONFIG.lifetimeMs * (0.5 + prng() * 0.5)
  p.trail = [[p.lon, p.lat]]
}

/** رنگ نسبی به‌صورت expression رنگی maplibre (بازهٔ خود میدان). */
function particleColorExpression(field: WindField): unknown[] {
  const [min, max] = fieldSpeedRange(field)
  const stops: unknown[] = ['interpolate', ['linear'], ['get', 'speed']]
  for (const stop of WIND_PARTICLE_RAMP) {
    const value = min + (max - min) * stop.t
    stops.push(Number(value.toFixed(2)), stop.color)
  }
  return stops
}

const WIND_PARTICLE_RAMP: ReadonlyArray<{ t: number; color: string }> = [
  { t: 0, color: 'rgb(37, 99, 235)' },
  { t: 0.25, color: 'rgb(34, 197, 94)' },
  { t: 0.5, color: 'rgb(234, 179, 8)' },
  { t: 0.75, color: 'rgb(249, 115, 22)' },
  { t: 1, color: 'rgb(239, 68, 68)' },
]

function particleGeoJson(particles: Particle[]) {
  return {
    type: 'FeatureCollection' as const,
    features: particles.map((p) => ({
      type: 'Feature' as const,
      properties: { speed: p.speedMps },
      geometry: { type: 'LineString' as const, coordinates: p.trail },
    })),
  }
}

function tickFlow(): void {
  if (!flow) return
  const { map, field, particles } = flow
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
    const bbox = fieldBbox(field)

    for (const p of particles) {
      const sample = sampleWindAtPoint(field, p.lat, p.lon)
      const heading = (sample.direction_deg + 180) * (Math.PI / 180)
      // حرکت نمایشی: هر m/s باد → چند صدم درجه در ثانیه (از کانفیگ)
      const dist = sample.speed_mps * WIND_PARTICLE_CONFIG.degPerSecPerMps * dtSec
      p.lon += Math.sin(heading) * dist
      p.lat += Math.cos(heading) * dist
      p.ageMs += dtMs
      p.speedMps = sample.speed_mps
      const outOfField =
        p.lon < bbox.lonMin ||
        p.lon > bbox.lonMax ||
        p.lat < bbox.latMin ||
        p.lat > bbox.latMax
      if (outOfField || p.ageMs > p.lifetimeMs) {
        respawnParticle(p, flow.prng, field)
      } else {
        p.trail.push([p.lon, p.lat])
        while (p.trail.length > WIND_PARTICLE_CONFIG.trailPoints) p.trail.shift()
      }
    }
    src.setData(particleGeoJson(particles))
  } catch {
    // نقشه حذف شده یا استایل عوض شده — جریان چیزی برای رسم ندارد
    stopParticleFlow()
  }
}

function startParticleFlow(map: MapLibreMap, field: WindField): void {
  if (flow && flow.map === map) {
    flow.field = field
    return
  }
  stopParticleFlow()
  const prng = mulberry32(WIND_PARTICLE_CONFIG.seed)
  const particles: Particle[] = []
  for (let i = 0; i < WIND_PARTICLE_CONFIG.count; i += 1) {
    const p: Particle = {
      lon: 0,
      lat: 0,
      trail: [],
      ageMs: 0,
      lifetimeMs: WIND_PARTICLE_CONFIG.lifetimeMs,
      speedMps: 0,
    }
    respawnParticle(p, prng, field)
    // عمر اولیهٔ تصادفی تا ذرات همزمان نپرند
    p.ageMs = prng() * p.lifetimeMs
    particles.push(p)
  }
  flow = {
    map,
    field,
    particles,
    timer: setInterval(tickFlow, WIND_PARTICLE_CONFIG.tickMs),
    lastTick: performance.now(),
    prng,
  }
  tickFlow()
}

export function stopParticleFlow(): void {
  if (flow) {
    clearInterval(flow.timer)
    flow = null
  }
}

/** نمایش/پنهان‌سازی گروهی باد (نقشهٔ رنگی + ذرات جریان) — کلیدهای تنظیمات. */
export function setWindOverlaysVisible(
  map: MapLibreMap,
  visible: { heatmap: boolean; arrows: boolean },
): void {
  if (map.getLayer(FIELD_LAYER)) {
    map.setLayoutProperty(FIELD_LAYER, 'visibility', visible.heatmap ? 'visible' : 'none')
  }
  if (map.getLayer(PARTICLE_LAYER)) {
    map.setLayoutProperty(PARTICLE_LAYER, 'visibility', visible.arrows ? 'visible' : 'none')
  }
  if (!visible.heatmap && !visible.arrows) stopParticleFlow()
}

/**
 * اعمال میدان‌های نمایان — نقشهٔ رنگی روی لایهٔ فعال و جریان ذرات روی
 * همان میدان؛ رنگ ذرات نسبت به بازهٔ میدان تنظیم می‌شود. هیچ لایه‌ای
 * add نمی‌شود — لایه‌ها از ابتدا در استایل‌اند و این‌جا فقط داده و دید
 * هرکدام تنظیم می‌شود؛ روی خطا با تایمر دوباره تلاش می‌شود.
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
    const ordered = [...fields].sort((a, b) => a.altitude_m - b.altitude_m)
    const active = ordered[0]
    if (active && opts.showHeatmap) {
      updateFieldImage(map, active)
    }
    if (map.getLayer(FIELD_LAYER)) {
      const heatmapVisible = Boolean(active) && opts.showHeatmap
      map.setLayoutProperty(FIELD_LAYER, 'visibility', heatmapVisible ? 'visible' : 'none')
    }
    // ذرات جریان: روی میدان فعال، رنگ نسبت به بازهٔ خود میدان
    if (map.getLayer(PARTICLE_LAYER)) {
      const particlesVisible = Boolean(active) && opts.showArrows
      map.setLayoutProperty(PARTICLE_LAYER, 'visibility', particlesVisible ? 'visible' : 'none')
      if (active) {
        map.setPaintProperty(PARTICLE_LAYER, 'line-color', particleColorExpression(active) as never)
      }
    }
    if (active && opts.showArrows) {
      startParticleFlow(map, active)
    } else {
      stopParticleFlow()
    }
    // یک رندر صریح — تضمین دیده‌شدن فوری داده‌های تازه
    map.triggerRepaint()
  } catch {
    if (attempt < 100) {
      setTimeout(() => applyWindFields(map, fields, { ...opts, attempt: attempt + 1 }), 150)
    }
  }
}
