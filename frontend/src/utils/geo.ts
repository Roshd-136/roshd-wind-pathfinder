/**
 * محاسبات زمین‌مرجع مشترک — فعلاً فقط فاصلهٔ دایرهٔ عظیمه.
 */

import type { Coordinate } from '../types/routing'

/** شعاع متوسط زمین (IUGG) — مبنای خط مستقیم هوایی. */
const EARTH_MEAN_RADIUS_KM = 6371.0088

/**
 * فاصلهٔ دایرهٔ عظیمه بین دو مختصات، به کیلومتر (فرمول هaversine).
 *
 * «خط مستقیم هوایی» مبدا–مقصد (کامنت ۹ «کامنت‌های نرم‌افزار») — کاربر باید
 * بتواند مسیر پیشنهادی مبتنی بر باد را با کوتاه‌ترین حالتِ ممکن مقایسه کند
 * و بداند مسیر چند درصد از خط مستقیم دور شده است.
 */
export function greatCircleDistanceKm(a: Coordinate, b: Coordinate): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLon = toRad(b.lon - a.lon)
  const lat1 = toRad(a.lat)
  const lat2 = toRad(b.lat)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_MEAN_RADIUS_KM * Math.asin(Math.sqrt(h))
}
