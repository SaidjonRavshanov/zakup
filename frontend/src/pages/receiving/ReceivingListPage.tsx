import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ORDER_FILTERS, OrderRow, purchaseOrdersQuery } from '@/entities/purchase-order'
import { useI18n } from '@/shared/i18n'
import { EmptyState, PageHeader, Skeleton } from '@/shared/ui'

export default function ReceivingListPage() {
  const navigate = useNavigate()
  const { t, locale } = useI18n()
  const { data: orders = [], isPending } = useQuery(purchaseOrdersQuery(locale))
  const toReceive = orders.filter((po) => ORDER_FILTERS.in_transit?.includes(po.status))

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${t.modules.warehouse} · ${t.roles.storekeeper}`} title={t.receiving.title} />
      <div className="flex flex-col gap-2">
        {isPending ? (
          Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
        ) : toReceive.length === 0 ? (
          <EmptyState code={`00/${t.receiving.title}`} title={t.receiving.allReceived} description={t.receiving.noDeliveries} />
        ) : (
          toReceive.map((po) => (
            <OrderRow key={po.id} order={po} onClick={() => navigate({ to: '/receiving/$orderId', params: { orderId: po.id } })} />
          ))
        )}
      </div>
    </div>
  )
}
