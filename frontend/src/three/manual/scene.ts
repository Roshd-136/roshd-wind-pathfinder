/**
 * مدل دادهٔ صحنهٔ سه‌بعدی دست‌ساز — قرارداد همان `scene3d.py` (routing_scene):
 *
 *  ۱) مختصات صحنه بر حسب کیلومتر، مبدأ گوشهٔ جنوب‌غربی کادر (lonlat_to_km صحنه)؛
 *  ۲) زمین لندپالی از DEM پروژه (khorasan_terrain.csv) با رنگ‌های
 *     TERRAIN_COLORSCALE؛ اغراق عمودی VERTICAL_EXAGGERATION=8 فقط در ماتریس
 *     مدل اعمال می‌شود تا عدد ارتفاع‌ها دست‌نخورده بماند؛
 *  ۳) لایه‌های باد (۱۵۰۰/۲۲۰۰/۲۹۰۰/۳۶۰۰ متر) مثل FLIGHT_LEVELS_MSL با پالت
 *     لایهٔ صحنه (#74b9ff/#00cec9/#fdcb6e/#e84393) و پیکان‌های سرعت‌رنگ از
 *     رمپ --wind-speed-*؛
 *  ۴) مسیر اسپلاین کیوبیک روی طول کمان + لولهٔ ۶ضلعی (_smooth_route و
 *     _route_tube صحنه) — از path_3d واقعی API با ارتفاع متر MSL.
 *
 * هر تابع خالص و بدون GL است تا در تست هم قابل بررسی باشد.
 */

import { colorForSpeed, fieldSpeedRange } from '../../utils/windField'
import type { WindField } from '../../types/routing'

// ————— ثابت‌های صحنه — هم‌ارز scene3d.py —————

/** اغراق عمودی زمین — همان VERTICAL_EXAGGERATION صحنه. */
export const VERTICAL_EXAGGERATION = 8.0
/** شعاع لولهٔ مسیر (کیلومتر) — همان ROUTE_TUBE_RADIUS_KM صحنه. */
export const ROUTE_TUBE_RADIUS_KM = 0.7
/** تعداد ضلع مقطع لوله — همان ROUTE_TUBE_SIDES صحنه. */
export const ROUTE_TUBE_SIDES = 8
/** نمونه‌های اسپلاین مسیر — ۶۰۰ نمونهٔ صحنه. */
export const SPLINE_SAMPLES = 600
/** طول پیکان باد: کیلومتر به‌ازای هر m/s — هم‌مقیاس پیکان‌های نمای ۲بعدی. */
export const ARROW_KM_PER_MS = 0.3
/** سقف طول پیکان (کیلومتر) — ARROW_MAX_LENGTH_KM صحنه. */
export const ARROW_MAX_LENGTH_KM = 5.0
/** حداقل فاصلهٔ مجاز لایهٔ باد از زمین (متر) — MIN_TERRAIN_CLEARANCE_M. */
export const MIN_TERRAIN_CLEARANCE_M = 300
/** رنگ‌های لایه‌های ارتفاعی — همان _LAYER_PALETTE صحنهٔ مسیریابی. */
export const LAYER_PALETTE = ['#74b9ff', '#00cec9', '#fdcb6e', '#e84393'] as const

/** رمپ رنگ زمین — همان TERRAIN_COLORSCALE صحنه (پایین به بالا). */
const TERRAIN_STOPS: ReadonlyArray<{ at: number; color: [number, number, number] }> = [
  { at: 0.0, color: [47, 125, 79] },
  { at: 0.22, color: [124, 179, 66] },
  { at: 0.42, color: [201, 178, 94] },
  { at: 0.62, color: [169, 113, 75] },
  { at: 0.82, color: [155, 133, 119] },
  { at: 1.0, color: [242, 240, 236] },
]

// ————— تبدیل مختصات — همان lonlat_to_km صحنه —————

/** کیلومتر به‌ازای هر درجهٔ طول/عرض در میانهٔ کادر — تقریب equirectangular صحنه. */
function kmPerDegLon(latMid: number): number {
  return 111.32 * Math.cos((latMid * Math.PI) / 180)
}

