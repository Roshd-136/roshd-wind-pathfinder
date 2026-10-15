import { useTranslation } from 'react-i18next'
import type { Algorithm } from '../../../types/routing'
import { Select } from '../../ui/Select'

interface AlgorithmSelectorProps {
  value: Algorithm
  onChange: (value: Algorithm) => void
}

/**
 * انتخاب الگوریتم مسیریابی — گزینه‌ها منطبق با `GET /algorithms` در
 * api/openapi.yaml (`a_star` پیش‌فرض، `dijkstra` جایگزین).
 */
export function AlgorithmSelector({ value, onChange }: AlgorithmSelectorProps) {
  const { t } = useTranslation()

  return (
    <Select
      label={t('routing.algorithm')}
      value={value}
      onChange={(v) => onChange(v as Algorithm)}
      options={[
        { value: 'a_star', label: 'A* (Wind Aware)' },
        { value: 'dijkstra', label: 'Dijkstra' },
      ]}
    />
  )
}
