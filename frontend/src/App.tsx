import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { useLanguageDirection } from './hooks/useLanguageDirection'
import { useThemeSync } from './hooks/useThemeSync'
import { AboutPage } from './pages/AboutPage'
import { Map2DPage } from './pages/Map2DPage'
import { Map3DPage } from './pages/Map3DPage'
import { SettingsPage } from './pages/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

function AppProviders() {
  useLanguageDirection()
  useThemeSync()

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Map2DPage />} />
        <Route path="map-3d" element={<Map3DPage />} />
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