export interface SceneFrame {
  /** مبدأ کادر (جنوب‌غربی) در درجه. */
  lon0: number
  lat0: number
  /** ضریب تبدیل طول جغرافیایی → کیلومتر. */
  kmPerLon: number
  /** ضریب تبدیل عرض جغرافیایی → کیلومتر. */
  kmPerLat: number
  /** ابعاد کادر (کیلومتر). */
  widthKm: number
  heightKm: number
}

/** ساخت قاب صحنه از کادر جغرافیایی. */
export function makeFrame(bbox: [number, number, number, number]): SceneFrame {
  const [lon0, lat0, lon1, lat1] = bbox
  const latMid = (lat0 + lat1) / 2
  const kmPerLon = kmPerDegLon(latMid)
  const kmPerLat = 111.32
  return {
    lon0,
    lat0,
    kmPerLon,
    kmPerLat,
    widthKm: (lon1 - lon0) * kmPerLon,
    heightKm: (lat1 - lat0) * kmPerLat,
  }
}

/** درجه → کیلومتر صحنه (x شرق، y شمال، مبدأ جنوب‌غربی). */
export function lonLatToKm(frame: SceneFrame, lon: number, lat: number): [number, number] {
  return [(lon - frame.lon0) * frame.kmPerLon, (lat - frame.lat0) * frame.kmPerLat]
}

/** کیلومتر صحنه → درجه (معکوس — برای کلیک نقشه). */
export function kmToLonLat(frame: SceneFrame, x: number, y: number): [number, number] {
  return [frame.lon0 + x / frame.kmPerLon, frame.lat0 + y / frame.kmPerLat]
}

// ————— زمین لندپالی — از CSV ارتفاع —————

export interface TerrainData {
  lats: number[]
  lons: number[]
  /** ارتفاع (متر) به صورت سطری از شمال به جنوب مثل CSV. */
  elev: Float32Array
  rows: number
  cols: number
}

/** خواندن CSV ارتفاع (lat,lon,elevation_m با خطوط # توضیح). */
export function parseTerrainCsv(text: string): TerrainData {
  const lines = text.split('\n')
  const cells: { lat: number; lon: number; elev: number }[] = []
  for (const line of lines) {
    if (!line || line.startsWith('#')) continue
    const parts = line.split(',')
    if (parts.length < 3) continue
    const lat = Number(parts[0])
    const lon = Number(parts[1])
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue
    cells.push({ lat, lon, elev: Number(parts[2]) })
  }
  if (cells.length === 0) throw new Error('terrain CSV خالی است')
  const lons = [...new Set(cells.map((c) => c.lon))].sort((a, b) => a - b)
  const lats = [...new Set(cells.map((c) => c.lat))].sort((a, b) => a - b)
  const rows = lats.length
  const cols = lons.length
  const elev = new Float32Array(rows * cols)
  // CSV از شمال (بزرگ‌ترین lat) شروع می‌شود — در گرید ردیف ۰ = جنوب
  for (const c of cells) {
    const row = lats.indexOf(c.lat)
    const col = lons.indexOf(c.lon)
    elev[row * cols + col] = c.elev
  }
  return { lats, lons, elev, rows, cols }
}

/** آیا (lat,lon) داخل کادر دادهٔ زمین است؟ بیرون کادر، سطحِ دیدِ کاربر
 * «صفحهٔ تراز» است (نه سطح لبهٔ کادر) و لنگرها باید روی همان بنشینند. */
export function isInTerrainFrame(t: TerrainData, lat: number, lon: number): boolean {
  return (
    lat >= t.lats[0] &&
    lat <= t.lats[t.rows - 1] &&
    lon >= t.lons[0] &&
    lon <= t.lons[t.cols - 1]
  )
}

/** ارتفاع زمین (متر) داخلِ کادر با درون‌یابی دوخطی.
 * ⚠️ بیرونِ کادر، مقدارِ **لبه‌چسبانده** برمی‌گرداند — این «فلاتِ خیالی»
 * یک زمانی پرتوِ برداشت را به برخوردِ خیالیِ دور می‌کشید و CPِ «جایی
 * دیگر» می‌ساخت. کدِ برداشت/لنگرِ جدید از `elevationInFrame` استفاده
 * کند؛ این تابع فقط برای نمونه‌هایی بماند که درون‌کادری بودنشان تضمین
 * شده (نوکِ مسیر، نقاطِ شبکهٔ باد). */
