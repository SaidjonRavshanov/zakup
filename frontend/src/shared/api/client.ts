import { getLocale } from '@/shared/i18n'
import { session } from './session'

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
  /** false — token qo'shilmaydi va 401 da sessiya yangilanmaydi (/auth/* so'rovlari). */
  auth?: boolean
}

const BASE_URL = '/api/v1'

/** 401 bo'lganda sessiyani tiklovchi (shared/api/auth.ts ro'yxatdan o'tkazadi). true — qayta urinish mumkin. */
type SessionRenewer = () => Promise<boolean>
let renewSession: SessionRenewer = async () => false

export function setSessionRenewer(renewer: SessionRenewer): void {
  renewSession = renewer
}

/** 401 dan keyin sessiyani tiklash (apiRequest'dan tashqari fetch'lar uchun: fayllar). true — qayta urinish mumkin. */
export function refreshSession(): Promise<boolean> {
  return renewSession()
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  // Accept-Language: backend xabarlari (bildirishnoma, PDF) foydalanuvchi tilida bo'lishi uchun
  const headers: Record<string, string> = { Accept: 'application/json', 'Accept-Language': getLocale() }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (options.idempotencyKey) headers['Idempotency-Key'] = options.idempotencyKey
  const token = options.auth === false ? null : session.accessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  return fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  })
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await send(path, options)
  // Access token yo'q yoki eskirgan → refresh (yoki Telegram orqali qayta kirish) → bir marta takror
  if (response.status === 401 && options.auth !== false && (await renewSession())) {
    response = await send(path, options)
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { code?: string; message?: string } | null
    throw new ApiError(response.status, payload?.code ?? 'http_error', payload?.message ?? response.statusText)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
