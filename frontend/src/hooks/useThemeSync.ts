import { useEffect } from 'react'
import { useSettingsStore } from '../store/useSettingsStore'

/**
 * `theme` را از ترجیحات کاربر به `document.documentElement[data-theme]`
 * اعمال می‌کند تا توکن‌های رنگ در `tokens.css` فعال شوند.
 * `system` یعنی از `prefers-color-scheme` مرورگر پیروی می‌شود (بدون
 * override دستی، چون پیش‌فرض ریشه در tokens.css خودش تاریک است).
 */
export function useThemeSync() {
  const theme = useSettingsStore((s) => s.theme)

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') {
      root.removeAttribute('data-theme')
      return
    }
    root.setAttribute('data-theme', theme)
  }, [theme])
}
