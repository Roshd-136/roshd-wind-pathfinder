import type { RouteResult } from '../../../types/routing'
import { Card } from '../../ui/Card'

interface RouteHistoryListProps {
  routes: RouteResult[]
}

/** تاریخچه مسیرهای محاسبه/ذخیره‌شده کاربر — GET /me/routes. */
export function RouteHistoryList({ routes }: RouteHistoryListProps) {
  if (routes.length === 0) {
    return <p className="text-sm text-text-muted">هنوز مسیری ذخیره نشده است.</p>
  }

  return (
    <ul className="space-y-2">
      {routes.map((route) => (
        <Card key={route.route_id} className="flex items-center justify-between text-sm">
          <span className="text-text-secondary">
            {route.total_distance_km.toFixed(1)} km · {route.layer_altitude_m}m ·{' '}
            {route.algorithm}
          </span>
          <span className="text-text-muted">{route.estimated_time_hours.toFixed(1)} h</span>
        </Card>
      ))}
    </ul>
  )
}
