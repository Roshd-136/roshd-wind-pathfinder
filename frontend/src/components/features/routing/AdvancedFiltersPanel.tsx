import type { Criterion, RouteConstraints } from '../../../types/routing'
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
 * پنل فیلترهای پیشرفته مسیر — محدودیت ارتفاع، اجتناب از منطقه (toggle
 * ساده — انتخاب منطقه‌ی واقعی روی نقشه، فاز بعدی)، و معیار بهینه‌سازی
 * زمان/انرژی/متعادل، دقیقاً منطبق با `RouteConstraints` در OpenAPI
 * (چک‌لیست آیتم ۱۱).
 */
export function AdvancedFiltersPanel({ value, onChange }: AdvancedFiltersPanelProps) {
  const [altMin, altMax] = value.altitude_range_m ?? [ALTITUDE_MIN, ALTITUDE_MAX]

  return (
    <div className="space-y-3 border-t border-border pt-3">
      <h3 className="text-sm font-semibold text-text-primary">فیلترهای پیشرفته</h3>

      <Slider
        label="حداقل ارتفاع"
        value={altMin}
        min={ALTITUDE_MIN}
        max={altMax}
        unit=" m"
        onChange={(v) => onChange({ ...value, altitude_range_m: [v, altMax] })}
      />
      <Slider
        label="حداکثر ارتفاع"
        value={altMax}
        min={altMin}
        max={ALTITUDE_MAX}
        unit=" m"
        onChange={(v) => onChange({ ...value, altitude_range_m: [altMin, v] })}
      />

      <Select
        label="معیار بهینه‌سازی"
        value={value.criterion ?? 'time'}
        onChange={(v) => onChange({ ...value, criterion: v as Criterion })}
        options={[
          { value: 'time', label: 'زمان' },
          { value: 'energy', label: 'انرژی' },
          { value: 'balanced', label: 'متعادل' },
        ]}
      />

      <Checkbox
        label="اجتناب از مناطق علامت‌گذاری‌شده"
        checked={Boolean(value.avoid_zones?.length)}
        onChange={(e) =>
          onChange({ ...value, avoid_zones: e.target.checked ? (value.avoid_zones ?? []) : [] })
        }
      />
    </div>
  )
}
