import type { WindField, WindLayerMeta, WindPointSample } from '../../types/routing'
import { apiFetch } from './client'

/**
 * پیش‌نمایش dev بدون بک‌اند: اگر سرور FastAPI در دسترس نبود، در حالت dev از
 * فیکسچرهای واقعی `frontend/public/mock/` استفاده می‌شود — خروجی
 * `scripts/export_web_wind_fixture.py` از داده واقعی ایستگاه‌ها. در build
 * نهایی fallback وجود ندارد و بک‌اند الزامی است.
 */
async function devFallback<T>(path: string, mockFile: string): Promise<T> {
  if (!import.meta.env.DEV) throw new Error(`backend unreachable: ${path}`)
  const response = await fetch(mockFile)
  if (!response.ok) throw new Error(`mock fixture missing: ${mockFile}`)
  return (await response.json()) as T
}

/** GET /wind-layers */
export async function listWindLayers(): Promise<WindLayerMeta[]> {
  try {
    return await apiFetch<WindLayerMeta[]>('/wind-layers')
  } catch {
    return devFallback('/wind-layers', '/mock/wind-layers.json')
  }
}

/** GET /wind-layers/point-all — برای پاپ‌آپ "Wind Layers" روی نقشه. */
export async function getWindAtPointAllLayers(
  lat: number,
  lon: number,
): Promise<WindPointSample[]> {
  return apiFetch<WindPointSample[]>(`/wind-layers/point-all?lat=${lat}&lon=${lon}`)
}

/** GET /wind-layers/{altitudeM}/field — میدان برداری باد یک لایه. */
export async function getWindField(altitudeM: number): Promise<WindField> {
  try {
    return await apiFetch<WindField>(`/wind-layers/${altitudeM}/field`)
  } catch {
    return devFallback(`/wind-layers/${altitudeM}/field`, `/mock/wind-field-${altitudeM}.json`)
  }
}
