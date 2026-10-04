import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type { UnitCode } from '@/shared/i18n/keys'
import type { Tone } from '@/shared/ui'

export type ReceiptStatus = 'ACCEPTED' | 'DISPUTED'
export type DiscrepancyKind = 'qty_over' | 'qty_under' | 'short' | 'price_up' | 'price_down' | 'defect'
export type Resolution = 'accepted' | 'return' | 'discount' | 'replacement'
export type PaymentMethod = 'cash' | 'transfer'
export type ExportStatus = 'pending' | 'exported' | 'failed'

export const RESOLUTIONS: ReadonlyArray<Resolution> = ['accepted', 'return', 'discount', 'replacement']

type DecimalString = string

export interface ExpectedLine {
  order_line_id: string
  product_id: string
  product_name: string
  base_unit: UnitCode
  qty: DecimalString
  price: DecimalString
}

export interface ExpectedOrder {
  order_id: string
  number: string
  store_id: string
  supplier_id: string
  lines: ExpectedLine[]
}

export interface ReceiptListItem {
  id: string
  number: string
  order_id: string
  store_name: string | null
  supplier_name: string | null
  status: ReceiptStatus
  total: DecimalString
  expected_total: DecimalString
  received_at: string
  dispute_open: boolean
  export_status: ExportStatus | null
}

export interface ReceiptLine {
  id: string
  product_name: string
  base_unit: UnitCode
  qty_expected: DecimalString
  price_expected: DecimalString
  qty_fact: DecimalString
  price_fact: DecimalString
  qty_defect: DecimalString
  defect_reason: string | null
  amount: DecimalString
}

export interface Discrepancy {
  line_id: string
  kind: DiscrepancyKind
  expected: DecimalString
  actual: DecimalString
  within_tolerance: boolean
}

export interface ReceiptDetail extends ReceiptListItem {
  supplier_invoice_no: string | null
  payment_method: PaymentMethod | null
  invoice_photo_id: string
  comment: string | null
  lines: ReceiptLine[]
  discrepancies: Discrepancy[]
  dispute: {
    opened_at: string
    resolution: Resolution | null
    comment: string | null
    resolved_at: string | null
  } | null
  export_error: string | null
  iiko_document_number: string | null
}

export const RECEIPT_STATUS_TONE: Record<ReceiptStatus, Tone> = { ACCEPTED: 'accent', DISPUTED: 'warning' }
export const EXPORT_STATUS_TONE: Record<ExportStatus, Tone> = { pending: 'info', exported: 'accent', failed: 'danger' }

export const RECEIPTS_KEY = ['receipts'] as const

export const expectedOrderQuery = (orderId: string) =>
  queryOptions({
    queryKey: [...RECEIPTS_KEY, 'expected', orderId],
    queryFn: ({ signal }) => apiRequest<ExpectedOrder>(`/receiving/orders/${orderId}/expected`, { signal }),
    // Omborda internet uzilsa — ochilgan buyurtma ekrani yo'qolmasin
    staleTime: 10 * 60_000,
    gcTime: 24 * 60 * 60_000,
  })

export const receiptsQuery = queryOptions({
  queryKey: [...RECEIPTS_KEY, 'list'],
  queryFn: ({ signal }) => apiRequest<ReceiptListItem[]>('/receiving/receipts?limit=100', { signal }),
})

export const receiptQuery = (id: string) =>
  queryOptions({
    queryKey: [...RECEIPTS_KEY, id],
    queryFn: ({ signal }) => apiRequest<ReceiptDetail>(`/receiving/receipts/${id}`, { signal }),
  })

export const resolveDispute = (id: string, resolution: Resolution, comment: string) =>
  apiRequest<void>(`/receiving/receipts/${id}/resolve`, { method: 'POST', body: { resolution, comment } })
