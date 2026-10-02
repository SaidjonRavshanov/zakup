import { queryOptions } from '@tanstack/react-query'
import type { Locale } from '@/shared/i18n'
import { buildMockOrders } from './mock'
import type { PurchaseOrder } from './model'

// TODO(procurement API): apiRequest<PurchaseOrder[]>('/purchase-orders') ga almashtirish.
// Til queryKey'da: til almashsa nomlar (Accept-Language) qayta olinadi.
const fetchOrders = async (locale: Locale): Promise<PurchaseOrder[]> => buildMockOrders(locale)

export const purchaseOrdersQuery = (locale: Locale) =>
  queryOptions({
    queryKey: ['purchase-orders', locale],
    queryFn: () => fetchOrders(locale),
  })

export const purchaseOrderQuery = (id: string, locale: Locale) =>
  queryOptions({
    queryKey: ['purchase-orders', locale, id],
    queryFn: async () => {
      const found = (await fetchOrders(locale)).find((po) => po.id === id)
      if (!found) throw new Error(`Purchase order not found: ${id}`)
      return found
    },
  })
