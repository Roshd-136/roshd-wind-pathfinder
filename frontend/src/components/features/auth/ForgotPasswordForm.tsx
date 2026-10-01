import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../ui/Button'
import { TextField } from '../../ui/TextField'
import { forgotPasswordSchema, type ForgotPasswordFormValues } from './authSchemas'
import { useRequestPasswordReset } from '../../../hooks/useAuth'

interface ForgotPasswordFormProps {
  onBack: () => void
}

export function ForgotPasswordForm({ onBack }: ForgotPasswordFormProps) {
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
        <p className="text-sm text-success">در صورت وجود این ایمیل، لینک بازیابی ارسال شد.</p>
      )}
      <Button type="submit" className="w-full" disabled={requestReset.isPending}>
        {requestReset.isPending ? t('common.loading') : 'ارسال لینک بازیابی'}
      </Button>
      <button type="button" onClick={onBack} className="w-full text-xs text-text-secondary hover:underline">
        بازگشت به ورود
      </button>
    </form>
  )
}
