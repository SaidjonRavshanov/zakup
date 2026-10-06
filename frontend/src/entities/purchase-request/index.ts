import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type { PurchaseOrderStatusKey, UnitCode } from '@/shared/i18n/keys'

export type RequestStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'PARTIALLY_APPROVED' | 'REJECTED' | 'CANCELLED' | 'SPLIT'
export type RequestType = 'manual' | 'event' | 'auto'
export type LineDecision = 'pending' | 'approved' | 'rejected'
export type Decision = 'approved' | 'partial' | 'returned' | 'rejected'

/** Pul / miqdor — backend'dan satr (Decimal); ko'rsatishda Number(). */
type DecimalString = string

export interface RequestListItem {
  id: string
  number: string
  store_id: string
  store_name: string | null
  type: RequestType
  status: RequestStatus
  needed_by: string
  initiator_id: string
  total: DecimalString
  lines_count: number
  created_at: string
}

export interface RequestLine {
  id: string
  product_id: string
  product_name: string
  base_unit: UnitCode
  qty: DecimalString
  note: string | null
  offer_id: string | null
  supplier_id: string | null
  supplier_name: string | null
  price_per_base: DecimalString | null
  amount: DecimalString
  decision: LineDecision
  qty_suggested: DecimalString | null
  calc: AutoCalc | null
}

/** Avto-zayavka: "nega shuncha" (backend `calc`, qiymatlar — matn ko'rinishidagi sonlar). */
export interface AutoCalc {
  avg_daily: string
  window_days: string
  days_observed: string
  stock: string | null
  stock_at: string | null
  in_transit: string
  lead_days: string
  coverage_days: string
  safety_stock: string
  seasonal_factor: string
  target: string
  reorder_point: string
  need: string
  packs: string
  pack_unit: string | null
  pack_factor: string
  trigger: 'reorder_point' | 'order_day' | null
}

export type AutoSkipReason = 'already_today' | 'in_open_request' | 'no_offer' | 'no_history' | 'enough_stock'

export interface AutoRunResult {
  request_ids: string[]
  lines: number
  skipped: Partial<Record<AutoSkipReason, number>>
}

export interface Approval {
  approver_id: string
  decision: Decision
  comment: string | null
  amount: DecimalString
  role_conflict: boolean
  decided_at: string
}

export interface RequestOrder {
  id: string
  number: string
  supplier_name: string | null
  status: PurchaseOrderStatusKey
  total: DecimalString
}

export interface RequestDetail extends Omit<RequestListItem, 'lines_count'> {
  comment: string | null
  lines: RequestLine[]
  approvals: Approval[]
  orders: RequestOrder[]
}

export type RequestFilter = 'active' | 'pending' | 'done' | 'all'

export const REQUEST_FILTERS: Record<RequestFilter, ReadonlyArray<RequestStatus> | null> = {
  active: ['DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'PARTIALLY_APPROVED'],
  pending: ['PENDING_APPROVAL'],
  done: ['SPLIT', 'REJECTED', 'CANCELLED'],
  all: null,
}

export const REQUESTS_KEY = ['purchase-requests'] as const

export const requestsQuery = queryOptions({
  queryKey: [...REQUESTS_KEY, 'list'],
  queryFn: ({ signal }) => apiRequest<RequestListItem[]>('/procurement/requests?limit=200', { signal }),
})

export const requestQuery = (id: string) =>
  queryOptions({
    queryKey: [...REQUESTS_KEY, id],
    queryFn: ({ signal }) => apiRequest<RequestDetail>(`/procurement/requests/${id}`, { signal }),
  })

const base = (id: string) => `/procurement/requests/${id}`

export const requestsApi = {
  create: (body: { store_id: string; needed_by: string; type: RequestType; comment: string | null }) =>
    apiRequest<{ id: string }>('/procurement/requests', { method: 'POST', body }),
  revise: (id: string, body: { needed_by: string; comment: string | null }) =>
    apiRequest<void>(base(id), { method: 'PATCH', body }),
  addLine: (id: string, body: { product_id: string; qty: string; note: string | null }) =>
    apiRequest<{ id: string }>(`${base(id)}/lines`, { method: 'POST', body }),
  runAuto: (body: { store_id?: string; force?: boolean } = {}) =>
    apiRequest<AutoRunResult>('/procurement/auto-requests', { method: 'POST', body }),
  changeLine: (id: string, lineId: string, body: { qty: string; note: string | null }) =>
    apiRequest<void>(`${base(id)}/lines/${lineId}`, { method: 'PATCH', body }),
  removeLine: (id: string, lineId: string) => apiRequest<void>(`${base(id)}/lines/${lineId}`, { method: 'DELETE' }),
  chooseOffer: (id: string, lineId: string, offerId: string | null) =>
    apiRequest<void>(`${base(id)}/lines/${lineId}/offer`, { method: 'PUT', body: { offer_id: offerId } }),
  submit: (id: string) => apiRequest<void>(`${base(id)}/submit`, { method: 'POST' }),
  approve: (id: string, lineIds: string[] | null) =>
    apiRequest<{ order_ids: string[] }>(`${base(id)}/approve`, { method: 'POST', body: { line_ids: lineIds } }),
  returnBack: (id: string, comment: string) => apiRequest<void>(`${base(id)}/return`, { method: 'POST', body: { comment } }),
  reject: (id: string, comment: string) => apiRequest<void>(`${base(id)}/reject`, { method: 'POST', body: { comment } }),
  cancel: (id: string) => apiRequest<void>(`${base(id)}/cancel`, { method: 'POST' }),
}

export { WhyQuantity } from './WhyQuantity'
