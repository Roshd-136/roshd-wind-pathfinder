import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { RouteHistoryList } from '../components/features/profile/RouteHistoryList'
import { useMe, useRouteHistory } from '../hooks/useProfile'

/** صفحه پروفایل — اطلاعات کاربری + تاریخچه مسیرها (چک‌لیست آیتم ۹). */
export function ProfilePage() {
  const { t } = useTranslation()
  const me = useMe()
  const history = useRouteHistory()

  return (
    <div className="space-y-4 p-6">
      <Card className="max-w-md">
        <h1 className="mb-3 text-lg font-semibold text-text-primary">{t('profile.title')}</h1>
        {me.isLoading && <p className="text-sm text-text-muted">{t('common.loading')}</p>}
        {me.isError && <p className="text-sm text-danger">{me.error.message}</p>}
        {me.data && (
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-text-secondary">{t('profile.name')}</dt>
              <dd className="text-text-primary">{me.data.name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-text-secondary">{t('profile.email')}</dt>
              <dd className="text-text-primary">{me.data.email}</dd>
            </div>
          </dl>
        )}
      </Card>

      <Card className="max-w-md">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">{t('profile.routeHistory')}</h2>
        {history.isLoading && <p className="text-sm text-text-muted">{t('common.loading')}</p>}
        {history.data && <RouteHistoryList routes={history.data.items} />}
      </Card>
    </div>
  )
}
