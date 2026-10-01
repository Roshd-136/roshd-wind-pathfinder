import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { useLanguageDirection } from './hooks/useLanguageDirection'
import { useThemeSync } from './hooks/useThemeSync'
import { AboutPage } from './pages/AboutPage'
import { SettingsPage } from './pages/SettingsPage'
import { OnboardingPage } from './pages/OnboardingPage'

// صفحات حجیم (Mapbox GL، فرم‌های Auth) فقط وقتی کاربر واقعاً واردشان
// می‌شود بارگذاری می‌شوند، نه در باندل اولیه.
const Map2DPage = lazy(() => import('./pages/Map2DPage').then((m) => ({ default: m.Map2DPage })))
const Map3DPage = lazy(() => import('./pages/Map3DPage').then((m) => ({ default: m.Map3DPage })))
const AuthPage = lazy(() => import('./pages/AuthPage').then((m) => ({ default: m.AuthPage })))
const ProfilePage = lazy(() => import('./pages/ProfilePage').then((m) => ({ default: m.ProfilePage })))
const ResultsPage = lazy(() => import('./pages/ResultsPage').then((m) => ({ default: m.ResultsPage })))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function PageFallback() {
  const { t } = useTranslation()
  return (
    <div className="flex h-full items-center justify-center text-text-muted">
      {t('common.loading')}
    </div>
  )
}

function withSuspense(element: ReactNode) {
  return <Suspense fallback={<PageFallback />}>{element}</Suspense>
}

function AppProviders() {
  useLanguageDirection()
  useThemeSync()

  return (
    <Routes>
      <Route path="onboarding" element={<OnboardingPage />} />
      <Route path="auth" element={withSuspense(<AuthPage />)} />
      <Route element={<AppShell />}>
        <Route index element={withSuspense(<Map2DPage />)} />
        <Route path="map-3d" element={withSuspense(<Map3DPage />)} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="profile" element={withSuspense(<ProfilePage />)} />
        <Route path="routes/:routeId" element={withSuspense(<ResultsPage />)} />
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
