/**
 * Yengil i18n: lug'at — oddiy obyekt (`t.orders.title`), kalitlar TypeScript bilan tekshiriladi,
 * tashqi kutubxona yo'q (i18next ~40 KB). Til tanlovi: saqlangan → Telegram → brauzer → uz.
 */
import { useSyncExternalStore } from 'react'
import { createFormatters, type Formatters } from '@/shared/lib/format'
import { telegram } from '@/shared/lib/telegram'
import { ru } from './locales/ru'
import { uz, type Messages } from './locales/uz'

export type Locale = 'uz' | 'ru'
export type { Messages }

interface LocaleMeta {
  label: string
  intl: string
}

export const LOCALES: Record<Locale, LocaleMeta> = {
  uz: { label: "O'zbekcha", intl: 'uz-Latn-UZ' },
  ru: { label: 'Русский', intl: 'ru-RU' },
}

const DICTIONARIES: Record<Locale, Messages> = { uz, ru }
const STORAGE_KEY = 'zakup.locale'

const isLocale = (value: unknown): value is Locale => value === 'uz' || value === 'ru'

function fromLanguageCode(code: string | null | undefined): Locale | null {
  const base = code?.toLowerCase().split('-')[0]
  return isLocale(base) ? base : null
}

function detectLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (isLocale(saved)) return saved
  } catch {
    /* private rejim */
  }
  return fromLanguageCode(telegram.languageCode()) ?? fromLanguageCode(navigator.language) ?? 'uz'
}

interface I18nState {
  locale: Locale
  t: Messages
  fmt: Formatters
}

const buildState = (locale: Locale): I18nState => ({
  locale,
  t: DICTIONARIES[locale],
  fmt: createFormatters(LOCALES[locale].intl, DICTIONARIES[locale].compact),
})

let state = buildState(detectLocale())
const listeners = new Set<() => void>()

export function initI18n(): void {
  document.documentElement.lang = state.locale
}

export function setLocale(locale: Locale): void {
  if (locale === state.locale) return
  try {
    localStorage.setItem(STORAGE_KEY, locale)
  } catch {
    /* tanlov faqat shu sessiyada */
  }
  state = buildState(locale)
  document.documentElement.lang = locale
  listeners.forEach((listener) => listener())
}

/** Hook'dan tashqarida (API client) joriy til. */
export const getLocale = (): Locale => state.locale

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Til almashganda faqat shu hook'ni chaqirgan komponentlar qayta chiziladi. */
export function useI18n(): I18nState {
  return useSyncExternalStore(subscribe, () => state)
}
