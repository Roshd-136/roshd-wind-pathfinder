import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { Card } from '../components/ui/Card'
import { getRoute } from '../services/api/routing'
import { formatAltitudeM, formatDistanceKm, formatDurationHours } from '../utils/format'
import { useFormatLang } from '../hooks/useFormatLang'

/** صفحه نتیجه مسیر — جزئیات کامل یک مسیر محاسبه/ذخیره‌شده (GET /routes/{routeId}). */
export function ResultsPage() {
  const { routeId } = useParams<{ routeId: string }>()
  const { t } = useTranslation()
  const lang = useFormatLang()
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['routes', routeId],
    queryFn: () => getRoute(routeId!),
    enabled: Boolean(routeId),
  })

  if (isLoading) return <p className="p-6 text-text-muted">{t('common.loading')}</p>
  if (isError) return <p className="p-6 text-danger">{error.message}</p>
  if (!data) return null

  return (
    <div className="p-6">
      <Card className="max-w-md">
        <h1 className="mb-4 text-lg font-semibold text-text-primary">{t('results.title')}</h1>
        <dl className="space-y-2 text-sm">
          <Row label={t('results.layerAltitude')} value={formatAltitudeM(data.layer_altitude_m, lang)} />
          <Row label={t('results.algorithm')} value={data.algorithm} />
          <Row label={t('results.criterion')} value={data.criterion} />
          <Row label={t('results.distance')} value={formatDistanceKm(data.total_distance_km, lang)} />
          <Row label={t('results.eta')} value={formatDurationHours(data.estimated_time_hours, lang)} />
          <Row label={t('results.pathPoints')} value={String(data.path.length)} />
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
