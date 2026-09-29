import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { useSettingsStore } from '../store/useSettingsStore'

/** صفحه تنظیمات — فرم کامل (واحد/تم/زبان/الگوریتم پیش‌فرض) در فاز ۳. */
export function SettingsPage() {
  const { t } = useTranslation()
  const { theme, language, setTheme, setLanguage } = useSettingsStore()

  return (
    <div className="p-6">
      <Card className="max-w-md">
        <h1 className="mb-4 text-lg font-semibold text-text-primary">{t('nav.settings')}</h1>
        <div className="mb-3 flex items-center justify-between text-sm">
          <span className="text-text-secondary">Theme</span>
          <select
            value={theme}
            onChange={(e) => setTheme(e.target.value as typeof theme)}
            className="rounded-md border border-border bg-surface-raised px-2 py-1 text-text-primary"
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="system">System</option>
          </select>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-secondary">Language</span>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as typeof language)}
            className="rounded-md border border-border bg-surface-raised px-2 py-1 text-text-primary"
          >
            <option value="fa">فارسی</option>
            <option value="en">English</option>
          </select>
        </div>
      </Card>
    </div>
  )
}
