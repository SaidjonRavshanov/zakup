/** Ustki qatlamlar holati (sahifalardan chaqiriladi): tasdiqlash, toast, sahifa amallari. Komponentlar — overlays.tsx. */
import { useEffect, useSyncExternalStore, type ReactNode } from 'react'
import { telegram } from '@/shared/lib/telegram'

function createStore<T>(initial: T) {
  let value = initial
  const listeners = new Set<() => void>()
  return {
    get: () => value,
    set(next: T) {
      value = next
      listeners.forEach((l) => l())
    },
    use(): T {
      return useSyncExternalStore(
        (l) => {
          listeners.add(l)
          return () => listeners.delete(l)
        },
        () => value,
      )
    },
  }
}

// ---------------------------------------------------------------- tasdiqlash

export interface ConfirmRequest {
  title: ReactNode
  body?: ReactNode
  label: ReactNode
  cancel: ReactNode
  danger?: boolean
  resolve: (ok: boolean) => void
}

export const confirmStore = createStore<ConfirmRequest | null>(null)

/** Qaytarib bo'lmaydigan amal oldidan: `if (await confirmAction({...})) ...` */
export function confirmAction(req: Omit<ConfirmRequest, 'resolve'>): Promise<boolean> {
  // Oldingi so'rov javobsiz qolmasin — "yo'q" deb yopiladi
  confirmStore.get()?.resolve(false)
  return new Promise((resolve) => confirmStore.set({ ...req, resolve }))
}

/** Ochiq tasdiqlashni bekor qilish (masalan, sahifa almashganda). */
export function dismissConfirm(): void {
  const pending = confirmStore.get()
  if (!pending) return
  confirmStore.set(null)
  pending.resolve(false)
}

// ---------------------------------------------------------------- toast

export const toastStore = createStore<{ id: number; text: ReactNode; error?: boolean } | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | undefined

/** Qisqa xabar. `error` — xato (sahifa almashib, Banner ko'rsatib bo'lmaganda). */
export function toast(text: ReactNode, options: { error?: boolean } = {}): void {
  telegram.haptic.notify(options.error ? 'error' : 'success')
  toastStore.set({ id: Date.now(), text, error: options.error })
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => toastStore.set(null), options.error ? 5000 : 2400)
}

// ---------------------------------------------------------------- sahifa amallari

export interface PageAction {
  label: ReactNode
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  danger?: boolean
}

export interface PageActions {
  primary?: PageAction | null
  secondary?: PageAction | null
}

export const actionsStore = createStore<PageActions>({})

/** Sahifaning asosiy amallari — pastki qotirilgan panelda. Har render'da yangilanadi, chiqishda tozalanadi. */
export function usePageActions(actions: PageActions): void {
  useEffect(() => {
    actionsStore.set(actions)
  })
  useEffect(() => () => actionsStore.set({}), [])
}
