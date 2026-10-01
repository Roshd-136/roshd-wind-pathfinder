import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/ui/Card'
import { getRoute } from '../services/api/routing'

/** صفحه نتیجه مسیر — جزئیات کامل یک مسیر محاسبه/ذخیره‌شده (GET /routes/{routeId}). */
export function ResultsPage() {
  const { routeId } = useParams<{ routeId: string }>()
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['routes', routeId],
    queryFn: () => getRoute(routeId!),
    enabled: Boolean(routeId),
  })

  if (isLoading) return <p className="p-6 text-text-muted">در حال بارگذاری…</p>
  if (isError) return <p className="p-6 text-danger">{error.message}</p>
  if (!data) return null

  return (
    <div className="p-6">
      <Card className="max-w-md">
        <h1 className="mb-4 text-lg font-semibold text-text-primary">نتیجه مسیر</h1>
        <dl className="space-y-2 text-sm">
          <Row label="لایه ارتفاعی" value={`${data.layer_altitude_m} m`} />
          <Row label="الگوریتم" value={data.algorithm} />
          <Row label="معیار" value={data.criterion} />
          <Row label="مسافت" value={`${data.total_distance_km.toFixed(1)} km`} />
          <Row label="زمان تخمینی" value={`${data.estimated_time_hours.toFixed(2)} h`} />
          <Row label="تعداد نقاط مسیر" value={String(data.path.length)} />
        </dl>
      </Card>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-text-secondary">{label}</dt>
      <dd className="text-text-primary">{value}</dd>
    </div>
  )
}
