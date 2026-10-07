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
import { uploadFile } from '@/shared/api/files'
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

/**
 * Server rad etgan qabulni qayta yuborish (masalan, buyurtma holati to'g'rilangandan keyin).
 * Foto ham qayta yuklanadi — xato aynan fotoda bo'lishi mumkin. Qabul ID o'zgarmaydi: server takrorni tanib oladi.
 */
export async function retryReceipt(id: string): Promise<void> {
  const item = await tx('readonly', (store) => store.get(id) as IDBRequest<PendingReceipt | undefined>)
  if (!item) return
  await tx('readwrite', (store) => store.put({ ...item, error: null, photoId: null }))
  await refresh()
  // Yuborish ketayotgan bo'lsa, u bu yozuvni o'tkazib yuborgan bo'lishi mumkin — tugashini kutib, yana yuboramiz
  await flushing?.catch(() => undefined)
  await flush()
}

/** Chiqishda: navbatni butunlay tozalash (boshqa foydalanuvchiga o'tmasin). */
export async function clearOutbox(): Promise<void> {
  await tx('readwrite', (store) => store.clear())
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

// Osilib qolgan so'rov navbatni to'xtatib qo'ymasin (sekin tarmoqda foto yuklash uchun yetarli)
const SEND_TIMEOUT_MS = 90_000

async function withTimeout<T>(run: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), SEND_TIMEOUT_MS)
  try {
    return await run(controller.signal)
  } finally {
    window.clearTimeout(timer)
  }
}

/** Yozuv hali navbatdami (yuborish paytida foydalanuvchi o'chirgan bo'lishi mumkin). */
const exists = async (id: string) => (await tx('readonly', (store) => store.getKey(id))) !== undefined

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
        const blob = new Blob([item.photo], { type: item.photoType })
        photoId = await withTimeout((signal) => uploadFile('/receiving/attachments', blob, { signal }))
        if (!(await exists(item.id))) continue // o'chirilgan — qayta tiriltirmaymiz
        await tx('readwrite', (store) => store.put({ ...item, photoId }))
      }
      // captured_at — qabul telefonda rasmiylashtirilgan vaqt (oflayn bo'lsa yuborilgan vaqtdan oldin)
      const body = { ...item.payload, invoice_photo_id: photoId, captured_at: new Date(item.createdAt).toISOString() }
      await withTimeout((signal) => apiRequest('/receiving/receipts', { method: 'POST', body, signal }))
      await tx('readwrite', (store) => store.delete(item.id))
      onSent.forEach((listener) => listener(item.id))
    } catch (error) {
      if (error instanceof ApiError && error.status >= 400 && error.status < 500 && error.status !== 401 && (await exists(item.id))) {
        await tx('readwrite', (store) => store.put({ ...item, error: error.message }))
      }
      // tarmoq / 5xx / sessiya — keyingi urinishda
    }
  }
  await refresh()
}

/** Ilova ochilganda: holatni yuklash, ulanish tiklanganda va har 30 s da yuborish. */
export function startOutbox(): void {
  void refresh().then(flush)
  window.addEventListener('online', () => void flush())
  window.setInterval(() => void flush(), RETRY_MS)
}
