import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type { Tone } from '@/shared/kit'

export type ObligationStatus = 'OPEN' | 'PARTIALLY_PAID' | 'PAID' | 'BLOCKED'
export type PaymentStatus = 'SUBMITTED' | 'APPROVED' | 'PAID' | 'REJECTED' | 'CANCELLED'
export type PaymentMethod = 'cash' | 'transfer'

type DecimalString = string

export interface SupplierBalance {
  supplier_id: string
  supplier_name: string | null
  debt: DecimalString
  blocked: DecimalString
  overdue: DecimalString
  reserved: DecimalString
  credit_limit: DecimalString | null
  free_limit: DecimalString | null
  nearest_due: string | null
  open_count: number
}

export interface Obligation {
  id: string
  receipt_id: string
  receipt_number: string
  store_id: string
  store_name: string | null
  amount: DecimalString
  paid: DecimalString
  outstanding: DecimalString
  reserved: DecimalString
  received_on: string
  due_date: string
  status: ObligationStatus
  overdue: boolean
}

export interface SupplierAccount {
  balance: SupplierBalance
  obligations: Obligation[]
}

export interface PaymentListItem {
  id: string
  number: string
  supplier_id: string
  supplier_name: string | null
  method: PaymentMethod
  status: PaymentStatus
  total: DecimalString
  requested_at: string
  paid_at: string | null
}

export interface PaymentDetail extends PaymentListItem {
  requested_by: string
  comment: string | null
  approved_by: string | null
  approved_at: string | null
  decision_comment: string | null
  paid_by: string | null
  proof_id: string | null
  lines: Array<{
    obligation_id: string
    receipt_id: string
    receipt_number: string
    amount: DecimalString
    outstanding: DecimalString
  }>
}

export interface NewPayment {
  supplier_id: string
  method: PaymentMethod
  comment?: string
  lines: Array<{ obligation_id: string; amount: string }>
}

export const OBLIGATION_TONE: Record<ObligationStatus, Tone> = {
  OPEN: 'neutral',
  PARTIALLY_PAID: 'accent',
  PAID: 'ok',
  BLOCKED: 'warn',
}

export const PAYMENT_TONE: Record<PaymentStatus, Tone> = {
  SUBMITTED: 'accent',
  APPROVED: 'solid',
  PAID: 'ok',
  REJECTED: 'danger',
  CANCELLED: 'neutral',
}

export const FINANCE_KEY = ['finance'] as const

export const balancesQuery = queryOptions({
  queryKey: [...FINANCE_KEY, 'balances'],
  queryFn: ({ signal }) => apiRequest<SupplierBalance[]>('/finance/suppliers', { signal }),
})

export const supplierAccountQuery = (supplierId: string) =>
  queryOptions({
    queryKey: [...FINANCE_KEY, 'supplier', supplierId],
    queryFn: ({ signal }) => apiRequest<SupplierAccount>(`/finance/suppliers/${supplierId}`, { signal }),
  })

export const paymentsQuery = (supplierId?: string) =>
  queryOptions({
    queryKey: [...FINANCE_KEY, 'payments', supplierId ?? 'all'],
    queryFn: ({ signal }) =>
      apiRequest<PaymentListItem[]>(`/finance/payments${supplierId ? `?supplier_id=${supplierId}` : ''}`, { signal }),
  })

export const paymentQuery = (id: string) =>
  queryOptions({
    queryKey: [...FINANCE_KEY, 'payment', id],
    queryFn: ({ signal }) => apiRequest<PaymentDetail>(`/finance/payments/${id}`, { signal }),
  })

export const paymentsApi = {
  create: (body: NewPayment) => apiRequest<{ id: string }>('/finance/payments', { method: 'POST', body }),
  approve: (id: string) => apiRequest<void>(`/finance/payments/${id}/approve`, { method: 'POST' }),
  reject: (id: string, comment: string) =>
    apiRequest<void>(`/finance/payments/${id}/reject`, { method: 'POST', body: { comment } }),
  cancel: (id: string) => apiRequest<void>(`/finance/payments/${id}/cancel`, { method: 'POST' }),
  pay: (id: string, proofId: string | null) =>
    apiRequest<void>(`/finance/payments/${id}/pay`, { method: 'POST', body: { proof_id: proofId } }),
}
