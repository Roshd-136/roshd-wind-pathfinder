import { useMutation } from '@tanstack/react-query'
import { calculateRoute } from '../services/api/routing'
import type { RouteRequest, RouteResult } from '../types/routing'

/**
 * محاسبه مسیر بهینه — پوششی نازک روی `POST /routes` با TanStack Query
 * برای مدیریت وضعیت loading/error/retry به‌صورت خودکار.
 */
export function usePathfinding() {
  return useMutation<RouteResult, Error, RouteRequest>({
    mutationFn: calculateRoute,
  })
}
