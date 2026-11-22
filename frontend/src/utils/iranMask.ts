/**
 * ماسک «داخل مرز ایران» برای نمایش میدان باد.
 *
 * دادهٔ باد روی یک شبکهٔ **مستطیلی** درون‌یابی می‌شود (برای درون‌یابی
 * دوخطی و ذرات به همسایه‌های کامل نیاز است)، ولی نمایش نباید باد را روی
 * عراق/افغانستان/دریا نشان دهد. این ماژول همان چندضلعی واقعی مرز را
 * آزمایش می‌کند تا پیکان‌ها، ذرات و تصویر حرارتی فقط داخل کشور بمانند.
 */

import { IRAN_BORDER_RINGS } from '../data/iranBorder'

/**
 * آزمون «نقطه داخل یک حلقه» با ray casting (even-odd).
 *
 * مختصات به ترتیب `[lon, lat]` است (قرارداد GeoJSON). حلقه بسته یا باز هر
 * دو پذیرفته می‌شود؛ سوراخ‌ها را باید با XOR چند حلقه پیاده کرد، نه با
 * چسباندن حلقه‌ها به هم (لبهٔ مصنوعی بین حلقه‌ها نتیجه را خراب می‌کند).
 */
export function pointInRing(
  lon: number,
  lat: number,
  ring: ReadonlyArray<readonly [number, number]>,
): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if (yi > lat !== yj > lat) {
      const xCross = ((xj - xi) * (lat - yi)) / (yj - yi) + xi
      if (lon < xCross) inside = !inside
    }
  }
  return inside
}

/**
 * آیا نقطه در ایران است؟ ( mainland + جزیره‌ها؛ سوراخ‌ها با even-odd)
 *
 * برای هر حلقه جداگانه آزمون می‌شود و نتیجه‌ها XOR می‌شوند: جزیره‌ها یک
 * بار «داخل» می‌دهند و سوراخ‌ها (دریاچه) دو بار → بیرون.
 */
export function isInsideIran(lat: number, lon: number): boolean {
  let inside = false
  for (const ring of IRAN_BORDER_RINGS) {
    if (pointInRing(lon, lat, ring)) inside = !inside
  }
  return inside
}

/**
 * ماسک ردیف‌محور شبکه — `mask[row * lons.length + col]`.
 *
 * یک‌بار برای هر میدان ساخته و بعد برای فیلتر پیکان‌ها/ذرات استفاده
 * می‌شود؛ آزمون چندضلعی برای هر ذره در هر تیک لازم نیست.
 */
export function insideGridMask(lats: number[], lons: number[]): boolean[] {
  const mask: boolean[] = []
  for (const lat of lats) {
    for (const lon of lons) {
      mask.push(isInsideIran(lat, lon))
    }
  }
  return mask
}
