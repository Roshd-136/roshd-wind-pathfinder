import { useMutation } from '@tanstack/react-query'
import { login, register, requestPasswordReset, type AuthTokens, type User } from '../services/api/auth'

/** POST /auth/login */
export function useLogin() {
  return useMutation<AuthTokens, Error, { email: string; password: string }>({
    mutationFn: login,
  })
}

/** POST /auth/register */
export function useRegister() {
  return useMutation<User, Error, { email: string; password: string; name: string }>({
    mutationFn: register,
  })
}

/** POST /auth/password-reset/request */
export function useRequestPasswordReset() {
  return useMutation<void, Error, string>({
    mutationFn: requestPasswordReset,
  })
}
