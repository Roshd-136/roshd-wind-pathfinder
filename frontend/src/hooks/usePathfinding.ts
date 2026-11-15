import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { calculateRouteWithProgress } from '../services/api/routing'
import type { RouteRequest, RouteResult } from '../types/routing'

/**
 * محاسبه مسیر بهینه — پوششی روی `POST /v1/routes` با TanStack Query.
 *
 * کامنت ۱۲ «کامنت‌های نرم‌افزار»: پیشتر فقط یک اسپینر بدون درصد بود چون
 * درخواست همگامِ کور بود؛ حالا مسیر ناهمگام با polling انجام میشود و
 * `progress` (۰ تا ۱۰۰) زنده از سرور میآید — `null` یعنی بیرون از محاسبه.
 */
export function usePathfinding() {
  const [progress, setProgress] = useState<number | null>(null)
  const mutation = useMutation<RouteResult, Error, RouteRequest>({
    mutationFn: (request) => calculateRouteWithProgress(request, setProgress),
    onSettled: () => setProgress(null),
  })
  return { ...mutation, progress }
}
