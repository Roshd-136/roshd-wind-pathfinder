import { useTranslation } from 'react-i18next'
import type { Criterion, RouteConstraints } from '../../../types/routing'
import { Collapsible } from '../../ui/Collapsible'
import { Select } from '../../ui/Select'
import { Slider } from '../../ui/Slider'
import { Checkbox } from '../../ui/Checkbox'

interface AdvancedFiltersPanelProps {
  value: RouteConstraints
  onChange: (value: RouteConstraints) => void
}

const ALTITUDE_MIN = 0
const ALTITUDE_MAX = 500

/**
 * پنل فیلترهای پیشرفته مسیر — دسته‌بندی‌شده (ارتفاع پرواز، بهینه‌سازی،
 * اجتناب از مناطق) و هر دسته فقط با گسترش توسط کاربر نمایش داده می‌شود؛
 * منطبق با `RouteConstraints` در OpenAPI (چک‌لیست آیتم ۱۱).
 */
export function AdvancedFiltersPanel({ value, onChange }: AdvancedFiltersPanelProps) {
  const { t } = useTranslation()
  const [altMin, altMax] = value.altitude_range_m ?? [ALTITUDE_MIN, ALTITUDE_MAX]

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-text-primary">{t('routing.advancedFilters')}</h3>

      <Collapsible title={t('routing.catAltitude')}>
        <Slider
          label={t('routing.minAltitude')}
          value={altMin}
          min={ALTITUDE_MIN}
          max={altMax}
          unit=" m"
          onChange={(v) => onChange({ ...value, altitude_range_m: [v, altMax] })}
        />
        <Slider
          label={t('routing.maxAltitude')}
          value={altMax}
          min={altMin}
          max={ALTITUDE_MAX}
          unit=" m"
          onChange={(v) => onChange({ ...value, altitude_range_m: [altMin, v] })}
        />
      </Collapsible>

      <Collapsible title={t('routing.catOptimization')}>
        <Select
          label={t('routing.criterion')}
          value={value.criterion ?? 'time'}
          onChange={(v) => onChange({ ...value, criterion: v as Criterion })}
          options={[
            { value: 'time', label: t('routing.criterionTime') },
            { value: 'energy', label: t('routing.criterionEnergy') },
            { value: 'balanced', label: t('routing.criterionBalanced') },
          ]}
        />
      </Collapsible>

      <Collapsible title={t('routing.catAvoid')}>
        <Checkbox
          label={t('routing.avoidZones')}
          checked={Boolean(value.avoid_zones?.length)}
          onChange={(e) =>
            onChange({ ...value, avoid_zones: e.target.checked ? (value.avoid_zones ?? []) : [] })
          }
        />
      </Collapsible>
    </div>
  )
}
