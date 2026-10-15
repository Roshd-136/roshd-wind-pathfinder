import { create } from 'zustand'

/** تنظیمات نمایش نقشه — چارچوب ابزار «نمای نقشه». */
export interface ViewportSettings {
  /** نقشهٔ پایه: ساده (OSM) یا ماهواره‌ای (Esri World Imagery آزاد). */
  mapStyle: 'simple' | 'satellite'
  showArrows: boolean
  showHeatmap: boolean
  showHillshade: boolean
}

interface UiState {
  isControlPanelOpen: boolean
  isMobileSheetOpen: boolean
  isSidebarOpen: boolean
  mapMode: '2d' | '3d'
  isViewportSettingsOpen: boolean
  viewport: ViewportSettings
  toggleControlPanel: () => void
  toggleSidebar: () => void
  openMobileSheet: () => void
  closeMobileSheet: () => void
  setMapMode: (mode: '2d' | '3d') => void
  toggleViewportSettings: () => void
  setViewport: (patch: Partial<ViewportSettings>) => void
}

/** حالت‌های صرفاً رابط کاربری — چیزی که نباید در URL یا سرور ذخیره شود. */
export const useUiStore = create<UiState>((set) => ({
  isControlPanelOpen: true,
  isMobileSheetOpen: true,
  isSidebarOpen: false,
  mapMode: '2d',
  isViewportSettingsOpen: false,
  viewport: { mapStyle: 'simple', showArrows: true, showHeatmap: true, showHillshade: true },
  toggleControlPanel: () => set((s) => ({ isControlPanelOpen: !s.isControlPanelOpen })),
  toggleSidebar: () => set((s) => ({ isSidebarOpen: !s.isSidebarOpen })),
  openMobileSheet: () => set({ isMobileSheetOpen: true }),
  closeMobileSheet: () => set({ isMobileSheetOpen: false }),
  setMapMode: (mapMode) => set({ mapMode }),
  toggleViewportSettings: () => set((s) => ({ isViewportSettingsOpen: !s.isViewportSettingsOpen })),
  setViewport: (patch) => set((s) => ({ viewport: { ...s.viewport, ...patch } })),
}))
