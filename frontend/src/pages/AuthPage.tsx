import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { LoginForm } from '../components/features/auth/LoginForm'
import { RegisterForm } from '../components/features/auth/RegisterForm'
import { ForgotPasswordForm } from '../components/features/auth/ForgotPasswordForm'

type Tab = 'login' | 'register' | 'forgot'

/** صفحه احراز هویت — تب‌های ورود/ثبت‌نام/بازیابی رمز (چک‌لیست آیتم ۹). */
export function AuthPage() {
  const { t } = useTranslation()
  const [tab, setTab] = useState<Tab>('login')

  return (
    <div className="flex h-full items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <h1 className="mb-4 text-center text-lg font-semibold text-text-primary">
          {t('app.name')}
        </h1>

        {tab !== 'forgot' && (
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

        {tab === 'login' && <LoginForm onForgotPassword={() => setTab('forgot')} />}
        {tab === 'register' && <RegisterForm />}
        {tab === 'forgot' && <ForgotPasswordForm onBack={() => setTab('login')} />}
      </Card>
    </div>
  )
}
