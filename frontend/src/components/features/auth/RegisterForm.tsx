import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Button } from '../../ui/Button'
import { TextField } from '../../ui/TextField'
import { registerSchema, type RegisterFormValues } from './authSchemas'
import { useRegister } from '../../../hooks/useAuth'

export function RegisterForm() {
  const { t } = useTranslation()
  const registerMutation = useRegister()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) })

  return (
    <form
      className="space-y-4"
      onSubmit={handleSubmit((values) => registerMutation.mutate(values))}
      noValidate
    >
      <TextField label="نام" autoComplete="name" error={errors.name?.message} {...register('name')} />
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
        autoComplete="new-password"
        error={errors.password?.message}
        {...register('password')}
      />
      {registerMutation.isError && (
        <p className="text-sm text-danger">{registerMutation.error.message}</p>
      )}
      {registerMutation.isSuccess && (
        <p className="text-sm text-success">ثبت‌نام موفق — ایمیل تایید ارسال شد.</p>
      )}
      <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
        {registerMutation.isPending ? t('common.loading') : t('auth.register')}
      </Button>
    </form>
  )
}
