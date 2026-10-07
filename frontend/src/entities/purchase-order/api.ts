import { queryOptions } from '@tanstack/react-query'
import { apiRequest } from '@/shared/api/client'
import type { UnitCode } from '@/shared/i18n/keys'
import type {
  Channel,
  PurchaseOrder,
  PurchaseOrderDetail,
  PurchaseOrderLine,
  PurchaseOrderStatus,
  ResponseKind,
} from './model'

// ---------------------------------------------------------------- backend DTO (Decimal → satr)

interface OrderListDto {
  id: string
  number: string
  request_id: string | null
  supplier_id: string
  supplier_name: string | null
  store_id: string
  store_name: string | null
  delivery_date: string
  status: PurchaseOrderStatus
  total: string
  confirmed_total: string
  lines_count: number
  sent_at: string | null
  response_deadline: string | null
}

interface OrderLineDto {
  id: string
  product_name: string
  base_unit: UnitCode
  pack_unit: UnitCode
  pack_factor: string
  qty_packs: string
  price_per_pack: string
  amount: string
  response: ResponseKind | null
  qty_confirmed: string | null
  price_confirmed: string | null
  needs_reapproval: boolean
}

interface OrderDetailDto extends Omit<OrderListDto, 'lines_count'> {
  lines: OrderLineDto[]
  supplier_phone: string | null
  supplier_telegram: string | null
  min_order_amount: string
  sent_channel: Channel | null
  responded_at: string | null
  cancel_reason: string | null
  warnings: string[]
}

const num = (value: string | null): number | null => (value === null ? null : Number(value))

const toOrder = (dto: OrderListDto): PurchaseOrder => ({
  id: dto.id,
  number: dto.number,
  requestId: dto.request_id,
  supplierId: dto.supplier_id,
  supplierName: dto.supplier_name ?? '—',
  storeId: dto.store_id,
  storeName: dto.store_name ?? '—',
  status: dto.status,
  deliveryDate: dto.delivery_date,
  totalAmount: Number(dto.total),
  confirmedTotal: Number(dto.confirmed_total),
  linesCount: dto.lines_count,
  sentAt: dto.sent_at,
  responseDeadline: dto.response_deadline,
})

export const toOrderLine = (dto: OrderLineDto): PurchaseOrderLine => ({
  id: dto.id,
  productName: dto.product_name,
  baseUnit: dto.base_unit,
  unit: dto.pack_unit,
  packFactor: Number(dto.pack_factor),
  qtyOrdered: Number(dto.qty_packs),
  priceOrdered: Number(dto.price_per_pack),
  amount: Number(dto.amount),
  response: dto.response,
  qtyConfirmed: num(dto.qty_confirmed),
  priceConfirmed: num(dto.price_confirmed),
  needsReapproval: dto.needs_reapproval,
})

const toDetail = (dto: OrderDetailDto): PurchaseOrderDetail => ({
  ...toOrder({ ...dto, lines_count: dto.lines.length }),
  lines: dto.lines.map(toOrderLine),
  supplierPhone: dto.supplier_phone,
  supplierTelegram: dto.supplier_telegram,
  minOrderAmount: Number(dto.min_order_amount),
  sentChannel: dto.sent_channel,
  respondedAt: dto.responded_at,
  cancelReason: dto.cancel_reason,
  warnings: dto.warnings,
})

export const ORDERS_KEY = ['purchase-orders'] as const

/**
 * Buyurtmalar ro'yxati (eng yangi 200 tasi). `statuses` — server tomonda filtr (`?status=A&status=B`):
 * ish ro'yxatlari (qabul, vazifalar) eski buyurtmalar ko'p bo'lsa ham to'liq bo'lishi uchun.
 */
export const purchaseOrdersQuery = (statuses?: ReadonlyArray<PurchaseOrderStatus>) => {
  const filter = statuses?.length ? [...statuses].sort() : null
  const search = new URLSearchParams({ limit: '200' })
  for (const value of filter ?? []) search.append('status', value)
  return queryOptions({
    queryKey: [...ORDERS_KEY, 'list', filter?.join(',') ?? 'all'],
    queryFn: async ({ signal }) => (await apiRequest<OrderListDto[]>(`/procurement/orders?${search}`, { signal })).map(toOrder),
  })
}

/** Qabul qilinishi mumkin bo'lgan holatlar (backend RECEIVABLE bilan bir xil). */
export const RECEIVABLE_STATUSES: ReadonlyArray<PurchaseOrderStatus> = ['SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED']

/** Hali yopilmagan buyurtmalar (vazifalar, bugungi yetkazmalar). */
export const OPEN_STATUSES: ReadonlyArray<PurchaseOrderStatus> = ['CREATED', 'SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED', 'REAPPROVAL']

export const purchaseOrderQuery = (id: string) =>
  queryOptions({
    queryKey: [...ORDERS_KEY, id],
    queryFn: async ({ signal }) => toDetail(await apiRequest<OrderDetailDto>(`/procurement/orders/${id}`, { signal })),
  })

export interface LineResponseInput {
  line_id: string
  kind: ResponseKind
  qty_packs?: string
  price_per_pack?: string
}

export const ordersApi = {
  send: (id: string, channel: Channel) =>
    apiRequest<{ message: string; response_url: string }>(`/procurement/orders/${id}/send`, { method: 'POST', body: { channel } }),
  respond: (id: string, lines: LineResponseInput[]) =>
    apiRequest<{ status: PurchaseOrderStatus }>(`/procurement/orders/${id}/response`, { method: 'POST', body: { lines } }),
  approveChanges: (id: string) =>
    apiRequest<{ status: PurchaseOrderStatus }>(`/procurement/orders/${id}/approve-changes`, { method: 'POST' }),
  cancel: (id: string, reason: string) =>
    apiRequest<void>(`/procurement/orders/${id}/cancel`, { method: 'POST', body: { reason } }),
}
