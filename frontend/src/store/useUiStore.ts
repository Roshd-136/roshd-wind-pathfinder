import { create } from 'zustand'

interface UiState {
  isControlPanelOpen: boolean
  isMobileSheetOpen: boolean
  mapMode: '2d' | '3d'
  toggleControlPanel: () => void
  openMobileSheet: () => void
  closeMobileSheet: () => void
  setMapMode: (mode: '2d' | '3d') => void
}

/** حالت‌های صرفاً رابط کاربری — چیزی که نباید در URL یا سرور ذخیره شود. */
export const useUiStore = create<UiState>((set) => ({
  isControlPanelOpen: true,
  isMobileSheetOpen: false,
  mapMode: '2d',
  toggleControlPanel: () => set((s) => ({ isControlPanelOpen: !s.isControlPanelOpen })),
  openMobileSheet: () => set({ isMobileSheetOpen: true }),
  closeMobileSheet: () => set({ isMobileSheetOpen: false }),
  setMapMode: (mapMode) => set({ mapMode }),
}))
