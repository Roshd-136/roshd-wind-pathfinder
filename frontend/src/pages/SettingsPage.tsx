import { useTranslation } from 'react-i18next'
import { Card } from '../components/ui/Card'
import { Select } from '../components/ui/Select'
import { useSettingsStore } from '../store/useSettingsStore'

/** پیش‌فرض‌های هواپیما/وسیلهٔ نقلیه — معادل VIZ_AIRCRAFT و تنوع‌های routing_scene. */
const VESSEL_CONFIGS = [
  { value: 'default', label: 'Default (20 m/s)', airspeed_mps: 20.0, induced_drag_coeff: 0.3, headwind_penalty_coeff: 0.25 },
  { value: 'cargo_5000dwt', label: 'Cargo 5000 DWT (15 m/s)', airspeed_mps: 15.0, induced_drag_coeff: 0.35, headwind_penalty_coeff: 0.3 },
  { value: 'tanker_10000dwt', label: 'Tanker 10000 DWT (12 m/s)', airspeed_mps: 12.0, induced_drag_coeff: 0.4, headwind_penalty_coeff: 0.35 },
  { value: 'container_20000dwt', label: 'Container 20000 DWT (18 m/s)', airspeed_mps: 18.0, induced_drag_coeff: 0.3, headwind_penalty_coeff: 0.25 },
  { value: 'bulk_15000dwt', label: 'Bulk 15000 DWT (14 m/s)', airspeed_mps: 14.0, induced_drag_coeff: 0.38, headwind_penalty_coeff: 0.32 },
  { value: 'ferry_2000dwt', label: 'Ferry 2000 DWT (22 m/s)', airspeed_mps: 22.0, induced_drag_coeff: 0.25, headwind_penalty_coeff: 0.2 },
]

/** صفحه تنظیمات — تم، زبان، واحد، الگوریتم/معیار پیش‌فرض، و هواپیما (Preferences در OpenAPI). */
export function SettingsPage() {
  const { t } = useTranslation()
  const {
    theme,
    language,
    units,
    defaultAlgorithm,
    defaultCriterion,
    defaultVessel,
    setTheme,
    setLanguage,
    setUnits,
    setDefaultAlgorithm,
    setDefaultCriterion,
    setDefaultVessel,
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
            { value: 'smooth', label: `Smoothed A* — ${t('routing.algorithmFallback')}` },
            { value: 'wind_riding', label: `Wind Riding — ${t('routing.algorithmFallback')}` },
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
            { value: 'distance', label: t('routing.criterionDistance') },
            { value: 'safety', label: t('routing.criterionSafety') },
          ]}
        />
        <Select
          label={t('settings.vessel')}
          value={defaultVessel}
          onChange={(v) => setDefaultVessel(v as typeof defaultVessel)}
          options={VESSEL_CONFIGS.map((v) => ({ value: v.value, label: v.label }))}
        />
      </Card>
    </div>
  )
}
