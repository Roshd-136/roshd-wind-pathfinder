import { useQuery, useQueries } from '@tanstack/react-query'
import { getWindAtPointAllLayers, getWindField, listWindLayers } from '../services/api/windLayers'
import type { Coordinate, WindField, WindPointSample } from '../types/routing'
import { sampleWindAtPoint } from '../utils/windField'

/**
 * ارتفاع «بالای زمین» سه لایهٔ رابط کاربری (میان‌باند چک‌باکس‌های
 * سطحی ۰-۵۰ / میانی ۵۰-۲۰۰ / بالا ۲۰۰-۵۰۰). فیلدهای پیش‌نمایش dev با همین
 * ارتفاع‌ها توسط `scripts/export_web_wind_fixture.py` تولید شده‌اند.
 */
export const UI_LAYER_ALTITUDES = [50, 200, 500] as const

/** GET /wind-layers — لیست لایه‌های ارتفاعی موجود. */
export function useWindLayers() {
  return useQuery({
    queryKey: ['wind-layers'],
    queryFn: listWindLayers,
    staleTime: 5 * 60_000,
  })
}

/**
 * میدان باد هر سه لایهٔ UI — روی نقشه، فیلتر چک‌باکس لایه تعیین می‌کند کدام
 * میدان نمایش داده شود؛ پاپ‌آپ نقطه هم در نبود بک‌اند از همین میدان‌ها
 * نمونه‌برداری می‌کند.
 */
export function useWindFields() {
  const queries = useQueries({
    queries: UI_LAYER_ALTITUDES.map((altitude) => ({
      queryKey: ['wind-field', altitude],
      queryFn: () => getWindField(altitude),
      staleTime: 10 * 60_000,
    })),
  })
  const fields = queries
    .map((q) => q.data)
    .filter((f): f is WindField => f !== undefined)
  const isLoading = queries.some((q) => q.isLoading)
  return { fields, isLoading }
}

/**
 * GET /wind-layers/point-all — سرعت باد یک نقطه در همه لایه‌ها (Point Info).
 * اگر بک‌اند در دسترس نباشد (فقط dev)، از میدان‌های بارگذاری‌شده با
 * درون‌یابی دوخطی نمونه‌برداری می‌شود — همان دادهٔ واقعی فیکسچرها.
 */
export function useWindAtPoint(point: Coordinate | null, fields: WindField[]) {
  return useQuery({
    queryKey: ['wind-point', point?.lat, point?.lon, fields.map((f) => f.altitude_m)],
    queryFn: async (): Promise<WindPointSample[]> => {
      if (point === null) return []
      try {
        return await getWindAtPointAllLayers(point.lat, point.lon)
      } catch (error) {
        if (!import.meta.env.DEV || fields.length === 0) throw error
        return fields.map((f) => ({
          altitude_m: f.altitude_m,
          ...sampleWindAtPoint(f, point.lat, point.lon),
        }))
      }
    },
    enabled: point !== null,
  })
}
