import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../ui/Button'
import { TextField } from '../../ui/TextField'
import { forgotPasswordSchema, type ForgotPasswordFormValues } from './authSchemas'
import { useRequestPasswordReset } from '../../../hooks/useAuth'

interface ForgotPasswordFormProps {
  onBack: () => void
  onHaveToken: () => void
}

export function ForgotPasswordForm({ onBack, onHaveToken }: ForgotPasswordFormProps) {
  const { t } = useTranslation()
  const requestReset = useRequestPasswordReset()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({ resolver: zodResolver(forgotPasswordSchema) })

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => requestReset.mutate(values.email))}
      noValidate
    >
      <TextField
        label={t('auth.email')}
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register('email')}
      />
      {requestReset.isSuccess && (
        <p className="text-sm text-success">{t('auth.resetEmailSent')}</p>
      )}
      <Button type="submit" className="w-full" disabled={requestReset.isPending}>
        {requestReset.isPending ? t('common.loading') : t('auth.sendResetLink')}
      </Button>
      <div className="flex justify-between">
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-text-secondary hover:underline"
        >
          {t('auth.backToLogin')}
        </button>
        <button
          type="button"
          onClick={onHaveToken}
          className="text-xs text-accent hover:underline"
        >
          {t('auth.haveToken')}
        </button>
      </div>
    </form>
  )
}
