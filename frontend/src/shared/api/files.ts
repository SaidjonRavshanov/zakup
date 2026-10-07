/**
 * Fayllar (nakladnoy fotosi, to'lov tasdig'i): xom tana bilan yuklash va avtorizatsiya bilan ko'rish.
 * `<img src>` ga token qo'yib bo'lmaydi — fayl fetch qilinib, blob URL beriladi.
 */
import { ApiError, refreshSession } from './client'
import { session } from './session'

const BASE = '/api/v1'

const authHeader = (): Record<string, string> => {
  const token = session.accessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** 401 bo'lsa — sessiyani apiRequest kabi yangilab, bir marta qayta urinadi. */
async function fetchWithAuth(path: string, init: RequestInit = {}): Promise<Response> {
  const run = () => fetch(`${BASE}${path}`, { ...init, headers: { ...(init.headers as Record<string, string>), ...authHeader() } })
  const response = await run()
  if (response.status === 401 && (await refreshSession())) return run()
  return response
}

/** POST xom tana (multipart'siz: backend Content-Type'dan oladi) → fayl ID. */
export async function uploadFile(path: string, file: Blob, options: { signal?: AbortSignal } = {}): Promise<string> {
  const type = file.type || 'image/jpeg'
  const response = await fetchWithAuth(path, {
    method: 'POST',
    headers: { 'Content-Type': type },
    body: file,
    signal: options.signal,
  })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { code?: string; message?: string } | null
    throw new ApiError(response.status, payload?.code ?? 'http_error', payload?.message ?? response.statusText)
  }
  return ((await response.json()) as { id: string }).id
}

export interface LoadedFile {
  url: string // blob URL — chaqiruvchi URL.revokeObjectURL qiladi
  type: string
}

/** Faylni ko'rsatish uchun yuklab olish (rasm — <img>, PDF — havola). */
export async function loadFile(path: string): Promise<LoadedFile | null> {
  const response = await fetchWithAuth(path)
  if (!response.ok) return null
  const blob = await response.blob()
  return { url: URL.createObjectURL(blob), type: blob.type }
}
