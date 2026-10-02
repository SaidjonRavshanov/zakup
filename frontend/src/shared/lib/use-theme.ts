import { useSyncExternalStore } from 'react'
import { applyTheme, readThemePref, resolveTheme, saveThemePref, type Theme, type ThemePref } from './theme'
import { telegram } from './telegram'

/** Kichik tashqi store: Context/Provider'siz, faqat obuna bo'lgan komponentlar qayta chiziladi. */
let pref: ThemePref = readThemePref()
let theme: Theme = resolveTheme(pref)
const listeners = new Set<() => void>()

function update(nextPref: ThemePref): void {
  pref = nextPref
  theme = resolveTheme(nextPref)
  applyTheme(theme)
  listeners.forEach((listener) => listener())
}

/** Ilova ishga tushganda bir marta: tizim / Telegram mavzusi o'zgarishini kuzatish. */
export function initTheme(): void {
  applyTheme(theme)
  const onSystemChange = () => pref === 'system' && update('system')
  matchMedia('(prefers-color-scheme: light)').addEventListener('change', onSystemChange)
  telegram.onThemeChange(onSystemChange)
}

export function setThemePref(next: ThemePref): void {
  saveThemePref(next)
  update(next)
}

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useTheme(): { pref: ThemePref; theme: Theme } {
  const currentPref = useSyncExternalStore(subscribe, () => pref)
  const currentTheme = useSyncExternalStore(subscribe, () => theme)
  return { pref: currentPref, theme: currentTheme }
}
