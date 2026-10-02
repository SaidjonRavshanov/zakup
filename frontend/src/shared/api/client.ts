import { getLocale } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  /** Yozish so'rovlari uchun: qayta yuborilganda server dublikat yaratmaydi (ARCHITECTURE §9). */
  idempotencyKey?: string
  signal?: AbortSignal
}

const BASE_URL = '/api/v1'

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  // Accept-Language: backend xabarlari (bildirishnoma, PDF) foydalanuvchi tilida bo'lishi uchun
  const headers: Record<string, string> = { Accept: 'application/json', 'Accept-Language': getLocale() }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey
  const initData = telegram.initData()
  if (initData) headers['X-Telegram-Init-Data'] = initData

  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  })

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { code?: string; message?: string } | null
    throw new ApiError(response.status, payload?.code ?? 'http_error', payload?.message ?? response.statusText)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
