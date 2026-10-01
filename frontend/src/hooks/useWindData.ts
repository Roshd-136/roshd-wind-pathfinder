import { useQuery } from '@tanstack/react-query'
import { getWindAtPointAllLayers, listWindLayers } from '../services/api/windLayers'
import type { Coordinate } from '../types/routing'

/** GET /wind-layers — لیست لایه‌های ارتفاعی موجود. */
export function useWindLayers() {
  return useQuery({
    queryKey: ['wind-layers'],
    queryFn: listWindLayers,
    staleTime: 5 * 60_000,
  })
}

/** GET /wind-layers/point-all — سرعت باد یک نقطه در همه لایه‌ها (Point Info). */
export function useWindAtPoint(point: Coordinate | null) {
  return useQuery({
    queryKey: ['wind-point', point?.lat, point?.lon],
    queryFn: () => getWindAtPointAllLayers(point!.lat, point!.lon),
    enabled: point !== null,
  })
}
