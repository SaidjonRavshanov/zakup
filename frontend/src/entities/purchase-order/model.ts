import type { PurchaseOrderStatusKey, UnitCode } from '@/shared/i18n/keys'

/** Backend status mashinasi bilan bir xil (docs/ARCHITECTURE.md §5). */
export type PurchaseOrderStatus = PurchaseOrderStatusKey

export type ResponseKind = 'confirmed' | 'price_changed' | 'qty_changed' | 'out_of_stock'
export type Channel = 'telegram' | 'whatsapp' | 'phone' | 'email' | 'other'

export const CHANNELS: ReadonlyArray<Channel> = ['telegram', 'whatsapp', 'phone', 'email', 'other']
export const RESPONSE_KINDS: ReadonlyArray<ResponseKind> = ['confirmed', 'price_changed', 'qty_changed', 'out_of_stock']

/** Ro'yxat qatori. Pul — ko'rsatish uchun son (hisob-kitob backend'da). */
export interface PurchaseOrder {
  id: string
  number: string
  requestId: string | null
  supplierId: string
  supplierName: string
  storeId: string
  storeName: string
  status: PurchaseOrderStatus
  deliveryDate: string
  totalAmount: number
  confirmedTotal: number
  linesCount: number
  sentAt: string | null
  responseDeadline: string | null
}

/** Pozitsiya yetkazuvchi qadog'ida: `unit` — qadoq birligi (qop), `packFactor` — undagi bazaviy miqdor. */
export interface PurchaseOrderLine {
  id: string
  productName: string
  baseUnit: UnitCode
  unit: UnitCode
  packFactor: number
  qtyOrdered: number
  priceOrdered: number
  amount: number
  response: ResponseKind | null
  qtyConfirmed: number | null
  priceConfirmed: number | null
  needsReapproval: boolean
}

export interface PurchaseOrderDetail extends Omit<PurchaseOrder, 'linesCount'> {
  lines: PurchaseOrderLine[]
  supplierPhone: string | null
  supplierTelegram: string | null
  minOrderAmount: number
  sentChannel: Channel | null
  respondedAt: string | null
  cancelReason: string | null
  warnings: string[]
}

export type OrderFilter = 'all' | 'awaiting' | 'in_transit' | 'done'

export const ORDER_FILTERS: Record<OrderFilter, ReadonlyArray<PurchaseOrderStatus> | null> = {
  all: null,
  awaiting: ['CREATED', 'SENT'],
  in_transit: ['CONFIRMED', 'PARTIALLY_CONFIRMED', 'REAPPROVAL', 'RECEIVING'],
  done: ['RECEIVED', 'PARTIALLY_RECEIVED', 'CLOSED', 'CANCELLED'],
}
