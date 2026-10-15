import { useMutation } from '@tanstack/react-query'
import {
  confirmPasswordReset,
  login,
  register,
  requestPasswordReset,
  verifyEmail,
  type AuthTokens,
  type User,
} from '../services/api/auth'

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

/** POST /auth/password-reset/confirm */
export function useConfirmPasswordReset() {
  return useMutation<void, Error, { token: string; newPassword: string }>({
    mutationFn: ({ token, newPassword }) => confirmPasswordReset(token, newPassword),
  })
}

/** POST /auth/verify-email/confirm */
export function useVerifyEmail() {
  return useMutation<void, Error, string>({
    mutationFn: verifyEmail,
  })
}
