import { apiFetch, setAccessToken, setRefreshToken } from './client'

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface User {
  id: string
  email: string
  name: string
  email_verified: boolean
  created_at: string
}

/** POST /auth/register */
export function register(input: { email: string; password: string; name: string }): Promise<User> {
  return apiFetch<User>('/auth/register', { method: 'POST', body: input })
}

/** POST /auth/login */
export async function login(input: { email: string; password: string }): Promise<AuthTokens> {
  const tokens = await apiFetch<AuthTokens>('/auth/login', { method: 'POST', body: input })
  setAccessToken(tokens.access_token)
  setRefreshToken(tokens.refresh_token)
  return tokens
}

/** POST /auth/password-reset/request */
export function requestPasswordReset(email: string): Promise<void> {
  return apiFetch<void>('/auth/password-reset/request', { method: 'POST', body: { email } })
}

/** POST /auth/password-reset/confirm — تعیین رمز جدید با توکن ایمیل‌شده. */
export function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  return apiFetch<void>('/auth/password-reset/confirm', {
    method: 'POST',
    body: { token, new_password: newPassword },
  })
}

/** POST /auth/verify-email/confirm — تایید ایمیل با توکن ارسال‌شده. */
export function verifyEmail(token: string): Promise<void> {
  return apiFetch<void>('/auth/verify-email/confirm', { method: 'POST', body: { token } })
}

/** POST /auth/logout — ابطال refresh token ذخیره‌شده (اگر باشد). */
export async function logout(): Promise<void> {
  const refresh_token = localStorage.getItem('windpath-refresh-token')
  await apiFetch<void>('/auth/logout', {
    method: 'POST',
    body: refresh_token ? { refresh_token } : undefined,
  })
  setAccessToken(null)
  setRefreshToken(null)
}
