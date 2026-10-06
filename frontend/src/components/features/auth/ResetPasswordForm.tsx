import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useSearchParams } from 'react-router-dom'
import { Button } from '../../ui/Button'
import { TextField } from '../../ui/TextField'
import { resetPasswordSchema, type ResetPasswordFormValues } from './authSchemas'
import { useConfirmPasswordReset } from '../../../hooks/useAuth'

interface ResetPasswordFormProps {
  onBack: () => void
}

/**
 * تعیین رمز جدید با توکن بازیابی (POST /auth/password-reset/confirm).
 * توکن از لینک ایمیل (`?token=...`) خوانده می‌شود؛ اگر نبود، کاربر
 * می‌تواند آن را دستی وارد کند.
 */
export function ResetPasswordForm({ onBack }: ResetPasswordFormProps) {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const confirmReset = useConfirmPasswordReset()
  const urlToken = params.get('token') ?? ''
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { token: urlToken, password: '', confirmPassword: '' },
  })

  const mismatch = errors.confirmPassword?.message === 'auth.passwordMismatch'

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((v) => confirmReset.mutate({ token: v.token, newPassword: v.password }))}
      noValidate
    >
      <h2 className="text-sm font-semibold text-text-primary">{t('auth.resetPassword')}</h2>
      <TextField
        label={t('auth.newPassword')}
        type="password"
        autoComplete="new-password"
        error={errors.password?.message}
        {...register('password')}
      />
      <TextField
        label={t('auth.confirmPassword')}
        type="password"
        autoComplete="new-password"
        error={mismatch ? t('auth.passwordMismatch') : errors.confirmPassword?.message}
        {...register('confirmPassword')}
      />
      {!urlToken && (
        <TextField
          label={t('auth.resetToken')}
          autoComplete="off"
          error={errors.token?.message}
          {...register('token')}
        />
      )}
      {confirmReset.isError && <p className="text-sm text-danger">{confirmReset.error.message}</p>}
      {confirmReset.isSuccess && <p className="text-sm text-success">{t('auth.resetSuccess')}</p>}
      <Button type="submit" className="w-full" disabled={confirmReset.isPending}>
        {confirmReset.isPending ? t('common.loading') : t('auth.resetPassword')}
      </Button>
      <button
        type="button"
        onClick={onBack}
        className="w-full text-xs text-text-secondary hover:underline"
      >
        {t('auth.backToLogin')}
      </button>
    </form>
  )
}
