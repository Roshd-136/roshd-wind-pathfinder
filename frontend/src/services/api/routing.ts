import type { LayerComparison, RouteRequest, RouteResult } from '../../types/routing'
import { apiFetch } from './client'

/**
 * همهٔ مسیرها با پیشوند `/v1` — روترهای بک‌اند در `api/main.py` با
 * `prefix="/v1"` مانت می‌شوند (OpenAPI spec)؛ بدون پیشوند همهٔ درخواست‌ها
 * ۴۰۴ می‌گیرند و دکمهٔ محاسبه بی‌اثر می‌شود.
 */

/** POST /v1/routes — معادل مستقیم schema در api/openapi.yaml. */
export function calculateRoute(request: RouteRequest): Promise<RouteResult> {
  return apiFetch<RouteResult>('/v1/routes', { method: 'POST', body: request })
}

/** فاصلهٔ هر poll وضعیت کار (کامنت ۱۲ — درصد پیشرفت زنده). */
const JOB_POLL_INTERVAL_MS = 500

/** سقف انتظار برای کار ناهمگام — ۱۰ دقیقه؛ بعدش خطای مهلت. */
const JOB_TIMEOUT_MS = 10 * 60_000

interface RouteJobAccepted {
  job_id: string
  status: string
  estimated_duration_seconds?: number | null
}

interface RouteJobStatus {
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number | null
  result: RouteResult | null
  error: string | null
}

/**
 * محاسبهٔ مسیر با **درصد پیشرفت واقعی** (کامنت ۱۲ «کامنت‌های نرم‌افزار»):
 * درخواست ناهمگام (`async: true` → ۲۰۲ + job_id) و polling وضعیت تا
 * تکمیل؛ هر `progress` از سرور به `onProgress` میرسد تا دکمهٔ محاسبه
 * درصد زنده نشان دهد. اگر بک‌اند قدیمی پاسخ همگام داد (بدون ۲۰۲)، همان
 * نتیجه مستقیم برمی‌گردد تا با استقرارهای دیگر نشکند.
 */
export async function calculateRouteWithProgress(
  request: RouteRequest,
  onProgress?: (percent: number) => void,
): Promise<RouteResult> {
  const accepted = await apiFetch<RouteJobAccepted | RouteResult>('/v1/routes', {
    method: 'POST',
    body: { ...request, async: true },
  })
  if ('total_distance_km' in accepted) return accepted

  const jobId = accepted.job_id
  const deadline = Date.now() + JOB_TIMEOUT_MS
  while (Date.now() < deadline) {
    await new Promise((resolve) => setTimeout(resolve, JOB_POLL_INTERVAL_MS))
    const job = await apiFetch<RouteJobStatus>(`/v1/routes/jobs/${jobId}`)
    if (typeof job.progress === 'number') onProgress?.(job.progress)
    if (job.status === 'completed' && job.result) return job.result
    if (job.status === 'failed') {
      throw new Error(job.error ?? 'routing job failed')
    }
  }
  throw new Error('routing job timed out')
}

/** GET /v1/routes/{routeId} */
export function getRoute(routeId: string): Promise<RouteResult> {
  return apiFetch<RouteResult>(`/v1/routes/${routeId}`)
}

/** GET /v1/routes/jobs/{jobId}/compare-layers */
export function compareLayers(jobId: string): Promise<LayerComparison> {
  return apiFetch<LayerComparison>(`/v1/routes/jobs/${jobId}/compare-layers`)
}
