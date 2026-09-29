import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { useTranslation } from 'react-i18next'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { useLanguageDirection } from './hooks/useLanguageDirection'
import { useThemeSync } from './hooks/useThemeSync'
import { AboutPage } from './pages/AboutPage'
import { SettingsPage } from './pages/SettingsPage'

// Mapbox GL JS حجیم است (~600KB gzip)؛ فقط وقتی کاربر واقعاً وارد صفحات
// نقشه می‌شود بارگذاری می‌شود، نه در باندل اولیه.
const Map2DPage = lazy(() => import('./pages/Map2DPage').then((m) => ({ default: m.Map2DPage })))
const Map3DPage = lazy(() => import('./pages/Map3DPage').then((m) => ({ default: m.Map3DPage })))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function MapPageFallback() {
  const { t } = useTranslation()
  return <div className="flex h-full items-center justify-center text-text-muted">{t('common.loading')}</div>
}

function AppProviders() {
  useLanguageDirection()
  useThemeSync()

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route
          index
          element={
            <Suspense fallback={<MapPageFallback />}>
              <Map2DPage />
            </Suspense>
          }
        />
        <Route
          path="map-3d"
          element={
            <Suspense fallback={<MapPageFallback />}>
              <Map3DPage />
            </Suspense>
          }
        />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="about" element={<AboutPage />} />
      </Route>
    </Routes>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppProviders />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
