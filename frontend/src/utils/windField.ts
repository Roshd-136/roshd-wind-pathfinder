import type { WindField, WindVector } from '../types/routing'

/**
 * توابع خالص میدان باد برای نمایش روی نقشه — رنگ‌آمیزی سرعت، ساخت آرایهٔ
 * پیکان‌ها و نمونه‌برداری نقطه‌ای. همهٔ ورودی‌ها از قرارداد `WindField` در
 * api/openapi.yaml می‌آیند (میدان منظم شبکه‌ای از `WindVector`).
 *
 * گام‌های شبکه (۰٫۰۵ درجه طول / ۰٫۰۳ عرض) همان خروجی
 * `scripts/export_web_wind_fixture.py` است؛ توابع با استخراج محورها از خود
 * داده کار می‌کنند تا به گام ثابت وابسته نباشند.
 */

/** توقف‌های رمپ رنگ سرعت باد — همان توکن‌های `--wind-speed-*` در tokens.css. */
export const WIND_SPEED_STOPS: ReadonlyArray<{ value: number; color: [number, number, number] }> = [
  { value: 0, color: [37, 99, 235] }, // آبی
  { value: 5, color: [34, 197, 94] }, // سبز
  { value: 10, color: [234, 179, 8] }, // زرد
  { value: 15, color: [249, 115, 22] }, // نارنجی
  { value: 20, color: [239, 68, 68] }, // قرمز
]

/** رنگ RGB سرعت باد با درون‌یابی خطی بین توقف‌های رمپ (خارج بازه کلیپ می‌شود). */
export function colorForSpeed(speedMps: number): [number, number, number] {
  const stops = WIND_SPEED_STOPS
  if (speedMps <= stops[0].value) return stops[0].color
  const last = stops[stops.length - 1]
  if (speedMps >= last.value) return last.color
  for (let i = 1; i < stops.length; i += 1) {
    if (speedMps <= stops[i].value) {
      const [a, b] = [stops[i - 1], stops[i]]
      const t = (speedMps - a.value) / (b.value - a.value)
      return [
        Math.round(a.color[0] + t * (b.color[0] - a.color[0])),
        Math.round(a.color[1] + t * (b.color[1] - a.color[1])),
        Math.round(a.color[2] + t * (b.color[2] - a.color[2])),
      ]
    }
  }
  return last.color
}

interface GridMeta {
  lats: number[]
  lons: number[]
  latStep: number
  lonStep: number
}

/** محورهای شبکهٔ میدان را از خود بردارها استخراج می‌کند (فرض: شبکهٔ منظم). */
export function gridMeta(field: WindField): GridMeta {
  const lats = [...new Set(field.vectors.map((v) => v.lat))].sort((a, b) => a - b)
  const lons = [...new Set(field.vectors.map((v) => v.lon))].sort((a, b) => a - b)
  return {
    lats,
    lons,
    latStep: lats.length > 1 ? lats[1] - lats[0] : 1,
    lonStep: lons.length > 1 ? lons[1] - lons[0] : 1,
  }
}

function lookupVector(field: WindField, meta: GridMeta, row: number, col: number): WindVector {
  // شبکهٔ منظم ردیف‌محور: ایندکس = row * n_lon + col
  return field.vectors[row * meta.lons.length + col]
}

/**
 * نمونهٔ باد در یک نقطه با درون‌یابی دوخطی روی شبکهٔ منظم (برای پاپ‌آپ
 * «لایه‌های باد در نقطه» وقتی بک‌اند در دسترس نیست).
 */
export function sampleWindAtPoint(
  field: WindField,
  lat: number,
  lon: number,
): { speed_mps: number; direction_deg: number } {
  const meta = gridMeta(field)
  const latMin = meta.lats[0]
  const lonMin = meta.lons[0]
  const fx = (lon - lonMin) / meta.lonStep
  const fy = (lat - latMin) / meta.latStep
  const col = Math.min(Math.max(fx, 0), meta.lons.length - 1)
  const row = Math.min(Math.max(fy, 0), meta.lats.length - 1)
  const c0 = Math.floor(col)
  const r0 = Math.floor(row)
  const c1 = Math.min(c0 + 1, meta.lons.length - 1)
  const r1 = Math.min(r0 + 1, meta.lats.length - 1)
  const tx = col - c0
  const ty = row - r0

  const v00 = lookupVector(field, meta, r0, c0)
  const v01 = lookupVector(field, meta, r0, c1)
  const v10 = lookupVector(field, meta, r1, c0)
  const v11 = lookupVector(field, meta, r1, c1)

  const lerp = (a: number, b: number, t: number) => a + t * (b - a)
  return {
    speed_mps: Number(
      lerp(lerp(v00.speed_mps, v01.speed_mps, tx), lerp(v10.speed_mps, v11.speed_mps, tx), ty).toFixed(2),
    ),
    direction_deg: Number(
      lerp(
        lerp(v00.direction_deg, v01.direction_deg, tx),
        lerp(v10.direction_deg, v11.direction_deg, tx),
        ty,
      ).toFixed(1),
    ),
  }
}

export interface ArrowFeature {
  lat: number
  lon: number
  speed_mps: number
  direction_deg: number
}

/**
 * زیرنمونه‌برداری پیکان‌ها از میدان (هر `stride` سلول یک پیکان) — همان الگوی
 * پیکان‌های صحنهٔ بصری‌سازی، برای لایهٔ symbol روی نقشه.
 */
export function arrowFeatures(field: WindField, stride = 3): ArrowFeature[] {
  const meta = gridMeta(field)
  const arrows: ArrowFeature[] = []
  for (let row = 0; row < meta.lats.length; row += stride) {
    for (let col = 0; col < meta.lons.length; col += stride) {
      const v = lookupVector(field, meta, row, col)
      arrows.push({
        lat: v.lat,
        lon: v.lon,
        speed_mps: v.speed_mps,
        direction_deg: v.direction_deg,
      })
    }
  }
  return arrows
}

/** سطل رنگی سرعت برای آیکون پیکان (همان رمپ راهنما). */
export function speedBucket(speedMps: number): '0' | '5' | '10' | '15' | '20' {
  if (speedMps < 5) return '0'
  if (speedMps < 10) return '5'
  if (speedMps < 15) return '10'
  if (speedMps < 20) return '15'
  return '20'
}
