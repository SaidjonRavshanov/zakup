/** Hujjat qayerda: Заявка → Согласование → Заказ → Поставщик → Приёмка + "hozir / keyin" izohi. */
import type { RequestDetail } from '@/entities/purchase-request'
import type { PurchaseOrderStatus } from '@/entities/purchase-order'
import { fill, type Zk, type ZkKey } from '@/shared/i18n/use-zk'

export const STEPS: ZkKey[] = ['fl_request', 'fl_approval', 'fl_order', 'fl_supplier', 'fl_receiving']

type Mark = 'ok' | 'warn' | 'stop'

export interface Flow {
  /** Joriy bosqich (0..4); 5 — hammasi tugagan. */
  at: number
  mark: Mark
  hint: string
}

// Buyurtma holati → bosqich (zayavka sahifasida eng ilg'or buyurtma ham shu bilan)
const ORDER_AT: Record<PurchaseOrderStatus, number> = {
  CREATED: 2,
  SENT: 3,
  REAPPROVAL: 3,
  CONFIRMED: 4,
  PARTIALLY_CONFIRMED: 4,
  RECEIVED: 5,
  PARTIALLY_RECEIVED: 5,
  CANCELLED: 2,
}

export function orderFlow(z: Zk, status: PurchaseOrderStatus): Flow {
  const at = ORDER_AT[status]
  if (status === 'CANCELLED') return { at, mark: 'stop', hint: z.fl_po_cancelled }
  if (status === 'REAPPROVAL') return { at, mark: 'warn', hint: z.fl_po_reapproval }
  const hint: Record<PurchaseOrderStatus, ZkKey> = {
    CREATED: 'fl_po_created',
    SENT: 'fl_po_sent',
    REAPPROVAL: 'fl_po_reapproval',
    CONFIRMED: 'fl_po_confirmed',
    PARTIALLY_CONFIRMED: 'fl_po_partial',
    RECEIVED: 'fl_po_received',
    PARTIALLY_RECEIVED: 'fl_po_received',
    CANCELLED: 'fl_po_cancelled',
  }
  return { at, mark: 'ok', hint: z[hint[status]] }
}

export function requestFlow(z: Zk, request: RequestDetail): Flow {
  switch (request.status) {
    case 'DRAFT':
      return { at: 0, mark: 'ok', hint: z.fl_rq_draft }
    case 'CANCELLED':
      return { at: 0, mark: 'stop', hint: z.fl_rq_cancelled }
    case 'PENDING_APPROVAL':
      return { at: 1, mark: 'ok', hint: z.fl_rq_pending }
    case 'REJECTED':
      return { at: 1, mark: 'stop', hint: z.fl_rq_rejected }
    default: {
      const live = request.orders.filter((o) => o.status !== 'CANCELLED')
      const at = live.length ? Math.max(...live.map((o) => ORDER_AT[o.status])) : 2
      return { at, mark: 'ok', hint: fill(z.fl_rq_split, { n: String(request.orders.length) }) }
    }
  }
}
