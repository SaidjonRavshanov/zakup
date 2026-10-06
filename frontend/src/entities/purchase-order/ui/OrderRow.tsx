import { useZk } from '@/shared/i18n/use-zk'
import { Row, Tag, status } from '@/shared/kit'
import type { PurchaseOrder } from '../model'

/** Buyurtma qatori (prototip poRow): PO · ombor · sana / yetkazuvchi / pozitsiyalar, summa + holat. */
export function OrderRow({ order, onClick }: { order: PurchaseOrder; onClick?: () => void }) {
  const { z, f } = useZk()
  const s = status(z, 'order', order.status)
  return (
    <Row
      meta={`${order.number} · ${order.storeName} · ${f.dt(order.deliveryDate)}`}
      title={order.supplierName}
      sub={`${order.linesCount} ${z.pos_short}`}
      amount={f.money(order.totalAmount)}
      badge={<Tag tone={s.tone}>{s.label}</Tag>}
      onClick={onClick}
    />
  )
}
