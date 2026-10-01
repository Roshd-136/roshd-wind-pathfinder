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

/** GET /me */
export function getMe(): Promise<User> {
  return apiFetch<User>('/me')
}

/** GET /me/preferences */
export function getPreferences(): Promise<Preferences> {
  return apiFetch<Preferences>('/me/preferences')
}

/** PUT /me/preferences */
export function updatePreferences(preferences: Preferences): Promise<Preferences> {
  return apiFetch<Preferences>('/me/preferences', { method: 'PUT', body: preferences })
}

/** GET /me/routes */
export function getRouteHistory(): Promise<RouteHistoryPage> {
  return apiFetch<RouteHistoryPage>('/me/routes')
}
