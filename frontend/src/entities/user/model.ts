import type { RoleKey } from '@/shared/i18n/keys'

export type Role = RoleKey

/** Rol + ombor doirasi; `store_id: null` — barcha omborlar. */
export interface Grant {
  role: Role
  store_id: string | null
}

export interface User {
  id: string
  telegram_id: number
  full_name: string
  username: string | null
  locale: 'uz' | 'ru'
  is_active: boolean
  grants: Grant[]
}

/** Backend tartibi bilan bir xil (shared_kernel/auth.py: Role). */
export const ROLES: ReadonlyArray<Role> = ['initiator', 'buyer', 'approver', 'storekeeper', 'accountant', 'auditor', 'admin']

/** Takrorlanmas rollar, ROLES tartibida. */
export const userRoles = (user: Pick<User, 'grants'>): Role[] =>
  ROLES.filter((role) => user.grants.some((grant) => grant.role === role))
