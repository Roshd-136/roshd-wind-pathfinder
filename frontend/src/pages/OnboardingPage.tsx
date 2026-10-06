import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

const STEPS = [
  { titleKey: 'onboarding.welcome', bodyKey: 'onboarding.welcomeBody' },
  { titleKey: 'onboarding.pickPoints', bodyKey: 'onboarding.pickPointsBody' },
  { titleKey: 'onboarding.layerAlgorithm', bodyKey: 'onboarding.layerAlgorithmBody' },
] as const

/** صفحه معرفی اولیه (چک‌لیست آیتم ۵) — یک‌بار برای کاربر جدید نمایش داده می‌شود. */
export function OnboardingPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  return (
    <div className="flex h-full items-center justify-center p-6">
      <Card className="max-w-md space-y-6 text-center">
        {STEPS.map((step) => (
          <div key={step.titleKey}>
            <h2 className="mb-1 font-semibold text-text-primary">{t(step.titleKey)}</h2>
            <p className="text-sm text-text-secondary">{t(step.bodyKey)}</p>
          </div>
        ))}
        <Button className="w-full" onClick={() => navigate('/')}>
          {t('onboarding.start')}
        </Button>
      </Card>
    </div>
  )
}
