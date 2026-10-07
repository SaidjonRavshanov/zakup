/**
 * Faol rol: bir nechta roli bor foydalanuvchi profilda almashtiradi, BottomNav shunga qarab o'zgaradi
 * (DESIGN_SYSTEM.md §7). Tanlov qurilmada saqlanadi.
 */
import { useSyncExternalStore } from 'react'
import { userRoles, type Role, type User } from './model'

const STORAGE_KEY = 'zakup.role'
const listeners = new Set<() => void>()

function read(): Role | null {
  try {
    return localStorage.getItem(STORAGE_KEY) as Role | null
  } catch {
    return null
  }
}

let chosen: Role | null = read()

export function setActiveRole(role: Role): void {
  chosen = role
  try {
    localStorage.setItem(STORAGE_KEY, role)
  } catch {
    /* faqat shu sessiyada */
  }
  listeners.forEach((listener) => listener())
}

/** Chiqishda: saqlangan tanlovni o'chirish (keyingi foydalanuvchiga o'tmasin). */
export function clearActiveRole(): void {
  chosen = null
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* e'tiborsiz */
  }
  listeners.forEach((listener) => listener())
}

const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** Tanlangan rol, agar foydalanuvchida hali bor bo'lsa; aks holda birinchisi. Rolsiz — null. */
export function useActiveRole(user: Pick<User, 'grants'> | undefined): Role | null {
  const selected = useSyncExternalStore(subscribe, () => chosen)
  if (!user) return null
  const roles = userRoles(user)
  return selected && roles.includes(selected) ? selected : (roles[0] ?? null)
}
