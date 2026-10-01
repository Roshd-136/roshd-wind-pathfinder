import { apiFetch, setAccessToken } from './client'

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
  return tokens
}

/** POST /auth/password-reset/request */
export function requestPasswordReset(email: string): Promise<void> {
  return apiFetch<void>('/auth/password-reset/request', { method: 'POST', body: { email } })
}

/** POST /auth/logout */
export async function logout(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST' })
  setAccessToken(null)
}