export function terrainElevationAt(t: TerrainData, lat: number, lon: number): number {
  const { lats, lons, elev, rows, cols } = t
  const latStep = lats[1] - lats[0]
  const lonStep = lons[1] - lons[0]
  const fx = (lon - lons[0]) / lonStep
  const fy = (lat - lats[0]) / latStep
  const x0 = Math.min(Math.max(Math.floor(fx), 0), cols - 2)
  const y0 = Math.min(Math.max(Math.floor(fy), 0), rows - 2)
  const tx = Math.min(Math.max(fx - x0, 0), 1)
  const ty = Math.min(Math.max(fy - y0, 0), 1)
  const e00 = elev[y0 * cols + x0]
  const e10 = elev[y0 * cols + x0 + 1]
  const e01 = elev[(y0 + 1) * cols + x0]
  const e11 = elev[(y0 + 1) * cols + x0 + 1]
  return e00 * (1 - tx) * (1 - ty) + e10 * tx * (1 - ty) + e01 * (1 - tx) * ty + e11 * tx * ty
}

/** ارتفاع زمین بدون دروغِ لبه‌چسبانده: بیرونِ کادرِ داده `null` می‌دهد
 * (کدِ لنگرِ نشانگر و برخوردِ پرتو از همین استفاده می‌کند). */
export function elevationInFrame(t: TerrainData, lat: number, lon: number): number | null {
  if (!isInTerrainFrame(t, lat, lon)) return null
  return terrainElevationAt(t, lat, lon)
}

/** رنگ رمپ زمین از نرمال‌شدهٔ ارتفاع. */
function terrainColor(tNorm: number): [number, number, number] {
  const stops = TERRAIN_STOPS
  if (tNorm <= stops[0].at) return stops[0].color
  const last = stops[stops.length - 1]
  if (tNorm >= last.at) return last.color
  for (let i = 1; i < stops.length; i += 1) {
    if (tNorm <= stops[i].at) {
      const a = stops[i - 1]
      const b = stops[i]
      const k = (tNorm - a.at) / (b.at - a.at)
      return [
        a.color[0] + k * (b.color[0] - a.color[0]),
        a.color[1] + k * (b.color[1] - a.color[1]),
        a.color[2] + k * (b.color[2] - a.color[2]),
      ]
    }
  }
  return last.color
}

export interface TerrainTiles {
  /** positions/colors مشترک بین همهٔ کاشی‌ها (یک بافر). */
  positions: Float32Array
  colors: Float32Array
  /** شاخص‌ها به ترتیب کاشی — هر کاشی بازهٔ پیوسته دارد. */
  indices: Uint32Array
  /** بازهٔ [start,end) شاخص + AABB هر کاشی — برای برش مخروط دید. */
  tiles: Array<{ start: number; end: number; bounds: Bounds6 }>
  /** بیشینهٔ ارتفاع صحنه (کیلومتر، اغراق‌شده) — برای دوربین. */
  maxZKm: number
}

/** AABB شش‌تایی: [minX,minY,minZ,maxX,maxY,maxZ]. */
export type Bounds6 = [number, number, number, number, number, number]

/**
 * مش زمین لندپالی به‌صورت کاشی‌شده — هر سلول DEM یک جفت مثلث؛ ارتفاع در
 * گوشه‌ها نمونه و رنگ هر رأس از ارتفاعش (رمپ TERRAIN_COLORSCALE با جیتر
 * لندپالی). کاشی‌بندی برای برش «فقط بخش جلوی دوربین» است.
 */
