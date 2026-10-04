import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useSettingsStore } from '../../store/useSettingsStore'

/**
 * نوار بالای صفحات نقشه — عنوان + زیرعنوان و کلید تغییر تم روشن/تاریک،
 * دقیقاً مطابق نوار بالای mockup. چیدمان با ویژگی‌های منطقی (start/end)
 * است تا در RTL و LTR درست بنشیند.
 */
export function AppHeader() {
  const { t } = useTranslation()
  const theme = useSettingsStore((s) => s.theme)
  const setTheme = useSettingsStore((s) => s.setTheme)

  const isDark = theme !== 'light'
  const toggleTheme = () => setTheme(isDark ? 'light' : 'dark')

  return (
    <header className="flex items-center justify-between gap-4 border-b border-border bg-surface px-4 py-3">
      <div>
        <h1 className="text-base font-semibold text-text-primary">{t('map.title')}</h1>
        <p className="text-xs text-text-muted">{t('map.subtitle')}</p>
      </div>
      <button
        type="button"
        onClick={toggleTheme}
        aria-label={t('settings.theme')}
        title={t('settings.theme')}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-raised text-text-secondary transition-colors hover:text-text-primary"
      >
        {isDark ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
      </button>
    </header>
  )
}
