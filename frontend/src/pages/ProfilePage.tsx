import { Card } from '../components/ui/Card'
import { RouteHistoryList } from '../components/features/profile/RouteHistoryList'
import { useMe, useRouteHistory } from '../hooks/useProfile'

/** صفحه پروفایل — اطلاعات کاربری + تاریخچه مسیرها (چک‌لیست آیتم ۹). */
export function ProfilePage() {
  const me = useMe()
  const history = useRouteHistory()

  return (
    <div className="space-y-4 p-6">
      <Card className="max-w-md">
        <h1 className="mb-3 text-lg font-semibold text-text-primary">پروفایل</h1>
        {me.isLoading && <p className="text-sm text-text-muted">در حال بارگذاری…</p>}
        {me.isError && <p className="text-sm text-danger">{me.error.message}</p>}
        {me.data && (
          <dl className="space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-text-secondary">نام</dt>
              <dd className="text-text-primary">{me.data.name}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-text-secondary">ایمیل</dt>
              <dd className="text-text-primary">{me.data.email}</dd>
            </div>
          </dl>
        )}
      </Card>

      <Card className="max-w-md">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">تاریخچه مسیرها</h2>
        {history.isLoading && <p className="text-sm text-text-muted">در حال بارگذاری…</p>}
        {history.data && <RouteHistoryList routes={history.data.items} />}
      </Card>
    </div>
  )
}
