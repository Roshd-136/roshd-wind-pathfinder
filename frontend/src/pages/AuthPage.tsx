import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { LoginForm } from '../components/features/auth/LoginForm'
import { RegisterForm } from '../components/features/auth/RegisterForm'
import { ForgotPasswordForm } from '../components/features/auth/ForgotPasswordForm'
import { ResetPasswordForm } from '../components/features/auth/ResetPasswordForm'
import { VerifyEmailPanel } from '../components/features/auth/VerifyEmailPanel'

type Tab = 'login' | 'register' | 'forgot' | 'reset' | 'verify'

/**
 * صفحه احراز هویت — ورود، ثبت‌نام، بازیابی رمز (درخواست + تعیین رمز جدید)
 * و تایید ایمیل (چک‌لیست آیتم ۹). توکن بازیابی/تایید از لینک ایمیل
 * (`?token=...`) خوانده می‌شود.
 */
export function AuthPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('login')

  return (
    <div className="flex h-full items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-4 text-center text-lg font-semibold text-text-primary">
          {t('app.name')}
        </h1>

        {(tab === 'login' || tab === 'register') && (
          <div className="mb-4 flex rounded-md border border-border p-1 text-sm">
            <button
              onClick={() => setTab('login')}
              className={`flex-1 rounded px-2 py-1 ${tab === 'login' ? 'bg-accent text-white' : 'text-text-secondary'}`}
            >
              {t('auth.login')}
            </button>
            <button
              onClick={() => setTab('register')}
              className={`flex-1 rounded px-2 py-1 ${tab === 'register' ? 'bg-accent text-white' : 'text-text-secondary'}`}
            >
              {t('auth.register')}
            </button>
          </div>
        )}

        {tab === 'login' && (
          <LoginForm
            onForgotPassword={() => setTab('forgot')}
            onVerifyEmail={() => setTab('verify')}
          />
        )}
        {tab === 'register' && <RegisterForm onVerifyEmail={() => setTab('verify')} />}
        {tab === 'forgot' && (
          <ForgotPasswordForm onBack={() => setTab('login')} onHaveToken={() => setTab('reset')} />
        )}
        {tab === 'reset' && <ResetPasswordForm onBack={() => setTab('login')} />}
        {tab === 'verify' && <VerifyEmailPanel onDone={() => setTab('login')} />}
      </Card>
    </div>
  )
}
