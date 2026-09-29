import type { WindLayerMeta, WindPointSample } from '../../types/routing'
import { apiFetch } from './client'

/** GET /wind-layers */
export function listWindLayers(): Promise<WindLayerMeta[]> {
  return apiFetch<WindLayerMeta[]>('/wind-layers')
}

/** GET /wind-layers/point-all — برای پاپ‌آپ "Wind Layers" روی نقشه. */
export function getWindAtPointAllLayers(lat: number, lon: number): Promise<WindPointSample[]> {
  return apiFetch<WindPointSample[]>(`/wind-layers/point-all?lat=${lat}&lon=${lon}`)
}
