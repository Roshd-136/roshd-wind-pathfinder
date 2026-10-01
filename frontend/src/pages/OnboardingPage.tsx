import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'

const STEPS = [
  { title: 'خوش آمدید', body: 'مسیریاب بادی — کوتاه‌ترین/کم‌مصرف‌ترین مسیر را با در نظر گرفتن باد پیدا کنید.' },
  { title: 'انتخاب مبدأ و مقصد', body: 'روی نقشه کلیک کنید تا مبدأ و مقصد را مشخص کنید.' },
  { title: 'لایه و الگوریتم', body: 'لایه ارتفاعی و الگوریتم مسیریابی را از پنل کنار نقشه انتخاب کنید.' },
]

/** صفحه معرفی اولیه (چک‌لیست آیتم ۵) — یک‌بار برای کاربر جدید نمایش داده می‌شود. */
export function OnboardingPage() {
  const navigate = useNavigate()

  return (
    <div className="flex h-full items-center justify-center p-6">
      <Card className="max-w-md space-y-6 text-center">
        {STEPS.map((step) => (
          <div key={step.title}>
            <h2 className="mb-1 font-semibold text-text-primary">{step.title}</h2>
            <p className="text-sm text-text-secondary">{step.body}</p>
          </div>
        ))}
        <Button className="w-full" onClick={() => navigate('/')}>
          شروع کنید
        </Button>
      </Card>
    </div>
  )
}
