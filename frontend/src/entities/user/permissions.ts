import { useQuery } from '@tanstack/react-query'
import { meQuery } from './api'
import type { Role } from './model'

/**
 * Tugma / forma ko'rsatish uchun: foydalanuvchida shu rollardan biri bormi (qaysidir omborda).
 * Haqiqiy tekshiruv — backend'da (use case); bu faqat UI'da keraksiz tugmani yashiradi.
 */
export function useHasRole(...roles: Role[]): boolean {
  const { data: me } = useQuery(meQuery)
  return me?.grants.some((grant) => roles.includes(grant.role)) ?? false
}
