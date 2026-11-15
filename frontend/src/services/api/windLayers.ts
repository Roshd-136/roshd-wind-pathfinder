import type { WindField, WindLayerMeta } from '../../types/routing'
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

/** شکل واقعی پاسخ بک‌اند (api/routers/wind_layers.py :: WindLayersList). */
interface WindLayersListShape {
  layers: Array<{ altitude_m: number; timestamp: string }>
  available_altitudes_m: number[]
  latest_timestamp: string
  /** عمر مشاهدات به ساعت — بک‌اند در همان قابِ مهرِ CSV حساب میکند. */
  data_age_hours?: number | null
}

/** خروجی نرمالشده — هم از بک‌اند، هم از فیکسچر dev. */
export interface WindLayersSnapshot {
  /** ارتفاع میدان‌های موجود (متر MSL). */
  altitudes: number[]
  /** عمر مشاهدات به ساعت — مبنای «داده از چند ساعت پیش»؛ null = نامشخص. */
  dataAgeHours: number | null
  /** مهر زمانی مشاهدات (ISO) — برای نمایش دقیقِ ساعتِ ضبط. */
  latestTimestamp: string | null
}

/** GET /wind-layers — دو شکل پاسخ نرمال میشود: آبجکتِ بک‌اند
 * (`layers`/`available_altitudes_m`/`latest_timestamp`/`data_age_hours`)
 * و فیکسچر dev (آرایهٔ `WindLayerMeta` با `last_updated` آگاه از UTC).
 * پیشتر تایپ فرانت فقط با فیکسچر میخواند و پاسخ واقعی بک‌اند را غلط
 * تفسیر میکرد. */
export async function getWindLayersSnapshot(): Promise<WindLayersSnapshot> {
  try {
    const backend = await apiFetch<WindLayersListShape>('/v1/wind-layers')
    return {
      altitudes:
        backend.available_altitudes_m ??
        backend.layers.map((l) => l.altitude_m),
      dataAgeHours: backend.data_age_hours ?? null,
      latestTimestamp: backend.latest_timestamp ?? null,
    }
  } catch {
    const fixture = await devFallback<WindLayerMeta[]>(
      '/wind-layers',
      '/mock/wind-layers.json',
    )
    const stamps = fixture
      .map((l) => Date.parse(l.last_updated))
      .filter((t) => Number.isFinite(t))
    return {
      altitudes: fixture.map((l) => l.altitude_m),
      // فیکسچر مهر آگاه از UTC دارد — عمر اینجا معتبر است
      dataAgeHours:
        stamps.length > 0
          ? Math.max(0, (Date.now() - Math.max(...stamps)) / 3_600_000)
          : null,
      latestTimestamp:
        stamps.length > 0 ? new Date(Math.max(...stamps)).toISOString() : null,
    }
  }
}

/** GET /wind-layers/{altitudeM}/field — میدان برداری باد یک لایه. */
export async function getWindField(altitudeM: number): Promise<WindField> {
  try {
    return await apiFetch<WindField>(`/v1/wind-layers/${altitudeM}/field`)
  } catch {
    return devFallback(`/wind-layers/${altitudeM}/field`, `/mock/wind-field-${altitudeM}.json`)
  }
}
