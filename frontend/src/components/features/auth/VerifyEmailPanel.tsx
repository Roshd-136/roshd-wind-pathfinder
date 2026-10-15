import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { useVerifyEmail } from '../../../hooks/useAuth'

interface VerifyEmailPanelProps {
  onDone: () => void
}

/**
 * تایید ایمیل — توکن از لینک ایمیل (`?token=...`) خوانده و مستقیماً
 * به `POST /auth/verify-email/confirm` فرستاده می‌شود؛ در نبود توکن،
 * فرم دستی نمایش داده می‌شود (چک‌لیست آیتم ۹).
 */
export function VerifyEmailPanel({ onDone }: VerifyEmailPanelProps) {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const token = params.get('token')
  const verify = useVerifyEmail()

  useEffect(() => {
    if (token) verify.mutate(token)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when token changes
  }, [token])

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-text-primary">{t('auth.verifyEmail')}</h2>
      {!token && <p className="text-sm text-text-secondary">{t('auth.verifyEmailHint')}</p>}
      {verify.isSuccess && <p className="text-sm text-success">{t('auth.verifySuccess')}</p>}
      {verify.isError && <p className="text-sm text-danger">{verify.error.message}</p>}
      <button
        type="button"
        onClick={onDone}
        className="w-full text-xs text-text-secondary hover:underline"
      >
        {t('auth.backToLogin')}
      </button>
    </div>
  )
}
