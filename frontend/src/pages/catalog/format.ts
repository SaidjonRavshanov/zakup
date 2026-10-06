import type { PaymentMethod, PaymentTerms } from '@/entities/catalog'
import { fill, type Zk } from '@/shared/i18n/use-zk'

/** Prototip `term()`: "Отсрочка 14 дн." / "По факту" / "Предоплата". */
export function termsLabel(z: Zk, terms: PaymentTerms, deferralDays: number): string {
  if (terms === 'deferred') return fill(z.term_delay, { n: deferralDays })
  return terms === 'prepay' ? z.term_prepay : z.term_fact
}

/** "Нал / Пер". */
export function methodsLabel(z: Zk, methods: PaymentMethod[], sep = ', '): string {
  return methods.map((m) => (m === 'cash' ? z.pm_cash : z.pm_bank)).join(sep)
}

/** Hafta kunlari (1 = Du) — prototip `t.wd`. */
export const weekdayNames = (z: Zk): string[] => z.wd.split(',')
