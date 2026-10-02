import type { PurchaseOrderStatusKey, UnitCode } from '@/shared/i18n/keys'
import type { Tone } from '@/shared/ui'

/** Backend status mashinasi bilan bir xil (docs/ARCHITECTURE.md §5). */
export type PurchaseOrderStatus = PurchaseOrderStatusKey

export interface PurchaseOrderLine {
  id: string
  productName: string
  unit: UnitCode
  qtyOrdered: number
  priceOrdered: number
}

export interface PurchaseOrder {
  id: string
  number: string
  supplierName: string
  storeName: string
  status: PurchaseOrderStatus
  deliveryDate: string
  totalAmount: number
  lines: PurchaseOrderLine[]
}

/** Status rangi. Matn — lug'atda: `t.poStatus[status]`. */
export const PO_STATUS_TONE: Record<PurchaseOrderStatus, Tone> = {
  CREATED: 'neutral',
  SENT: 'info',
  CONFIRMED: 'accent',
  PARTIALLY_CONFIRMED: 'warning',
  REAPPROVAL: 'warning',
  RECEIVING: 'info',
  RECEIVED: 'accent',
  PARTIALLY_RECEIVED: 'warning',
  CLOSED: 'neutral',
  CANCELLED: 'danger',
}

export type OrderFilter = 'all' | 'awaiting' | 'in_transit' | 'done'

export const ORDER_FILTERS: Record<OrderFilter, ReadonlyArray<PurchaseOrderStatus> | null> = {
  all: null,
  awaiting: ['CREATED', 'SENT', 'REAPPROVAL'],
  in_transit: ['CONFIRMED', 'PARTIALLY_CONFIRMED', 'RECEIVING'],
  done: ['RECEIVED', 'PARTIALLY_RECEIVED', 'CLOSED', 'CANCELLED'],
}

export const orderTotal = (lines: ReadonlyArray<PurchaseOrderLine>): number =>
  lines.reduce((sum, line) => sum + line.qtyOrdered * line.priceOrdered, 0)