export function buildTerrainTiles(
  t: TerrainData,
  frame: SceneFrame,
  columns = 72,
  tileGrid = 8,
): TerrainTiles {
  const C = Math.max(columns, 8)
  const R = Math.max(Math.round((C * frame.heightKm) / frame.widthKm), 8)
  const elevMin = Math.min(...t.elev)
  const elevMax = Math.max(...t.elev)
  const elevSpan = Math.max(elevMax - elevMin, 1)
  const positions = new Float32Array((R + 1) * (C + 1) * 3)
  const colors = new Float32Array((R + 1) * (C + 1) * 3)
  let maxZKm = 0
  for (let r = 0; r <= R; r += 1) {
    for (let c = 0; c <= C; c += 1) {
      const i = (r * (C + 1) + c) * 3
      const fx = c / C
      const fy = r / R
      const lon = frame.lon0 + fx * (frame.widthKm / frame.kmPerLon)
      const lat = frame.lat0 + fy * (frame.heightKm / frame.kmPerLat)
      const elevM = terrainElevationAt(t, lat, lon)
      const zKm = (elevM / 1000) * VERTICAL_EXAGGERATION
      if (zKm > maxZKm) maxZKm = zKm
      positions[i] = fx * frame.widthKm
      positions[i + 1] = fy * frame.heightKm
      positions[i + 2] = zKm
      // جیتر لندپالی — همان حس «کم‌ضلعی» صحنه
      const jitter = ((Math.sin(c * 12.9898 + r * 78.233) * 43758.5453) % 1) * 0.05
      const [cr, cg, cb] = terrainColor(Math.min(Math.max((elevM - elevMin) / elevSpan + jitter, 0), 1))
      colors[i] = cr / 255
      colors[i + 1] = cg / 255
      colors[i + 2] = cb / 255
    }
  }
  // شاخص‌ها per کاشی — بازهٔ پیوسته برای draw بخشی از زمین
  const tr = Math.min(tileGrid, R)
  const tc = Math.min(tileGrid, C)
  const indexChunks: number[][] = Array.from({ length: tr * tc }, () => [])
  for (let r = 0; r < R; r += 1) {
    for (let c = 0; c < C; c += 1) {
      const a = r * (C + 1) + c
      const b = a + 1
      const d = a + (C + 1)
      const e = d + 1
      const tile = Math.min(Math.floor((r / R) * tr), tr - 1) * tc + Math.min(Math.floor((c / C) * tc), tc - 1)
      indexChunks[tile].push(a, d, b, b, d, e)
    }
  }
  const indices = new Uint32Array(R * C * 6)
  const tiles: TerrainTiles['tiles'] = []
  let ptr = 0
  for (const chunk of indexChunks) {
    const start = ptr
    for (const idx of chunk) indices[ptr++] = idx
    // AABB کاشی از رئوس همان کاشی
    let minX = Infinity, minY = Infinity, minZ = Infinity
    let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity
    const seen = new Set<number>()
    for (let k = start; k < ptr; k += 1) {
      const vi = indices[k]
      if (seen.has(vi)) continue
      seen.add(vi)
      const p = vi * 3
      if (positions[p] < minX) minX = positions[p]
      if (positions[p + 1] < minY) minY = positions[p + 1]
      if (positions[p + 2] < minZ) minZ = positions[p + 2]
      if (positions[p] > maxX) maxX = positions[p]
      if (positions[p + 1] > maxY) maxY = positions[p + 1]
      if (positions[p + 2] > maxZ) maxZ = positions[p + 2]
    }
    tiles.push({ start, end: ptr, bounds: [minX, minY, minZ, maxX, maxY, maxZ] })
  }
  return { positions, colors, indices, tiles, maxZKm }
}

// ————— اسپلاین کیوبیک روی طول کمان — همان _smooth_route صحنه —————

/**
 * اسپلاین کیوبیک با پارامترسازی طول کمان (Catmull-Rom) — همان رفتار
 * `_smooth_route`: مسیر نرم بدون قوس اضافی بین گره‌ها.
 */
export function smoothRoute(
  points: Array<{ x: number; y: number; z: number }>,
  samples = SPLINE_SAMPLES,
): Array<{ x: number; y: number; z: number }> {
  if (points.length < 2) return points.slice()
  const P = points
  const segLen: number[] = []
  let total = 0
  for (let i = 1; i < P.length; i += 1) {
    const d = Math.hypot(P[i].x - P[i - 1].x, P[i].y - P[i - 1].y, P[i].z - P[i - 1].z)
    segLen.push(Math.max(d, 1e-6))
    total += d
  }
  const out: Array<{ x: number; y: number; z: number }> = []
  const segs = P.length - 1
  for (let s = 0; s < samples; s += 1) {
    const target = (s / (samples - 1)) * total
    // جستجوی قطعهٔ متناظر
    let acc = 0
    let seg = 0
    let local = 0
    for (let i = 0; i < segs; i += 1) {
      if (acc + segLen[i] >= target) {
        seg = i
        local = (target - acc) / segLen[i]
        break
      }
      acc += segLen[i]
      seg = i
      local = 1
    }
    // نقاط Catmull-Rom با بازتاب لبه
    const i0 = Math.max(seg - 1, 0)
    const i1 = seg
    const i2 = Math.min(seg + 1, P.length - 1)
    const i3 = Math.min(seg + 2, P.length - 1)
    const t = local
    const t2 = t * t
    const t3 = t2 * t
    const lerp = (a: number, b: number, k: number) => a + (b - a) * k
    const cubic = (p0: number, p1: number, p2: number, p3: number) =>
      0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
    out.push({
      x: cubic(P[i0].x, P[i1].x, P[i2].x, P[i3].x),
      y: cubic(P[i0].y, P[i1].y, P[i2].y, P[i3].y),
      z: lerp(P[i1].z, P[i2].z, t),
    })
  }
  return out
}

