/**
 * Kirish oqimi (ARCHITECTURE §7): Telegram initData → access + refresh.
 * Brauzerda (faqat dev) — /auth/dev orqali, Telegram ID qo'lda kiritiladi.
 */
import { isInTelegram, telegram } from '@/shared/lib/telegram'
import { ApiError, apiRequest, setSessionRenewer } from './client'
import { session, type SessionDto } from './session'

export interface DevIdentity {
  telegram_id: number
  first_name: string
  username?: string
}

async function start(path: string, body: unknown): Promise<void> {
  session.set(await apiRequest<SessionDto>(path, { method: 'POST', body, auth: false }))
}

export const signInWithTelegram = () => start('/auth/telegram', { init_data: telegram.initData() })

const DEV_IDENTITY_KEY = 'zakup.devIdentity'

/** Oxirgi dev-kirish: "qayta tekshirish" va sahifa yangilanganda qayta so'ramaslik uchun. */
export function rememberedDevIdentity(): DevIdentity | null {
  try {
    const raw = localStorage.getItem(DEV_IDENTITY_KEY)
    return raw ? (JSON.parse(raw) as DevIdentity) : null
  } catch {
    return null
  }
}

export function forgetDevIdentity(): void {
  session.clear()
  try {
    localStorage.removeItem(DEV_IDENTITY_KEY)
  } catch {
    /* e'tiborsiz */
  }
}

export async function devSignIn(identity: DevIdentity): Promise<void> {
  try {
    localStorage.setItem(DEV_IDENTITY_KEY, JSON.stringify(identity))
  } catch {
    /* faqat shu safar */
  }
  await start('/auth/dev', identity)
}

/**
 * Sessiya bormi? Bo'lmasa Telegram ichida avtomatik kiradi (dev'da — oxirgi dev-identity bilan).
 * false — qo'lda kirish kerak. Akkaunt faollashtirilmagan bo'lsa — ApiError('account_pending').
 */
export async function ensureSession(): Promise<boolean> {
  if (session.hasAny()) return true
  if (isInTelegram) {
    await signInWithTelegram()
    return true
  }
  const dev = import.meta.env.DEV ? rememberedDevIdentity() : null
  if (!dev) return false
  await devSignIn(dev)
  return true
}

/** Ilova Telegram ichidan brauzerda ochilgan bo'lsa (#handoff=kod) — kodni sessiyaga olib, manzildan o'chiramiz. */
export function adoptBrowserHandoff(): void {
  const match = /^#handoff=([\w-]+)$/.exec(window.location.hash)
  if (!match?.[1]) return
  session.adoptRefresh(match[1])
  window.history.replaceState(null, '', window.location.pathname + window.location.search)
}

/** Telegram ichida: shu foydalanuvchi bilan tizim brauzerida ochiladigan havola (2 daqiqa, bir martalik). */
export async function browserHandoffUrl(): Promise<string> {
  const { code } = await apiRequest<{ code: string }>('/auth/handoff', { method: 'POST' })
  return `${window.location.origin}/#handoff=${code}`
}

export async function signOut(): Promise<void> {
  const refresh = session.refreshToken()
  session.clear()
  if (refresh) await apiRequest<void>('/auth/logout', { method: 'POST', body: { refresh_token: refresh }, auth: false })
}

async function renew(): Promise<boolean> {
  const refresh = session.refreshToken()
  if (refresh) {
    try {
      await start('/auth/refresh', { refresh_token: refresh })
      return true
    } catch (error) {
      if (!(error instanceof ApiError) || error.status >= 500) throw error
      session.clear()
    }
  }
  if (!isInTelegram) return false
  await signInWithTelegram()
  return true
}

// Bir vaqtda kelgan bir nechta 401 → bitta refresh (refresh token bir martalik!)
let inFlight: Promise<boolean> | null = null
setSessionRenewer(() => {
  inFlight ??= renew().finally(() => {
    inFlight = null
  })
  return inFlight
})
