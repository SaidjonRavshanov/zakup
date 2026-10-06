import { useQuery } from '@tanstack/react-query'
import { useActiveRole } from './active-role'
import { meQuery } from './api'
import type { Role } from './model'

/**
 * Tugma / forma ko'rsatish uchun: faol rol shu rollardan birimi (prototip: ekran faol rolga qarab).
 * Bir nechta roli bor xodim boshqa rol amallari uchun profilda rolni almashtiradi.
 * Haqiqiy tekshiruv — backend'da (use case); bu faqat UI'da keraksiz tugmani yashiradi.
 */
export function useHasRole(...roles: Role[]): boolean {
  const { data: me } = useQuery(meQuery)
  const active = useActiveRole(me)
  return active !== null && roles.includes(active)
}
