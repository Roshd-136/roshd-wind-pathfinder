import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'system'
export type Language = 'fa' | 'en'
export type Algorithm = 'a_star' | 'dijkstra'
export type Criterion = 'time' | 'energy' | 'balanced'

interface SettingsState {
  theme: Theme
  language: Language
  units: 'metric' | 'imperial'
  defaultAlgorithm: Algorithm
  defaultCriterion: Criterion
  setTheme: (theme: Theme) => void
  setLanguage: (language: Language) => void
  setUnits: (units: 'metric' | 'imperial') => void
  setDefaultAlgorithm: (algorithm: Algorithm) => void
  setDefaultCriterion: (criterion: Criterion) => void
}

/**
 * ترجیحات کاربر (معادل schema `Preferences` در api/openapi.yaml).
 * محلی (localStorage) ذخیره می‌شود و وقتی کاربر لاگین است، با
 * `GET/PUT /me/preferences` همگام‌سازی می‌شود (در فاز ۳ / تسک احراز هویت).
 */
export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'dark',
      language: 'fa',
      units: 'metric',
      defaultAlgorithm: 'a_star',
      defaultCriterion: 'time',
      setTheme: (theme) => set({ theme }),
      setLanguage: (language) => set({ language }),
      setUnits: (units) => set({ units }),
      setDefaultAlgorithm: (defaultAlgorithm) => set({ defaultAlgorithm }),
      setDefaultCriterion: (defaultCriterion) => set({ defaultCriterion }),
    }),
    { name: 'windpath-settings' },
  ),
)
