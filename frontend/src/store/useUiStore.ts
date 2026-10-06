import { create } from 'zustand'

interface UiState {
  isControlPanelOpen: boolean
  isMobileSheetOpen: boolean
  isSidebarOpen: boolean
  mapMode: '2d' | '3d'
  toggleControlPanel: () => void
  toggleSidebar: () => void
  openMobileSheet: () => void
  closeMobileSheet: () => void
  setMapMode: (mode: '2d' | '3d') => void
}

/** حالت‌های صرفاً رابط کاربری — چیزی که نباید در URL یا سرور ذخیره شود. */
export const useUiStore = create<UiState>((set) => ({
  isControlPanelOpen: true,
  isMobileSheetOpen: true,
  isSidebarOpen: false,
  mapMode: '2d',
  toggleControlPanel: () => set((s) => ({ isControlPanelOpen: !s.isControlPanelOpen })),
  toggleSidebar: () => set((s) => ({ isSidebarOpen: !s.isSidebarOpen })),
  openMobileSheet: () => set({ isMobileSheetOpen: true }),
  closeMobileSheet: () => set({ isMobileSheetOpen: false }),
  setMapMode: (mapMode) => set({ mapMode }),
}))
