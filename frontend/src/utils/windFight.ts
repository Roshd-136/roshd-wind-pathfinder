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

/** طیفِ مقابله — روشن به تیره: سفیدِ خالص (۰٪، حرکتِ همسوباد) به سرخ‌های
 * تیره (۱۰۰٪ مقاومتِ کامل). بخشهای درگیرِ مقابله هرگز سفید نمی‌شوند؛ گاما
 * سهمهای کم را سریع از سپیدی بیرون میکشد (۳٪ = [231,113,104]، ۱۵٪ =
 * [175,42,44]) و انتهای تیره به مرواریدِ نزدیک‌سیاه میرسد. */
export const FIGHT_RED: [number, number, number] = [58, 0, 20]

/** گره‌های خمِ ورودیِ طیف — (٪ مقابله → جایگاه ۰..۱ روی طیف). زیرِ ~۵٪
 * نزدیک سفید میماند («حرکتِ راحت»)؛ حدود ۸٪ ورودِ رنگ شروع میشود و از
 * ~۱۵٪ تیرگیِ سرخِ عمیق میرسد — بخشهای مقابله سفید نمیمانند. */
const FIGHT_WARP: ReadonlyArray<readonly [number, number]> = [
  [0, 0],
  [2, 0.04],
  [8, 0.18],
  [20, 0.45],
  [40, 0.68],
  [70, 0.85],
  [100, 1],
]

function fightWarp(pct: number): number {
  const p = Math.min(Math.max(pct, 0), 100)
  let k = 0
  while (k < FIGHT_WARP.length - 2 && p > FIGHT_WARP[k + 1][0]) k += 1
  const [p0, w0] = FIGHT_WARP[k]
  const [p1, w1] = FIGHT_WARP[k + 1]
  return w0 + ((p - p0) / (p1 - p0)) * (w1 - w0)
}

const FIGHT_STOPS: ReadonlyArray<readonly [number, [number, number, number]]> = [
  [0, [255, 255, 255]],
  [10, [252, 205, 205]],
  [20, [245, 160, 158]],
  [30, [230, 110, 100]],
  [40, [210, 70, 60]],
  [50, [180, 45, 45]],
  [60, [150, 28, 40]],
  [70, [120, 15, 36]],
  [80, [95, 5, 32]],
  [90, [75, 0, 26]],
  [100, [58, 0, 20]],
]

/** رنگِ مقابله روی طیف — ٪۰↔۱۰۰ کلیپ میشود؛ درون‌یابیِ خطیِ بین توقفهای فام
 * روشن↔تیره: هرچه مقابله بیشتر، تیره‌تر. */
export function fightColor(pct: number): [number, number, number] {
  const u = fightWarp(pct) * 100
  let k = 0
  while (k < FIGHT_STOPS.length - 2 && u > FIGHT_STOPS[k + 1][0]) k += 1
  const [p0, c0] = FIGHT_STOPS[k]
  const [p1, c1] = FIGHT_STOPS[k + 1]
  const t = p1 === p0 ? 0 : Math.min(Math.max((u - p0) / (p1 - p0), 0), 1)
  return [
    Math.round(c0[0] + (c1[0] - c0[0]) * t),
    Math.round(c0[1] + (c1[1] - c0[1]) * t),
    Math.round(c0[2] + (c1[2] - c0[2]) * t),
  ]
}

/** مثل `fightColor` ولی خروجیِ شناور ۰..۱ — مصرفِ مستقیمِ GL (لولهٔ سه‌بعدی). */
export function fightColor01(pct: number): [number, number, number] {
  const c = fightColor(pct)
  return [c[0] / 255, c[1] / 255, c[2] / 255]
}

/**
 * گرادیانِ CSS طیفنما از تابعِ همان رمپ ساخته میشود تا رنگِ میله دقیقاً همان
 * رنگی باشد که خط/لوله خود را از آن میگیرند؛ توقفها هر ۲٪ — چون گاما در فضای
 * ورودی ناهموار است، فاصلههای کم خطای CSS-lerp را صفر میکند.
 */
export function fightLegendGradientCss(isRtl: boolean): string {
  const colors: string[] = []
  for (let p = 0; p <= 100; p += 2) colors.push(`${rgbCss(fightColor(p))} ${p}%`)
  return `linear-gradient(to ${isRtl ? 'left' : 'right'}, ${colors.join(', ')})`
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