// ————— لولهٔ مسیر — همان _route_tube صحنه (فریم موازی + رودریگز) —————

export interface TubeMesh {
  positions: Float32Array
  colors: Float32Array
  indices: Uint32Array
}

/** رنگ مسیر — همان رنگ لایهٔ مسیر نقشهٔ دوبعدی (سفید مایل به آبی). */
const ROUTE_COLOR: [number, number, number] = [0.97, 0.98, 1.0]

/**
 * لولهٔ ۶ضلعی حول اسپلاین — حلقه‌ها با فریم انتقال موازی (رودریگز)؛
 * همان الگوریتم `_route_tube` صحنه با مثلث‌های صریح (a,b,c)/(a,c,d).
 */
export function buildRouteTube(
  spline: Array<{ x: number; y: number; z: number }>,
  radiusKm = ROUTE_TUBE_RADIUS_KM,
  sides = ROUTE_TUBE_SIDES,
  color: [number, number, number] = ROUTE_COLOR,
): TubeMesh {
  const n = spline.length
  const ringCount = Math.min(Math.max(Math.floor(n / 4), 40), 160)
  const step = (n - 1) / (ringCount - 1)
  const positions = new Float32Array(ringCount * sides * 3)
  const colors = new Float32Array(ringCount * sides * 3)
  const indices = new Uint32Array((ringCount - 1) * sides * 6)
  // تانژانت در هر حلقه
  const tangentAt = (idx: number): [number, number, number] => {
    const i0 = Math.max(Math.min(idx, n - 2), 0)
    const dx = spline[i0 + 1].x - spline[i0].x
    const dy = spline[i0 + 1].y - spline[i0].y
    const dz = spline[i0 + 1].z - spline[i0].z
    const len = Math.hypot(dx, dy, dz) || 1
    return [dx / len, dy / len, dz / len]
  }
  // مرجع اولیهٔ نرمال — عمود بر تانژانت اول
  let refNormal: [number, number, number] = [0, 0, 1]
  const t0 = tangentAt(0)
  const dot0 = refNormal[0] * t0[0] + refNormal[1] * t0[1] + refNormal[2] * t0[2]
  if (Math.abs(dot0) > 0.9) refNormal = [1, 0, 0]
  // نرمال اول: ref minus projection
  const proj = refNormal[0] * t0[0] + refNormal[1] * t0[1] + refNormal[2] * t0[2]
  let normal: [number, number, number] = [
    refNormal[0] - proj * t0[0],
    refNormal[1] - proj * t0[1],
    refNormal[2] - proj * t0[2],
  ]
  let nlen = Math.hypot(normal[0], normal[1], normal[2]) || 1
  normal = [normal[0] / nlen, normal[1] / nlen, normal[2] / nlen]
  for (let ring = 0; ring < ringCount; ring += 1) {
    const idx = Math.round(ring * step)
    const p = spline[Math.min(idx, n - 1)]
    const tan = tangentAt(idx)
    // نرمال را با رودریگز حول تانژانت می‌چرخانیم (فریم موازی)
    const dot = normal[0] * tan[0] + normal[1] * tan[1] + normal[2] * tan[2]
    const cross: [number, number, number] = [
      normal[1] * tan[2] - normal[2] * tan[1],
      normal[2] * tan[0] - normal[0] * tan[2],
      normal[0] * tan[1] - normal[1] * tan[0],
    ]
    normal = [
      normal[0] - tan[0] * dot,
      normal[1] - tan[1] * dot,
      normal[2] - tan[2] * dot,
    ]
    nlen = Math.hypot(normal[0], normal[1], normal[2])
    if (nlen < 1e-8) {
      normal = cross
      nlen = Math.hypot(normal[0], normal[1], normal[2]) || 1
    }
    normal = [normal[0] / nlen, normal[1] / nlen, normal[2] / nlen]
    const binormal: [number, number, number] = [
      tan[1] * normal[2] - tan[2] * normal[1],
      tan[2] * normal[0] - tan[0] * normal[2],
      tan[0] * normal[1] - tan[1] * normal[0],
    ]
    for (let s = 0; s < sides; s += 1) {
      const ang = (s / sides) * Math.PI * 2
      const cx = Math.cos(ang) * radiusKm
      const cy = Math.sin(ang) * radiusKm
      const vi = (ring * sides + s) * 3
      positions[vi] = p.x + normal[0] * cx + binormal[0] * cy
      positions[vi + 1] = p.y + normal[1] * cx + binormal[1] * cy
      positions[vi + 2] = p.z + normal[2] * cx + binormal[2] * cy
      const shade = 0.82 + 0.18 * (Math.cos(ang) * 0.5 + 0.5)
      colors[vi] = color[0] * shade
      colors[vi + 1] = color[1] * shade
      colors[vi + 2] = color[2] * shade
    }
  }
  let ptr = 0
  for (let ring = 0; ring < ringCount - 1; ring += 1) {
    for (let s = 0; s < sides; s += 1) {
      const s2 = (s + 1) % sides
      const a = ring * sides + s
      const b = ring * sides + s2
      const c = (ring + 1) * sides + s
      const d = (ring + 1) * sides + s2
      indices[ptr++] = a; indices[ptr++] = c; indices[ptr++] = b
      indices[ptr++] = b; indices[ptr++] = c; indices[ptr++] = d
    }
  }
  return { positions, colors, indices }
}

