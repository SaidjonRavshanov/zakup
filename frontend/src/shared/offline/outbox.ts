/**
 * Oflayn navbat (ADR-08): omborda internet bo'lmasa ham qabul yo'qolmaydi.
 *
 * Yozuv IndexedDB'da (foto — Blob bilan) saqlanadi, ulanish bo'lganda tartib bilan yuboriladi:
 *   1) foto → POST /receiving/attachments (bir marta; olingan ID yozuvga saqlanadi)
 *   2) qabul → POST /receiving/receipts (ID klientda — qayta yuborish xavfsiz)
 * 4xx (server rad etdi) — yozuv xato bilan qoladi, foydalanuvchi ko'radi; tarmoq / 5xx — keyinroq qayta.
 */
import { useSyncExternalStore } from 'react'
import { ApiError, apiRequest } from '@/shared/api/client'
import { session } from '@/shared/api/session'

const DB_NAME = 'zakup-offline'
const STORE = 'receipts'
const RETRY_MS = 30_000

export interface PendingReceipt {
  id: string
  orderId: string
  orderNumber: string
  createdAt: number
  photo: Blob
  photoType: string
  photoId: string | null
  payload: Record<string, unknown> // invoice_photo_id'siz qabul tanasi
  error: string | null
}

let db: Promise<IDBDatabase> | null = null

function open(): Promise<IDBDatabase> {
  db ??= new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(STORE, { keyPath: 'id' })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
  return db
}

async function tx<T>(mode: IDBTransactionMode, run: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const database = await open()
  return new Promise((resolve, reject) => {
    const request = run(database.transaction(STORE, mode).objectStore(STORE))
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

// ---------------------------------------------------------------- holat (UI uchun)

let pending: PendingReceipt[] = []
const listeners = new Set<() => void>()
const emit = () => listeners.forEach((listener) => listener())

async function refresh(): Promise<void> {
  pending = (await tx('readonly', (store) => store.getAll() as IDBRequest<PendingReceipt[]>)).sort((a, b) => a.createdAt - b.createdAt)
  emit()
}

export function usePendingReceipts(): PendingReceipt[] {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    () => pending,
  )
}

// ---------------------------------------------------------------- navbat

export async function enqueueReceipt(item: Omit<PendingReceipt, 'createdAt' | 'photoId' | 'error'>): Promise<void> {
  await tx('readwrite', (store) => store.put({ ...item, createdAt: Date.now(), photoId: null, error: null }))
  await refresh()
  void flush()
}

export async function discardReceipt(id: string): Promise<void> {
  await tx('readwrite', (store) => store.delete(id))
  await refresh()
}

let flushing: Promise<void> | null = null

/** Navbatni yuborish (bir vaqtda bitta). Qabullar soni qaytarilmaydi — holat usePendingReceipts orqali. */
export function flush(): Promise<void> {
  flushing ??= send().finally(() => {
    flushing = null
  })
  return flushing
}

const onSent = new Set<(id: string) => void>()

/** Muvaffaqiyatli yuborilganda (masalan, ro'yxat keshini yangilash uchun). */
export function onReceiptSent(listener: (id: string) => void): () => void {
  onSent.add(listener)
  return () => onSent.delete(listener)
}

async function send(): Promise<void> {
  if (!navigator.onLine || !session.hasAny()) return
  for (const item of await tx('readonly', (store) => store.getAll() as IDBRequest<PendingReceipt[]>)) {
    if (item.error) continue
    try {
      let photoId = item.photoId
      if (!photoId) {
        photoId = (await uploadPhoto(item.photo, item.photoType)).id
        await tx('readwrite', (store) => store.put({ ...item, photoId }))
      }
      await apiRequest('/receiving/receipts', { method: 'POST', body: { ...item.payload, invoice_photo_id: photoId } })
      await tx('readwrite', (store) => store.delete(item.id))
      onSent.forEach((listener) => listener(item.id))
    } catch (error) {
      if (error instanceof ApiError && error.status >= 400 && error.status < 500 && error.status !== 401) {
        await tx('readwrite', (store) => store.put({ ...item, error: error.message }))
      }
      // tarmoq / 5xx / sessiya — keyingi urinishda
    }
  }
  await refresh()
}

async function uploadPhoto(photo: Blob, type: string, retried = false): Promise<{ id: string }> {
  // Xom tana: multipart'siz (backend Content-Type'dan oladi)
  const token = session.accessToken()
  const response = await fetch('/api/v1/receiving/attachments', {
    method: 'POST',
    headers: { 'Content-Type': type, ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: photo,
  })
  if (response.status === 401 && !retried) {
    // access token eskirgan — umumiy klient orqali yangilab, bir marta qayta urinamiz
    await apiRequest('/me')
    return uploadPhoto(photo, type, true)
  }
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { code?: string; message?: string } | null
    throw new ApiError(response.status, payload?.code ?? 'http_error', payload?.message ?? response.statusText)
  }
  return (await response.json()) as { id: string }
}

/** Ilova ochilganda: holatni yuklash, ulanish tiklanganda va har 30 s da yuborish. */
export function startOutbox(): void {
  void refresh().then(flush)
  window.addEventListener('online', () => void flush())
  window.setInterval(() => void flush(), RETRY_MS)
}
