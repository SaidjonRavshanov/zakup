/**
 * Sessiya tokenlari. Access — faqat xotirada (15 daq, XSS'da uzoq yashamaydi),
 * refresh — localStorage'da (ilova qayta ochilganda Telegram'siz ham davom etadi; bir martalik, rotatsiya).
 */

export interface SessionDto {
  access_token: string
  expires_in: number
  refresh_token: string
}

const REFRESH_KEY = 'zakup.refresh'

let accessToken: string | null = null

function readRefresh(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY)
  } catch {
    return null
  }
}

export const session = {
  accessToken: (): string | null => accessToken,

  refreshToken: readRefresh,

  hasAny: (): boolean => accessToken !== null || readRefresh() !== null,

  set(dto: SessionDto): void {
    accessToken = dto.access_token
    try {
      localStorage.setItem(REFRESH_KEY, dto.refresh_token)
    } catch {
      /* private rejim: sessiya faqat shu oynada */
    }
  },

  /** Telegram → brauzer: bir martalik kod refresh o'rnida (birinchi so'rovda oddiy sessiyaga almashadi). */
  adoptRefresh(code: string): void {
    accessToken = null
    try {
      localStorage.setItem(REFRESH_KEY, code)
    } catch {
      /* private rejim: kod ishlatilmaydi — "Telegram orqali oching" ekrani */
    }
  },

  clear(): void {
    accessToken = null
    try {
      localStorage.removeItem(REFRESH_KEY)
    } catch {
      /* e'tiborsiz */
    }
  },
}