// ————— پیکان‌های باد لایه‌ها — مانند لایهٔ باد صحنه —————

export interface ArrowMesh {
  positions: Float32Array
  colors: Float32Array
  count: number
}

/** رنگ hex → نرمال‌شدهٔ RGB. */
function hexToRgb(hex: string): [number, number, number] {
  const v = parseInt(hex.slice(1), 16)
  return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255]
}

/**
 * پیکان‌های باد یک لایه — خط مرکزی + دو بال؛ جهت جریان (direction+180،
 * قرارداد هواشناسی «از کجا می‌وزد»). طول = سرعت×ARROW_KM_PER_MS با سقف.
 * هر پیکان ۳ قطعه (دُم + ۲ بال) = ۶ رأس خطی (GL_LINES).
 */
export function buildWindArrows(
  field: WindField,
  frame: SceneFrame,
  terrain: TerrainData,
  layerIndex: number,
): ArrowMesh {
  void layerIndex
  const vectors = field.vectors
  // گام انتخاب پیکان‌ها — حدود ۱۲×۸ پیکان در صحنه (همان تراکم صحنهٔ مسیریابی)
  const lats = [...new Set(vectors.map((v) => v.lat))].sort((a, b) => a - b)
  const lons = [...new Set(vectors.map((v) => v.lon))].sort((a, b) => a - b)
  const targetRows = 9
  const rowStride = Math.max(1, Math.round(lats.length / targetRows))
  const colStride = Math.max(1, Math.round(lons.length / 14))
  // هر پیکان = ۹ رأس مثلثی: بدنهٔ چهارگوش (۲ مثلث) + سر مثلثی (۱ مثلث)
  const verts: number[] = []
  const speeds: number[] = []
  for (let r = 0; r < lats.length; r += rowStride) {
    for (let c = 0; c < lons.length; c += colStride) {
      const lat = lats[r]
      const lon = lons[c]
      const v = vectors.find((q) => q.lat === lat && q.lon === lon)
      if (!v) continue
      const [x, y] = lonLatToKm(frame, lon, lat)
      // ارتفاع لایه: متر MSL → کیلومتر اغراق‌شده، با حداقل فاصله از زمین
      const groundM = terrainElevationAt(terrain, lat, lon)
      const elevM = Math.max(field.altitude_m, groundM + MIN_TERRAIN_CLEARANCE_M)
      const zKm = (elevM / 1000) * VERTICAL_EXAGGERATION
      // طول پیکان — خطی با کف و سقف؛ حتی باد ملایم هم دیده شود
      const lenKm = Math.max(2.5, Math.min(v.speed_mps * ARROW_KM_PER_MS, ARROW_MAX_LENGTH_KM))
      // جهت جریان = direction + 180 (قرارداد هواشناسی «از کجا می‌وزد»)
      const flow = ((v.direction_deg + 180) * Math.PI) / 180
      const ux = Math.sin(flow)
      const uy = Math.cos(flow)
      // پهنای نوار — مستقل از دوربین، بر حسب کیلومتر صحنه
      const wKm = Math.max(0.8, lenKm * 0.16)
      const px = -uy * (wKm / 2)
      const py = ux * (wKm / 2)
      // نوک پیکان از مرکز تا جلو
      const cx = x - ux * (lenKm / 2)
      const cy = y - uy * (lenKm / 2)
      const ax = x + ux * (lenKm / 2)
      const ay = y + uy * (lenKm / 2)
      const headLen = lenKm * 0.38
      const headW = wKm * 1.5
      const bx = ax - ux * headLen
      const by = ay - uy * headLen
      // — بدنه: چهارگوش cx±p → bx±p —
      verts.push(cx + px, cy + py, zKm, cx - px, cy - py, zKm, bx - px, by - py, zKm)
      speeds.push(v.speed_mps, v.speed_mps, v.speed_mps)
      verts.push(cx + px, cy + py, zKm, bx - px, by - py, zKm, bx + px, by + py, zKm)
      speeds.push(v.speed_mps, v.speed_mps, v.speed_mps)
      // — سر: مثلث پهن —
      verts.push(ax, ay, zKm, bx - uy * headW, by + ux * headW, zKm, bx + uy * headW, by - ux * headW, zKm)
      speeds.push(v.speed_mps, v.speed_mps, v.speed_mps)
    }
  }
  const count = verts.length / 3
  const positions = new Float32Array(verts)
  const colors = new Float32Array(count * 3)
  // بازهٔ سرعت این میدان — همان نرمال‌سازی نمای ۲بعدی (colorForFieldSpeed)
  // تا رنگ پیکان‌ها در هر دو نما یکسان خوانده شود
  const [minS, maxS] = fieldSpeedRange(field)
  for (let i = 0; i < count; i += 1) {
    const t = Math.min(Math.max((speeds[i] - minS) / Math.max(maxS - minS, 1e-6), 0), 1)
    const [sr, sg, sb] = colorForSpeed(t * 20)
    colors[i * 3] = sr / 255
    colors[i * 3 + 1] = sg / 255
    colors[i * 3 + 2] = sb / 255
  }
  return { positions, colors, count }
}


