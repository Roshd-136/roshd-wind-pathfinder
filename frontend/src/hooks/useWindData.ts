import { useQuery, useQueries } from '@tanstack/react-query'
import { WIND_LAYER_BANDS } from '../config/routing'
import { getWindField, listWindLayers } from '../services/api/windLayers'
import type { WindField } from '../types/routing'

/**
 * ارتفاع نمایندهٔ میدان باد سه لایهٔ رابط کاربری (سطحی ۰-۵۰ / میانی ۵۰-۲۰۰ /
 * بالا ۲۰۰-۵۰۰ متر AGL). از پیکربندی مشترک می‌آید — این ارتفاع‌ها پیش‌تر
 * در RoutingMapScreen هم به‌صورت هاردکد تکرار شده بود. فیلدهای پیش‌نمایش
 * dev با همین ارتفاع‌ها توسط `scripts/export_web_wind_fixture.py` تولید
 * شده‌اند.
 */
export const UI_LAYER_ALTITUDES = WIND_LAYER_BANDS.map((b) => b.fieldAltitude)

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
