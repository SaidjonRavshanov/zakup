import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useDeferredValue, useMemo, useState } from 'react'
import { ORDER_FILTERS, OrderRow, purchaseOrdersQuery, type OrderFilter } from '@/entities/purchase-order'
import { useI18n } from '@/shared/i18n'
import { EmptyState, PageHeader, SearchPill, SegmentedControl, Skeleton } from '@/shared/ui'

const FILTER_KEYS = Object.keys(ORDER_FILTERS) as OrderFilter[]

export default function OrdersPage() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: orders = [], isPending } = useQuery(purchaseOrdersQuery())
  const [filter, setFilter] = useState<OrderFilter>('all')
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim().toLowerCase())

  const segments = useMemo(
    () =>
      FILTER_KEYS.map((key) => {
        const statuses = ORDER_FILTERS[key]
        return {
          value: key,
          label: t.orders.filters[key],
          count: statuses ? orders.filter((po) => statuses.includes(po.status)).length : orders.length,
        }
      }),
    [orders, t],
  )

  const visible = useMemo(() => {
    const statuses = ORDER_FILTERS[filter]
    return orders.filter(
      (po) =>
        (!statuses || statuses.includes(po.status)) &&
        (!query || po.supplierName.toLowerCase().includes(query) || po.number.toLowerCase().includes(query)),
    )
  }, [orders, filter, query])

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${t.modules.procurement} · PO`} title={t.orders.title} />
      <SearchPill placeholder={t.orders.searchPlaceholder} value={search} onChange={(e) => setSearch(e.target.value)} />
      <SegmentedControl className="-mx-4 mt-3 px-4" segments={segments} value={filter} onChange={setFilter} />

      <div className="mt-4 flex flex-col gap-2">
        {isPending ? (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
        ) : visible.length === 0 ? (
          <EmptyState code="404" title={t.common.notFound} description={t.orders.emptyHint} />
        ) : (
          visible.map((po) => (
            <OrderRow key={po.id} order={po} onClick={() => navigate({ to: '/orders/$orderId', params: { orderId: po.id } })} />
          ))
        )}
      </div>
    </div>
  )
}
