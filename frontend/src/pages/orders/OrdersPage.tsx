import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useDeferredValue, useState } from 'react'
import { ORDER_FILTERS, OrderRow, purchaseOrdersQuery, type OrderFilter } from '@/entities/purchase-order'
import { useZk } from '@/shared/i18n/use-zk'
import { Empty, PageHead, RowsSkeleton, SearchInput, Seg } from '@/shared/kit'

const FILTER_KEYS = Object.keys(ORDER_FILTERS) as OrderFilter[]

export default function OrdersPage() {
  const navigate = useNavigate()
  const { z } = useZk()
  const { data: orders = [], isPending } = useQuery(purchaseOrdersQuery())
  const [filter, setFilter] = useState<OrderFilter>('all')
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim().toLowerCase())

  const label: Record<OrderFilter, string> = { all: z.f_all, awaiting: z.f_wait, in_transit: z.f_transit, done: z.f_done }
  const options = FILTER_KEYS.map((key) => {
    const statuses = ORDER_FILTERS[key]
    return {
      value: key,
      label: label[key],
      count: statuses ? orders.filter((po) => statuses.includes(po.status)).length : orders.length,
    }
  })

  const statuses = ORDER_FILTERS[filter]
  const visible = orders.filter(
    (po) =>
      (!statuses || statuses.includes(po.status)) &&
      (!query || po.supplierName.toLowerCase().includes(query) || po.number.toLowerCase().includes(query)),
  )

  return (
    <div className="mx-auto max-w-[1040px]">
      <PageHead title={z.orders} />
      <SearchInput className="mt-3" value={search} onChange={setSearch} placeholder={z.search_po} />
      <Seg scroll className="mt-3" options={options} value={filter} onChange={setFilter} />
      {isPending ? (
        <RowsSkeleton n={5} />
      ) : visible.length === 0 ? (
        <Empty title={z.empty_po} hint={z.empty_po_hint} />
      ) : (
        visible.map((po) => (
          <OrderRow key={po.id} order={po} onClick={() => navigate({ to: '/orders/$orderId', params: { orderId: po.id } })} />
        ))
      )}
    </div>
  )
}
