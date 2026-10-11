import type { User } from './auth'
import { apiFetch } from './client'
import type { RouteResult } from '../../types/routing'

export interface Preferences {
  units: 'metric' | 'imperial'
  theme: 'light' | 'dark' | 'system'
  language: 'fa' | 'en'
  default_algorithm: 'a_star' | 'dijkstra'
  default_criterion: 'time' | 'energy' | 'balanced'
}

export interface RouteHistoryPage {
  items: RouteResult[]
  next_cursor: string | null
}

/**
 * همهٔ مسیرها با پیشوند `/v1` — روتر بک‌اند `account` با
 * `prefix="/account"` تعریف و در `api/main.py` با `prefix="/v1"` مانت می‌شود
 * (`/v1/account`)؛ مسیرهای `/me...` در سرور وجود ندارند.
 */

/** GET /v1/account — پروفایل کاربر جاری. */
export function getMe(): Promise<User> {
  return apiFetch<User>('/v1/account')
}

/** GET /v1/account/preferences */
export function getPreferences(): Promise<Preferences> {
  return apiFetch<Preferences>('/v1/account/preferences')
}

/** PUT /v1/account/preferences */
export function updatePreferences(preferences: Preferences): Promise<Preferences> {
  return apiFetch<Preferences>('/v1/account/preferences', { method: 'PUT', body: preferences })
}

/** GET /v1/account/history */
export function getRouteHistory(): Promise<RouteHistoryPage> {
  return apiFetch<RouteHistoryPage>('/v1/account/history')
}
