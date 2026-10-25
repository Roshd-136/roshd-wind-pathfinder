/**
 * لایه پایه ارتباط با بک‌اند FastAPI.
 * ساختار پاسخ خطا دقیقاً منطبق با schema `Error`/`ValidationErrorBody`
 * در `api/openapi.yaml` است.
 *
 * توکن‌ها: access در حافظه؛ refresh در localStorage — پاسخ 401 (به‌جز
 * مسیرهای auth) یک‌بار با `/auth/refresh` تمدید و درخواست تکرار می‌شود.
 */

/**
 * همان‌مبدا پیشفرض است (`/v1/...`) — در توسعه vite proxy کرده و در استقرار
 * nginx `/v1/` را به backend میریزد. `VITE_API_BASE_URL` برای نمونههای
 * جداگانه باقی مانده است.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
const REFRESH_KEY = 'windpath-refresh-token'

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly requestId?: string

  constructor(message: string, code: string, status: number, requestId?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.requestId = requestId
  }
}

let accessToken: string | null = null

/** توسط `useAuth` بعد از لاگین/تمدید توکن فراخوانی می‌شود. */
export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setRefreshToken(token: string | null) {
  if (token) localStorage.setItem(REFRESH_KEY, token)
  else localStorage.removeItem(REFRESH_KEY)
}

function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

/** تمدید access token با refresh — یک‌بار در هر لحظه (جلوگیری از طوفان). */
let refreshing: Promise<boolean> | null = null
async function tryRefresh(): Promise<boolean> {
  const stored = getRefreshToken()
  if (!stored) return false
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${BASE_URL}/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: stored }),
      })
      if (!res.ok) return false
      const data = (await res.json()) as { access_token: string; refresh_token: string }
      accessToken = data.access_token
      setRefreshToken(data.refresh_token)
      return true
    } catch {
      return false
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

function headersWithAuth(headers?: HeadersInit): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(headers as Record<string, string> | undefined),
  }
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}, retried = false): Promise<T> {
  const { body, headers, ...rest } = options

  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: headersWithAuth(headers),
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) {
    return undefined as T
  }

  // 401 → یک‌بار تمدید توکن و تکرار درخواست (به‌جز مسیرهای auth)
  if (response.status === 401 && !path.startsWith('/auth/') && !retried && (await tryRefresh())) {
    return apiFetch<T>(path, options, true)
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      // پیام خطا: بک‌اند FastAPI خطا را در `detail` می‌گذارد (رشته یا فهرست
      // خطاهای اعتبارسنجی) — پیش‌تر فقط `message` خوانده می‌شد و پیام‌های
      // فارسی موتور (مثل «در این باند مسیر پروازپذیری نیست») هرگز به کاربر
      // نمی‌رسید و همیشه «خطای غیرمنتظره» دیده می‌شد.
      extractErrorMessage(data),
      data?.code ?? 'unknown_error',
      response.status,
      data?.request_id,
    )
  }

  return data as T
}

/** پیام خطا را از بدن‌های متعارف FastAPI (`detail`) و قرارداد خودی (`message`) بیرون می‌کشد. */
function extractErrorMessage(data: unknown): string {
  if (typeof data !== 'object' || data === null) return 'خطای غیرمنتظره'
  const record = data as Record<string, unknown>
  if (typeof record.message === 'string' && record.message) return record.message
  const detail = record.detail
  if (typeof detail === 'string' && detail) return detail
  // خطاهای اعتبارسنجی FastAPI: [{loc, msg, type}, ...]
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { msg?: unknown }
    if (typeof first?.msg === 'string') return first.msg
  }
  return 'خطای غیرمنتظره'
}