// ————— وایرفریم اطراف لایه‌ها (کمکی بصری، اختیاری) —————

/** برچسب ارتفاع لایه برای HUD. */
export function layerLabel(altitudeM: number): string {
  return altitudeM >= 1000 ? `${(altitudeM / 1000).toFixed(1)} km` : `${altitudeM} m`
}

// ————— ستون نشانگر مبدأ/مقصد — پین عمودیِ صحنهٔ مسیریابی —————

// ————— نقطهٔ نشانگر (گوی) — مبدأ/مقصد/چک‌پوینت مثل «نقطه» دیده می‌شوند —————

export interface DotMesh {
  positions: Float32Array
  colors: Float32Array
  indices: Uint32Array
}

/** شعاع گوی نشانگر (کیلومتر صحنه). */
export const MARKER_DOT_RADIUS_KM = 0.9

/**
 * گوی (icosaedر کم‌وجه) روی زمین در مکان نقطه — جای ستون پین. «نقطه» یعنی
 * گوی کوچکِ هم‌رنگ نقش (مبدأ سبز، مقصد قرمز، چک‌پوینت کهربایی) که با زاویهٔ
 * دوربین گم نمی‌شود و کلیک روی آن قابل تشخیص است.
 */
export function buildMarkerDot(
  frame: SceneFrame,
  terrain: TerrainData,
  lat: number,
  lon: number,
  colorHex: string,
  radiusKm: number = MARKER_DOT_RADIUS_KM,
  altOverrideM?: number,
): DotMesh {
  const [cx, cy] = lonLatToKm(frame, lon, lat)
  const groundM = terrainElevationAt(terrain, lat, lon)
  // ارتفاع گوی: مقدار صریح (ارتفاع ذخیره‌شدهٔ نقطه) یا سطح زمین. بیرونِ
  // کادرِ زمین، terrainElevationAt به لبه می‌چسبد و گوی روی «ستونِ خیالی»
  // ارتفاعِ لبه می‌نشیند — با پارالاکس جایی دیگر از محل کلیک دیده می‌شد
  // («نقطهٔ انتخاب‌شده روی چیزی که کلیک کردم نیست»). سطحِ واقعیِ آنجا
  // برای کاربر همان صفحهٔ تراز است که کلیک رویش اتفاق افتاده.
  const altM = altOverrideM ?? (isInTerrainFrame(terrain, lat, lon) ? groundM : 0)
  const cz = (altM / 1000) * VERTICAL_EXAGGERATION + radiusKm * 0.8
  const [r, g, b] = hexToRgb(colorHex)

  // کرهٔ کاملِ UV (حلقه‌های عرضی × قطعات طولی) با سایه‌پردازیِ جهت‌دار —
  // نسخهٔ قبلی ۱۲ رأسِ ایکوزاهدرون با «اتصال به دو نزدیک‌ترین» بود که شکلِ
  // له‌شده و نامنظم می‌ساخت («نقاط کرهٔ درست نیستند»).
  const segments = 16
  const rings = 10
  const positions: number[] = []
  const colors: number[] = []
  const indices: number[] = []
  // نورِ ثابت از جنوبِ شرقیِ بالا — حجمِ کره از هر زاویه خوانده شود
  const lightLen = Math.hypot(0.45, -0.35, 0.82)
  const lx = 0.45 / lightLen
  const ly = -0.35 / lightLen
  const lz = 0.82 / lightLen
  for (let ring = 0; ring <= rings; ring += 1) {
    const phi = (Math.PI * ring) / rings
    const nz = Math.cos(phi)
    const rxy = Math.sin(phi)
    for (let s = 0; s <= segments; s += 1) {
      const th = (2 * Math.PI * s) / segments
      const nx = rxy * Math.cos(th)
      const ny = rxy * Math.sin(th)
      positions.push(cx + nx * radiusKm, cy + ny * radiusKm, cz + nz * radiusKm)
      const lambert = Math.max(0, nx * lx + ny * ly + nz * lz)
      const shade = 0.45 + 0.62 * lambert
      colors.push(Math.min(r * shade, 1), Math.min(g * shade, 1), Math.min(b * shade, 1))
    }
  }
  for (let ring = 0; ring < rings; ring += 1) {
    for (let s = 0; s < segments; s += 1) {
      const a = ring * (segments + 1) + s
      const bRow = a + segments + 1
      indices.push(a, bRow, a + 1, bRow, bRow + 1, a + 1)
    }
  }

  // ساقهٔ باریکِ متقاطع از سطحِ لنگر تا مرکز گوی — گویِ تنها در نمای دور
  // گم می‌شد؛ ساقه راهنمای دیداری «این نقطه کجا لنگر افتاده» می‌دهد.
  const stemW = radiusKm * 0.22
  const zBase = cz - radiusKm * 0.8
  const stemColor = [r * 0.85, g * 0.85, b * 0.85]
  const stemQuad = (ax: 'x' | 'y'): void => {
    const base = positions.length / 3
    if (ax === 'x') {
      positions.push(cx - stemW, cy, zBase, cx + stemW, cy, zBase, cx - stemW, cy, cz, cx + stemW, cy, cz)
    } else {
      positions.push(cx, cy - stemW, zBase, cx, cy + stemW, zBase, cx, cy - stemW, cz, cx, cy + stemW, cz)
    }
    for (let v = 0; v < 4; v += 1) colors.push(stemColor[0], stemColor[1], stemColor[2])
    // CULL_FACE در این رندرر فعال نیست — یک winding برای هر دو سو کافی است
    indices.push(base, base + 1, base + 2, base + 1, base + 3, base + 2)
  }
  stemQuad('x')
  stemQuad('y')
  return { positions: new Float32Array(positions), colors: new Float32Array(colors), indices: new Uint32Array(indices) }
}
