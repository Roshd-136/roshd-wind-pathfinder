import { gridMeta, sampleWindAtPoint, type GridMeta } from './windField'
import type { WindField } from '../types/routing'

/**
 * «مقابله با باد» — درصدی از ۰ تا ۱۰۰ که در هر قطعهٔ مسیر می‌گوید پرنده
 * چند درصد مخالفِ جریانِ باد می‌جنگد:
 *
 * • ۰٪ — باد دقیقاً از پشت (همسو با جریان) → سفید
 * • ~۵۰٪ — باد جانبی → میانهٔ رمپ
 * • ۱۰۰٪ — باد دقیقاً روبه‌رو (روبه‌بادِ کامل) → سرخ
 *
 * ملاک فقط «راستا» است (طبق مشخصهٔ درخواستی)؛ اندازهٔ باد وارد درصدِ
 * رنگ نمی‌شود. قرارداد `direction_deg` همان بیرینگِ «باد از کجا» در
 * هواشناسی است — جریان به سمت ‎direction+۱۸۰ می‌وزد (همان قراردادِ
 * `speed_direction_to_uv` بک‌اند و لایهٔ پیکان‌های نقشه).
 */

/** درصد مقابله با باد از زاویهٔ قطعهٔ مسیر و بیرینگِ «باد از کجا». */
export function fightPercent(pathBearingRad: number, windFromDeg: number): number {
  const flowHeadingRad = ((windFromDeg + 180) * Math.PI) / 180
  const delta = pathBearingRad - flowHeadingRad
  return ((1 - Math.cos(delta)) / 2) * 100
}

/** بیرینگِ قطعه (رادیان از شمال، مثبت به شرق) از دو نقطهٔ جغرافیایی. */
export function segmentBearingRad(lat1: number, lon1: number, lat2: number, lon2: number): number {
  return bearingFromDeltaRad(lat2 - lat1, lon2 - lon1, (lat1 + lat2) / 2)
}

/** بیرینگ از تفاوت عرض/طول — طول جغرافیایی با عرضِ میانه مقیاس می‌گیرد. */
export function bearingFromDeltaRad(dLat: number, dLon: number, midLat: number): number {
  const midRad = (midLat * Math.PI) / 180
  // کفِ cos برای قطب‌های دور — در گستردهٔ پروژه (خراسان) بی‌اثر است
  const dE = dLon * Math.max(Math.cos(midRad), 0.1)
  return Math.atan2(dE, dLat)
}

/** نزدیک‌ترین لایهٔ باد به ارتفاع نقطه (متر MSL). */
export function nearestField(altM: number, fields: ReadonlyArray<WindField>): WindField | null {
  let best: WindField | null = null
  let bestGap = Number.POSITIVE_INFINITY
  for (const f of fields) {
    const gap = Math.abs(f.altitude_m - altM)
    if (gap < bestGap) {
      bestGap = gap
      best = f
    }
  }
  return best
}

/** کِشِ محورِ شبکه برای هر میدان — نمونه‌گیریِ نقطه‌ای بدون استخراجِ تکراری. */
const metaCache = new WeakMap<WindField, GridMeta>()
function metaOf(field: WindField): GridMeta {
  let m = metaCache.get(field)
  if (!m) {
    m = gridMeta(field)
    metaCache.set(field, m)
  }
  return m
}

/**
 * درصد مقابله با باد برای هر نقطهٔ مسیر. آخرین نقطه همان راستای قطعهٔ
 * پیش را می‌گیرد؛ قطعه‌های صفر-طول از نزدیک‌ترین قطعهٔ معتبر ورثه می‌شوند.
 * بدون میدانِ باد `null` می‌دهد تا نماها به رنگ ثابت قبلی بازگردند.
 */
