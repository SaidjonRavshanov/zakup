/** Menyu rol bo'yicha (prototip menu()): telefonda 5 tadan ko'p bo'lsa — 4 ta + "Ещё". */
import {
  BookOpen,
  ChartLine,
  ClipboardList,
  House,
  Inbox,
  PackageCheck,
  RefreshCw,
  Truck,
  UserRound,
  UsersRound,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import type { Role } from '@/entities/user'
import type { ZkKey } from '@/shared/i18n/use-zk'

export type NavKey =
  | 'home'
  | 'todo'
  | 'requests'
  | 'orders'
  | 'receiving'
  | 'finance'
  | 'catalog'
  | 'analytics'
  | 'users'
  | 'iiko'
  | 'profile'

export const NAV: Record<NavKey, { to: string; icon: LucideIcon; label: ZkKey }> = {
  home: { to: '/', icon: House, label: 'home' },
  todo: { to: '/todo', icon: Inbox, label: 'inbox' },
  requests: { to: '/requests', icon: ClipboardList, label: 'requests' },
  orders: { to: '/orders', icon: Truck, label: 'orders' },
  receiving: { to: '/receiving', icon: PackageCheck, label: 'receiving' },
  finance: { to: '/finance', icon: Wallet, label: 'finance' },
  catalog: { to: '/catalog', icon: BookOpen, label: 'catalog' },
  analytics: { to: '/analytics', icon: ChartLine, label: 'analytics' },
  users: { to: '/admin/users', icon: UsersRound, label: 'users' },
  iiko: { to: '/admin/iiko', icon: RefreshCw, label: 'iiko' },
  profile: { to: '/profile', icon: UserRound, label: 'profile' },
}

export const MENU: Record<Role, NavKey[]> = {
  initiator: ['home', 'requests', 'catalog', 'profile'],
  buyer: ['home', 'requests', 'orders', 'catalog', 'analytics', 'finance', 'receiving', 'profile'],
  approver: ['home', 'requests', 'orders', 'finance', 'analytics', 'profile'],
  storekeeper: ['home', 'receiving', 'profile'],
  accountant: ['home', 'finance', 'orders', 'catalog', 'profile'],
  auditor: ['home', 'orders', 'receiving', 'finance', 'analytics', 'requests', 'profile'],
  admin: ['home', 'requests', 'finance', 'catalog', 'users', 'iiko', 'analytics', 'orders', 'receiving', 'profile'],
}

const ROOTS = new Set(Object.values(NAV).map((n) => n.to))

/** Ildiz sahifa (menyu bo'limi) — pastki menyu ko'rinadi; ichki sahifada — "Назад". */
export const isRootPath = (path: string) => ROOTS.has(path.replace(/\/+$/, '') || '/')

/** Ichki sahifaning bo'limi: /requests/Z-1 → /requests, /finance/suppliers/x → /finance. */
export function sectionOf(path: string): string {
  const clean = path.replace(/\/+$/, '') || '/'
  if (ROOTS.has(clean)) return clean
  if (clean.startsWith('/admin/users')) return '/admin/users'
  const first = `/${clean.split('/')[1] ?? ''}`
  return ROOTS.has(first) ? first : '/'
}

/** Desktop'da keng ustun (1040px) — ro'yxatlar va jadvallar; qolganlari 720px. */
export function isWidePath(path: string): boolean {
  return isRootPath(path) || path.startsWith('/finance/suppliers/')
}
