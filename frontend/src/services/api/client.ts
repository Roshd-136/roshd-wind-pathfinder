/**
 * لایه پایه ارتباط با بک‌اند FastAPI.
 * ساختار پاسخ خطا دقیقاً منطبق با schema `Error`/`ValidationErrorBody`
 * در `api/openapi.yaml` است.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

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

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options

  const response = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.status === 204) {
    return undefined as T
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new ApiError(
      data?.message ?? 'خطای غیرمنتظره',
      data?.code ?? 'unknown_error',
      response.status,
      data?.request_id,
    )
  }

  return data as T
}
