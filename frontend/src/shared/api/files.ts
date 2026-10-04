/**
 * Fayllar (nakladnoy fotosi, to'lov tasdig'i): xom tana bilan yuklash va avtorizatsiya bilan ko'rish.
 * `<img src>` ga token qo'yib bo'lmaydi — fayl fetch qilinib, blob URL beriladi.
 */
import { ApiError, apiRequest } from './client'
import { session } from './session'

const BASE = '/api/v1'

const authHeader = (): Record<string, string> => {
  const token = session.accessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/** POST xom tana (multipart'siz: backend Content-Type'dan oladi) → fayl ID. */
export async function uploadFile(path: string, file: Blob, retried = false): Promise<string> {
  const type = file.type || 'image/jpeg'
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': type, ...authHeader() },
    body: file,
  })
  if (response.status === 401 && !retried) {
    // access token eskirgan — umumiy klient orqali yangilab, bir marta qayta urinamiz
    await apiRequest('/me')
    return uploadFile(path, file, true)
  }
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
  const response = await fetch(`${BASE}${path}`, { headers: authHeader() })
  if (!response.ok) return null
  const blob = await response.blob()
  return { url: URL.createObjectURL(blob), type: blob.type }
}
