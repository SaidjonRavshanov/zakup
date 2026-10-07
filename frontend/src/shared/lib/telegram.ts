/**
 * Telegram Mini App ustidan yupqa adapter.
 * Ilovaning qolgan qismi `window.Telegram` ni to'g'ridan-to'g'ri bilmaydi (DIP):
 * brauzerda (lokal dev) xuddi shu interfeys xavfsiz no-op sifatida ishlaydi.
 */

type ColorScheme = 'light' | 'dark'
type HapticImpact = 'light' | 'medium' | 'heavy'
type HapticNotice = 'success' | 'warning' | 'error'

interface TgButton {
  show(): void
  hide(): void
  onClick(cb: () => void): void
  offClick(cb: () => void): void
}

interface TgWebApp {
  initData: string
  /** Imzosiz nusxa — faqat UI uchun (til), ishonch/ruxsat uchun emas: backend initData'ni tekshiradi. */
  initDataUnsafe: { user?: { id?: number; language_code?: string } }
  colorScheme: ColorScheme
  platform: string
  version: string
  ready(): void
  expand(): void
  isVersionAtLeast(v: string): boolean
  setHeaderColor(color: string): void
  setBackgroundColor(color: string): void
  setBottomBarColor?(color: string): void
  disableVerticalSwipes?(): void
  /** Bot API 8.0: to'liq ekran (Telegram Desktop'da — butun oyna/monitor). */
  requestFullscreen?(): void
  isFullscreen?: boolean
  onEvent(event: 'themeChanged', cb: () => void): void
  offEvent(event: 'themeChanged', cb: () => void): void
  BackButton: TgButton
  HapticFeedback: {
    impactOccurred(style: HapticImpact): void
    notificationOccurred(type: HapticNotice): void
    selectionChanged(): void
  }
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TgWebApp }
  }
}

const webApp: TgWebApp | undefined = window.Telegram?.WebApp

/** Telegram ichida ochilganmi (brauzerda initData bo'sh bo'ladi). */
export const isInTelegram = Boolean(webApp?.initData)

/** Kompyuterdagi Telegram (Windows/Linux — tdesktop, macOS) — keng ekran uchun to'liq ekran so'raladi. */
export const isTelegramDesktop = isInTelegram && ['tdesktop', 'macos'].includes(webApp?.platform ?? '')

export const telegram = {
  initData: (): string => webApp?.initData ?? '',

  /** Faqat ko'rsatish uchun ("admin'ga ID yuboring"); ishonch uchun emas. */
  userId: (): number | null => (isInTelegram ? (webApp?.initDataUnsafe.user?.id ?? null) : null),

  languageCode: (): string | null => (isInTelegram ? (webApp?.initDataUnsafe.user?.language_code ?? null) : null),

  colorScheme: (): ColorScheme | null => (isInTelegram && webApp ? webApp.colorScheme : null),

  init(): void {
    if (!isInTelegram || !webApp) return
    webApp.ready()
    webApp.expand()
    // Kompyuterda kichik oyna telefon ko'rinishini beradi — to'liq ekranda chap menyuli desktop ko'rinishi
    if (isTelegramDesktop && webApp.isVersionAtLeast('8.0')) {
      try {
        webApp.requestFullscreen?.()
      } catch {
        /* eski klient — oddiy oynada qoladi */
      }
    }
    // Ro'yxatni pastga tortganda ilova yopilib qolmasin
    if (webApp.isVersionAtLeast('7.7')) webApp.disableVerticalSwipes?.()
  },

  /** Telegram oynasi ranglarini ilova foni bilan tenglash — "chok" ko'rinmasin. */
  paintChrome(bg: string): void {
    if (!isInTelegram || !webApp || !webApp.isVersionAtLeast('6.1')) return
    webApp.setHeaderColor(bg)
    webApp.setBackgroundColor(bg)
    if (webApp.isVersionAtLeast('7.10')) webApp.setBottomBarColor?.(bg)
  },

  onThemeChange(cb: () => void): () => void {
    if (!isInTelegram || !webApp) return () => {}
    webApp.onEvent('themeChanged', cb)
    return () => webApp.offEvent('themeChanged', cb)
  },

  backButton(cb: (() => void) | null): () => void {
    if (!isInTelegram || !webApp || !webApp.isVersionAtLeast('6.1')) return () => {}
    if (!cb) {
      webApp.BackButton.hide()
      return () => {}
    }
    webApp.BackButton.onClick(cb)
    webApp.BackButton.show()
    return () => {
      webApp.BackButton.offClick(cb)
      webApp.BackButton.hide()
    }
  },

  haptic: {
    impact(style: HapticImpact = 'light'): void {
      if (isInTelegram) webApp?.HapticFeedback.impactOccurred(style)
    },
    notify(type: HapticNotice): void {
      if (isInTelegram) webApp?.HapticFeedback.notificationOccurred(type)
    },
    select(): void {
      if (isInTelegram) webApp?.HapticFeedback.selectionChanged()
    },
  },
}
