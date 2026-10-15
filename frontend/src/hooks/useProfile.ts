import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getMe,
  getPreferences,
  getRouteHistory,
  updatePreferences,
  type Preferences,
} from '../services/api/account'

/** GET /me */
export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: getMe })
}

/** GET /me/preferences */
export function usePreferences() {
  return useQuery({ queryKey: ['me', 'preferences'], queryFn: getPreferences })
}

/** PUT /me/preferences */
export function useUpdatePreferences() {
  const queryClient = useQueryClient()
  return useMutation<Preferences, Error, Preferences>({
    mutationFn: updatePreferences,
    onSuccess: (data) => queryClient.setQueryData(['me', 'preferences'], data),
  })
}

/** GET /me/routes — تاریخچه مسیرها */
export function useRouteHistory() {
  return useQuery({ queryKey: ['me', 'routes'], queryFn: getRouteHistory })
}
