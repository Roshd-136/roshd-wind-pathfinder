import { useQuery } from '@tanstack/react-query'
import type { Coordinate } from '../../../types/routing'
import { reverseGeocode } from '../../../utils/geocode'
import { useSettingsStore } from '../../../store/useSettingsStore'

/**
 * نام مکان یک نقطه (استان/شهر/خیابان) — ژئوکدینگ معکوس آزاد OSM.
 *
 * پیش‌تر فقط در ویزارد استفاده می‌شد؛ حالا پنل مسیر هم برای «مبدا و مقصد
 * همیشه‌دید» (کامنت ۹ «کامنت‌های نرم‌افزار») همان برچسب را نشان می‌دهد —
 * یک منبع واحد برای نام مکان تا دو جا دو رفتار نگیرند.
 */
export function PlaceLabel({ point }: { point: Coordinate }) {
  const language = useSettingsStore((s) => s.language)
  const { data } = useQuery({
    queryKey: ['geocode', point.lat.toFixed(3), point.lon.toFixed(3), language],
    queryFn: () => reverseGeocode(point.lat, point.lon, language),
    staleTime: Infinity,
  })
  const fallback = `${point.lat.toFixed(3)}, ${point.lon.toFixed(3)}`
  return <>{data ?? fallback}</>
}
