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

/** GET /v1/routes/{routeId} */
export function getRoute(routeId: string): Promise<RouteResult> {
  return apiFetch<RouteResult>(`/v1/routes/${routeId}`)
}

/** GET /v1/routes/jobs/{jobId}/compare-layers */
export function compareLayers(jobId: string): Promise<LayerComparison> {
  return apiFetch<LayerComparison>(`/v1/routes/jobs/${jobId}/compare-layers`)
}
