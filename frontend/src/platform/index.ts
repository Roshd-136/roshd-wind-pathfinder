/**
 * تشخیص پلتفرم اجرا — یک کدبیس، سه هدف build (Web/PWA، Tauri، Capacitor).
 * کد فیچر هیچ‌وقت مستقیماً `window.__TAURI__`/Capacitor را چک نمی‌کند؛
 * همیشه از این ماژول عبور می‌کند تا جایگزینی/تست ساده بماند.
 */

export type Platform = 'web' | 'tauri' | 'capacitor'

declare global {
  interface Window {
    __TAURI__?: unknown
    Capacitor?: { isNativePlatform?: () => boolean }
  }
}

export function getPlatform(): Platform {
  if (typeof window === 'undefined') return 'web'
  if (window.__TAURI__) return 'tauri'
  if (window.Capacitor?.isNativePlatform?.()) return 'capacitor'
  return 'web'
}

export function isNative(): boolean {
  return getPlatform() !== 'web'
}
