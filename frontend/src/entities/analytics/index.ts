import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type { UnitCode } from '@/shared/i18n/keys'

type DecimalString = string

export interface PeriodDto {
  date_from: string
  date_to: string
}

export interface Summary {
  period: PeriodDto
  purchases: DecimalString
  purchases_prev: DecimalString
  receipts: number
  savings: DecimalString
  overpay: DecimalString
  defect_loss: DecimalString
  price_change_pct: DecimalString | null
  pending_requests: number
  auto_drafts: number
  orders_in_transit: number
  arriving_today: number
  open_disputes: number
  debt: DecimalString
  overdue: DecimalString
}

export interface SupplierRating {
  supplier_id: string
  supplier_name: string
  orders: number
  receipts: number
  amount: DecimalString
  short_rate: DecimalString
  defect_rate: DecimalString
  price_rate: DecimalString
  on_time_rate: DecimalString
  response_hours: DecimalString | null
  score: DecimalString | null
}

export interface ProductPrice {
  product_id: string
  product_name: string
  base_unit: UnitCode
  qty: DecimalString
  amount: DecimalString
  avg_price: DecimalString
  prev_avg_price: DecimalString | null
  change_pct: DecimalString | null
  best_price: DecimalString | null
  best_supplier: string | null
  overpay: DecimalString
}

export interface PricePoint {
  day: string
  supplier_name: string
  price: DecimalString
  source: 'offer' | 'receipt'
}

export interface StockItem {
  store_id: string
  store_name: string
  product_id: string
  product_name: string
  base_unit: UnitCode
  qty: DecimalString
  value: DecimalString
  avg_daily: DecimalString
  days_cover: DecimalString | null
  dead: boolean
}

export interface StockOverview {
  total_value: DecimalString
  dead_value: DecimalString
  items: StockItem[]
}

export type ControlKind = 'price_change' | 'discrepancy' | 'role_conflict' | 'manual_increase' | 'payment_without_proof'

export interface ControlItem {
  kind: ControlKind
  entity_id: string
  number: string
  title: string
  detail: string
  amount: DecimalString | null
  at: string
}

interface Report<T> {
  period: PeriodDto
  items: T[]
}

export const ANALYTICS_KEY = ['analytics'] as const

export const summaryQuery = queryOptions({
  queryKey: [...ANALYTICS_KEY, 'summary'],
  queryFn: ({ signal }) => apiRequest<Summary>('/analytics/summary', { signal }),
  staleTime: 60_000,
})

export const supplierRatingQuery = queryOptions({
  queryKey: [...ANALYTICS_KEY, 'suppliers'],
  queryFn: ({ signal }) => apiRequest<Report<SupplierRating>>('/analytics/suppliers', { signal }),
})

export const pricesQuery = queryOptions({
  queryKey: [...ANALYTICS_KEY, 'prices'],
  queryFn: ({ signal }) => apiRequest<Report<ProductPrice>>('/analytics/prices', { signal }),
})

export const priceHistoryQuery = (productId: string) =>
  queryOptions({
    queryKey: [...ANALYTICS_KEY, 'price', productId],
    queryFn: ({ signal }) => apiRequest<PricePoint[]>(`/analytics/prices/${productId}`, { signal }),
  })

export const stockQuery = queryOptions({
  queryKey: [...ANALYTICS_KEY, 'stock'],
  queryFn: ({ signal }) => apiRequest<StockOverview>('/analytics/stock', { signal }),
})

export const controlQuery = queryOptions({
  queryKey: [...ANALYTICS_KEY, 'control'],
  queryFn: ({ signal }) => apiRequest<Report<ControlItem>>('/analytics/control', { signal }),
})

/** % (bitta kasr) — ulush 0..1 dan. */
export const pct = (share: DecimalString | number) => Math.round(Number(share) * 1000) / 10
