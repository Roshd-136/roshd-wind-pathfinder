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
          label={t('settings.theme')}
          value={theme}
          onChange={(v) => setTheme(v as typeof theme)}
          options={[
            { value: 'dark', label: t('settings.themeDark') },
            { value: 'light', label: t('settings.themeLight') },
            { value: 'system', label: t('settings.themeSystem') },
          ]}
        />
        <Select
          label={t('settings.language')}
          value={language}
          onChange={(v) => setLanguage(v as typeof language)}
          options={[
            { value: 'fa', label: 'فارسی' },
            { value: 'en', label: 'English' },
          ]}
        />
        <Select
          label={t('settings.units')}
          value={units}
          onChange={(v) => setUnits(v as typeof units)}
          options={[
            { value: 'metric', label: t('settings.unitsMetric') },
            { value: 'imperial', label: t('settings.unitsImperial') },
          ]}
        />
        <Select
          label={t('routing.algorithm')}
          value={defaultAlgorithm}
          onChange={(v) => setDefaultAlgorithm(v as typeof defaultAlgorithm)}
          options={[
            { value: 'a_star', label: `A* (Wind Aware) — ${t('routing.algorithmDefault')}` },
            { value: 'dijkstra', label: `Dijkstra — ${t('routing.algorithmFallback')}` },
          ]}
        />
        <Select
          label={t('routing.criterion')}
          value={defaultCriterion}
          onChange={(v) => setDefaultCriterion(v as typeof defaultCriterion)}
          options={[
            { value: 'time', label: t('routing.criterionTime') },
            { value: 'energy', label: t('routing.criterionEnergy') },
            { value: 'balanced', label: t('routing.criterionBalanced') },
          ]}
        />
      </Card>
    </div>
  )
}
