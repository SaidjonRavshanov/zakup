import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { CloudOff, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ORDERS_KEY, OrderRow, purchaseOrdersQuery, type PurchaseOrderStatus } from '@/entities/purchase-order'
import { EXPORT_STATUS_TONE, RECEIPTS_KEY, RECEIPT_STATUS_TONE, receiptsQuery } from '@/entities/receipt'
import { useI18n } from '@/shared/i18n'
import { discardReceipt, onReceiptSent, usePendingReceipts } from '@/shared/offline/outbox'
import { EmptyState, ListRow, MoneyText, PageHeader, SegmentedControl, Skeleton, StatusBadge } from '@/shared/ui'

/** Tovar kelishi mumkin bo'lgan buyurtmalar (javob kelmagan bo'lsa ham). */
const RECEIVABLE: ReadonlyArray<PurchaseOrderStatus> = ['SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED']
type Tab = 'toReceive' | 'done'

export default function ReceivingListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { t, fmt } = useI18n()
  const [tab, setTab] = useState<Tab>('toReceive')
  const pending = usePendingReceipts()
  const { data: orders = [], isPending } = useQuery(purchaseOrdersQuery())
  const { data: receipts = [] } = useQuery({ ...receiptsQuery, enabled: tab === 'done' })

  // Navbatdagi qabul yuborilganda — ro'yxatlar yangilanadi
  useEffect(
    () =>
      onReceiptSent(() => {
        void queryClient.invalidateQueries({ queryKey: ORDERS_KEY })
        void queryClient.invalidateQueries({ queryKey: RECEIPTS_KEY })
      }),
    [queryClient],
  )

  const queuedOrders = new Set(pending.map((p) => p.orderId))
  const toReceive = orders.filter((po) => RECEIVABLE.includes(po.status) && !queuedOrders.has(po.id))

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${t.modules.warehouse} · ${t.roles.storekeeper}`} title={t.receiving.title} />

      {pending.length > 0 && (
        <div className="mb-4 flex flex-col gap-2">
          {pending.map((item) => (
            <div key={item.id} className="flex items-center gap-3 rounded-row border border-dashed border-warning/50 px-4 py-3">
              <CloudOff size={18} className={item.error ? 'text-danger' : 'text-warning'} />
              <div className="min-w-0 flex-1">
                <div className="text-[14px] font-semibold">{item.orderNumber}</div>
                <div className={`text-[12px] ${item.error ? 'text-danger' : 'text-text-2'}`}>{item.error ?? t.receiving.queued}</div>
              </div>
              {item.error && (
                <button type="button" aria-label={t.receiving.discard} className="text-text-3" onClick={() => void discardReceipt(item.id)}>
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <SegmentedControl
        className="-mx-4 px-4"
        segments={(['toReceive', 'done'] as const).map((value) => ({
          value,
          label: t.receiving.tabs[value],
          count: value === 'toReceive' ? toReceive.length : undefined,
        }))}
        value={tab}
        onChange={setTab}
      />

      <div className="mt-4 flex flex-col gap-2">
        {tab === 'toReceive' ? (
          isPending ? (
            Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
          ) : toReceive.length === 0 ? (
            <EmptyState code={`00/${t.receiving.title}`} title={t.receiving.allReceived} description={t.receiving.noDeliveries} />
          ) : (
            toReceive.map((po) => (
              <OrderRow key={po.id} order={po} onClick={() => navigate({ to: '/receiving/$orderId', params: { orderId: po.id } })} />
            ))
          )
        ) : receipts.length === 0 ? (
          <EmptyState code="0" title={t.common.notFound} />
        ) : (
          receipts.map((receipt) => (
            <ListRow
              key={receipt.id}
              meta={`${receipt.number} · ${receipt.store_name ?? '—'} · ${fmt.date(receipt.received_at)}`}
              title={receipt.supplier_name ?? '—'}
              subtitle={receipt.export_status ? t.receiving.exportStatus[receipt.export_status] : undefined}
              badge={
                <StatusBadge tone={receipt.export_status === 'failed' ? EXPORT_STATUS_TONE.failed : RECEIPT_STATUS_TONE[receipt.status]}>
                  {t.receiving.status[receipt.status]}
                </StatusBadge>
              }
              trailing={<MoneyText value={Number(receipt.total)} className="text-[13px]" />}
              onClick={() => navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: receipt.id } })}
            />
          ))
        )}
      </div>
    </div>
  )
}