export function computeFightProfile(
  pts: ReadonlyArray<{ lat: number; lon: number; alt?: number }>,
  fields: ReadonlyArray<WindField>,
): number[] | null {
  const n = pts.length
  if (n < 2 || fields.length === 0) return null
  const out = new Array<number>(n)
  for (let i = 0; i < n; i += 1) {
    // قطعهٔ نمایندهٔ راستا: ترجیحاً قطعهٔ جلوی نقطه (قطعهٔ قبل برای نقطهٔ
    // آخر)؛ قطعه‌های صفر-طول (نقطه‌های تکراری موتور) از نزدیک‌ترین قطعهٔ
    // معتبر ورثه می‌شوند — اول رو به بعد، نداشت رو به قبل.
    const last = Math.min(i, n - 2)
    let pick = -1
    for (let s = last; s < n - 1; s += 1) {
      if (Math.abs(pts[s + 1].lat - pts[s].lat) + Math.abs(pts[s + 1].lon - pts[s].lon) > 1e-9) {
        pick = s
        break
      }
    }
    if (pick < 0) {
      for (let s = last - 1; s >= 0; s -= 1) {
        if (Math.abs(pts[s + 1].lat - pts[s].lat) + Math.abs(pts[s + 1].lon - pts[s].lon) > 1e-9) {
          pick = s
          break
        }
      }
    }
    if (pick < 0) return null // کل مسیر یک نقطه است
    const bearing = bearingFromDeltaRad(
      pts[pick + 1].lat - pts[pick].lat,
      pts[pick + 1].lon - pts[pick].lon,
      (pts[pick].lat + pts[pick + 1].lat) / 2,
    )
    // لایهٔ نزدیک‌تر به ارتفاعِ واقعی نقطه — بیرونِ شبکه هم لبه‌چسبیده
    // نمونه می‌شود (مسیر داخل کادر است) و خطای بی‌لایه خالی نمی‌گذاریم
    const field = nearestField(pts[i].alt ?? fields[0].altitude_m, fields) ?? fields[0]
    const sample = sampleWindAtPoint(field, pts[i].lat, pts[i].lon, metaOf(field))
    out[i] = fightPercent(bearing, sample.direction_deg)
  }
  return out
}

/** سرخِ انتهای رمپ — ۱۰۰٪ روبه‌باد. */
export const FIGHT_RED: [number, number, number] = [220, 38, 38]

/** سفید → سرخ: ۰٪ سفیدِ خالص، ۱۰۰٪ سرخ (بیرونِ بازه کلیپ می‌شود). */
export function whiteToRed(pct: number): [number, number, number] {
  const t = Math.min(Math.max(pct, 0), 100) / 100
  return [
    Math.round(255 + (FIGHT_RED[0] - 255) * t),
    Math.round(255 + (FIGHT_RED[1] - 255) * t),
    Math.round(255 + (FIGHT_RED[2] - 255) * t),
  ]
}

/** مثل `whiteToRed` ولی خروجیِ شناور ۰..۱ — مصرفِ مستقیمِ GL (لولهٔ سه‌بعدی). */
export function whiteToRed01(pct: number): [number, number, number] {
  const [r, g, b] = whiteToRed(pct)
  return [r / 255, g / 255, b / 255]
}

/** CSS رنگ RGB تصادفی‌نشده. */
export function rgbCss(c: [number, number, number]): string {
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`
}

/**
 * کسرِ فاصله‌ایِ هر نقطه در کل مسیر (۰..۱) — دلت‌های استوانه‌ایِ
 * طول جغرافیایی با عرضِ میانه مقیاس می‌گیرند؛ برای رنگ‌آمیزی کافی است.
 */
export function cumulativeFractions(pts: ReadonlyArray<{ lat: number; lon: number }>): number[] {
  if (pts.length < 2) return pts.length === 1 ? [0] : []
  const cum = new Array<number>(pts.length)
  cum[0] = 0
  for (let i = 1; i < pts.length; i += 1) {
    const dLat = (pts[i].lat - pts[i - 1].lat) * 111.32
    const midRad = ((pts[i].lat + pts[i - 1].lat) / 2) * (Math.PI / 180)
    const dLon = (pts[i].lon - pts[i - 1].lon) * 111.32 * Math.cos(midRad)
    cum[i] = cum[i - 1] + Math.hypot(dLat, dLon)
  }
  const total = cum[cum.length - 1]
  if (total <= 1e-9) return cum.map(() => 0)
  return cum.map((c) => c / total)
}

/**
 * درصد مقابله در یک کسرِ فاصله — درون‌یابیِ خطی بین دو نقطهٔ پیرامون.
 * (لولهٔ سه‌بعدی و گرادیانِ نقشه هر دو در فضای کسرِ فاصله کار می‌کنند.)
 */
export function fightAtFraction(profile: number[], fracs: number[], f: number): number {
  if (profile.length === 0) return 0
  if (profile.length === 1) return profile[0]
  const t = Math.min(Math.max(f, 0), 1)
  let lo = 0
  let hi = fracs.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (fracs[mid] <= t) lo = mid
    else hi = mid
  }
  const span = fracs[hi] - fracs[lo]
  const local = span > 1e-9 ? Math.min(Math.max((t - fracs[lo]) / span, 0), 1) : 0
  return profile[lo] * (1 - local) + profile[hi] * local
}
