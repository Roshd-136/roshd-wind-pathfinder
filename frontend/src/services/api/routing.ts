import type { LayerComparison, RouteRequest, RouteResult } from '../../types/routing'
import { apiFetch } from './client'

/** POST /routes — معادل مستقیم schema در api/openapi.yaml. */
export function calculateRoute(request: RouteRequest): Promise<RouteResult> {
  return apiFetch<RouteResult>('/routes', { method: 'POST', body: request })
}

/** GET /routes/{routeId} */
export function getRoute(routeId: string): Promise<RouteResult> {
  return apiFetch<RouteResult>(`/routes/${routeId}`)
}

/** GET /routes/jobs/{jobId}/compare-layers */
export function compareLayers(jobId: string): Promise<LayerComparison> {
  return apiFetch<LayerComparison>(`/routes/jobs/${jobId}/compare-layers`)
}
