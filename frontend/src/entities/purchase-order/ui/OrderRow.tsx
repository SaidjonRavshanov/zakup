import { useI18n } from '@/shared/i18n'
import { ListRow, MoneyText, StatusBadge } from '@/shared/ui'
import { PO_STATUS_TONE, type PurchaseOrder } from '../model'

export function OrderRow({ order, onClick }: { order: PurchaseOrder; onClick?: () => void }) {
  const { t, fmt } = useI18n()
  return (
    <ListRow
      meta={`${order.number} · ${order.storeName} · ${fmt.date(order.deliveryDate)}`}
      title={order.supplierName}
      subtitle={t.orders.positions(order.linesCount)}
      badge={<StatusBadge tone={PO_STATUS_TONE[order.status]}>{t.poStatus[order.status]}</StatusBadge>}
      trailing={<MoneyText value={order.totalAmount} className="text-[13px]" />}
      onClick={onClick}
    />
  )
}
