import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../ui/Button'
import { TextField } from '../../ui/TextField'
import { loginSchema, type LoginFormValues } from './authSchemas'
import { useLogin } from '../../../hooks/useAuth'

interface LoginFormProps {
  onForgotPassword: () => void
  onVerifyEmail: () => void
}

export function LoginForm({ onForgotPassword, onVerifyEmail }: LoginFormProps) {
  const { t } = useTranslation()
  const login = useLogin()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => login.mutate(values))}
      noValidate
    >
      <TextField
        label={t('auth.email')}
        type="email"
        autoComplete="email"
        error={errors.email?.message}
        {...register('email')}
      />
      <TextField
        label={t('auth.password')}
        type="password"
        autoComplete="current-password"
        error={errors.password?.message}
        {...register('password')}
      />
      {login.isError && <p className="text-sm text-danger">{login.error.message}</p>}
      <div className="flex justify-between">
        <button
          type="button"
          onClick={onForgotPassword}
          className="text-xs text-accent hover:underline"
        >
          {t('auth.forgotPassword')}
        </button>
        <button
          type="button"
          onClick={onVerifyEmail}
          className="text-xs text-accent hover:underline"
        >
          {t('auth.verifyEmail')}
        </button>
      </div>
      <Button type="submit" className="w-full" disabled={login.isPending}>
        {login.isPending ? t('common.loading') : t('auth.login')}
      </Button>
    </form>
  )
}
