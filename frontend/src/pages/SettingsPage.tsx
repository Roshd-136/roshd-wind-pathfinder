import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { Select } from '../components/ui/Select'
import { useSettingsStore } from '../store/useSettingsStore'

/** صفحه تنظیمات — تم، زبان، واحد، الگوریتم/معیار پیش‌فرض (Preferences در OpenAPI). */
export function SettingsPage() {
  const { t } = useTranslation()
  const {
    theme,
    language,
    units,
    defaultAlgorithm,
    defaultCriterion,
    setTheme,
    setLanguage,
    setUnits,
    setDefaultAlgorithm,
    setDefaultCriterion,
  } = useSettingsStore()

  return (
    <div className="p-6">
      <Card className="max-w-md space-y-4">
        <h1 className="text-lg font-semibold text-text-primary">{t('nav.settings')}</h1>

        <Select
          label="Theme"
          value={theme}
          onChange={(v) => setTheme(v as typeof theme)}
          options={[
            { value: 'dark', label: 'Dark' },
            { value: 'light', label: 'Light' },
            { value: 'system', label: 'System' },
          ]}
        />
        <Select
          label="Language"
          value={language}
          onChange={(v) => setLanguage(v as typeof language)}
          options={[
            { value: 'fa', label: 'فارسی' },
            { value: 'en', label: 'English' },
          ]}
        />
        <Select
          label="Units"
          value={units}
          onChange={(v) => setUnits(v as typeof units)}
          options={[
            { value: 'metric', label: 'Metric (m/s, km)' },
            { value: 'imperial', label: 'Imperial (mph, mi)' },
          ]}
        />
        <Select
          label={t('routing.algorithm')}
          value={defaultAlgorithm}
          onChange={(v) => setDefaultAlgorithm(v as typeof defaultAlgorithm)}
          options={[
            { value: 'a_star', label: 'A* (Wind Aware) — default' },
            { value: 'dijkstra', label: 'Dijkstra — fallback' },
          ]}
        />
        <Select
          label="Optimization criterion"
          value={defaultCriterion}
          onChange={(v) => setDefaultCriterion(v as typeof defaultCriterion)}
          options={[
            { value: 'time', label: 'Time' },
            { value: 'energy', label: 'Energy' },
            { value: 'balanced', label: 'Balanced' },
          ]}
        />
      </Card>
    </div>
  )
}
