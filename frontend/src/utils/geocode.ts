/**
 * ژئوکدینگ معکوس آزاد (Nominatim/OpenStreetMap — بدون کلید).
 * خروجی: «استان، شهر، خیابان» (یا نزدیک‌ترین نام مکان) به زبان درخواستی.
 * پاسخ‌ها بر اساس مختصات گردشده کش می‌شوند؛ در نبود شبکه None برمی‌گردد
 * تا UI به نمایش مختصات برگردد.
 */

const cache = new Map<string, string>()

export async function reverseGeocode(
  lat: number,
  lon: number,
  language: 'fa' | 'en',
): Promise<string | null> {
  const key = `${lat.toFixed(3)},${lon.toFixed(3)},${language}`
  const cached = cache.get(key)
  if (cached !== undefined) return cached
  try {
    const url =
      `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lon}` +
      `&zoom=14&accept-language=${language}`
    const response = await fetch(url, { headers: { Accept: 'application/json' } })
    if (!response.ok) throw new Error(`nominatim ${response.status}`)
    const data = (await response.json()) as {
      address?: Record<string, string | undefined>
      display_name?: string
      name?: string
    }
    const a = data.address ?? {}
    // ترتیب: استان → شهر/شهرستان → خیابان/محله (اولین‌های موجود)
    const parts = [
      a.state ?? a.province,
      a.city ?? a.town ?? a.village ?? a.municipality ?? a.county,
      a.road ?? a.suburb ?? a.neighbourhood,
    ].filter((p): p is string => Boolean(p))
    const label = parts.length > 0 ? parts.join('، ') : (data.name ?? null)
    if (label) {
      cache.set(key, label)
      return label
    }
    return null
  } catch {
    return null
  }
}
