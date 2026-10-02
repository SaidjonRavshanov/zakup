import { telegram } from './telegram'

export type ThemePref = 'system' | 'light' | 'dark'
export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'zakup.theme'

export function readThemePref(): ThemePref {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return value === 'light' || value === 'dark' ? value : 'system'
  } catch {
    return 'system'
  }
}

export function saveThemePref(pref: ThemePref): void {
  try {
    localStorage.setItem(STORAGE_KEY, pref)
  } catch {
    /* private rejim — tanlov faqat shu sessiyada qoladi */
  }
}

export function systemTheme(): Theme {
  return telegram.colorScheme() ?? (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
}

export function resolveTheme(pref: ThemePref): Theme {
  return pref === 'system' ? systemTheme() : pref
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement
  root.dataset.theme = theme
  const bg = getComputedStyle(root).getPropertyValue('--bg').trim()
  if (bg) telegram.paintChrome(bg)
}

/** Kuchsiz qurilmada og'ir effektlarni o'chirish (DESIGN_SYSTEM.md §6). */
export function detectPerformanceMode(): void {
  const nav = navigator as Navigator & { deviceMemory?: number }
  const weak = (nav.hardwareConcurrency ?? 8) <= 4 || (nav.deviceMemory ?? 8) <= 2
  if (weak) document.documentElement.dataset.perf = 'lite'
}
