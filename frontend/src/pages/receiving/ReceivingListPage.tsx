import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Clock, WifiOff } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ORDERS_KEY, purchaseOrdersQuery, type PurchaseOrderStatus } from '@/entities/purchase-order'
import { RECEIPTS_KEY, receiptsQuery } from '@/entities/receipt'
import { useZk } from '@/shared/i18n/use-zk'
import { Blueprint, Btn, Empty, Row, RowsSkeleton, Seg, Tag, confirmAction, status, toast } from '@/shared/kit'
import { discardReceipt, flush, onReceiptSent, retryReceipt, usePendingReceipts } from '@/shared/offline/outbox'
import { useOnline } from './use-online'

/** Tovar kelishi mumkin bo'lgan buyurtmalar (javob kelmagan bo'lsa ham). */
const RECEIVABLE: ReadonlyArray<PurchaseOrderStatus> = ['SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED']
type Tab = 'exp' | 'acc'

export default function ReceivingListPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { z, f } = useZk()
  const online = useOnline()
  const [tab, setTab] = useState<Tab>('exp')
  const pending = usePendingReceipts()
  const { data: orders = [], isPending } = useQuery(purchaseOrdersQuery())
  const { data: receipts = [], isPending: receiptsPending } = useQuery(receiptsQuery)

  // Navbatdagi qabul yuborilganda — ro'yxatlar yangilanadi
  useEffect(
    () =>
      onReceiptSent(() => {
        toast(z.toast_synced)
        void queryClient.invalidateQueries({ queryKey: ORDERS_KEY })
        void queryClient.invalidateQueries({ queryKey: RECEIPTS_KEY })
      }),
    [queryClient, z],
  )

  const queuedOrders = new Set(pending.map((p) => p.orderId))
  const toReceive = orders.filter((po) => RECEIVABLE.includes(po.status) && !queuedOrders.has(po.id))
  const supplierOf = (orderId: string) => orders.find((o) => o.id === orderId)?.supplierName

  const discard = async (id: string) => {
    if (await confirmAction({ title: z.cf_del_queue, body: z.cf_del_queue_body, label: z.a_delete, cancel: z.cancel, danger: true }))
      await discardReceipt(id)
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-3 pt-2">
        <h1 className="m-0 text-[34px]">{z.receiving}</h1>
        {!online && (
          <span className="flex items-center gap-1.5 text-[14px] text-warn">
            <WifiOff size={20} />
            {z.offline}
          </span>
        )}
      </div>

      {pending.length > 0 && (
        <Blueprint className="mt-4 px-3.5 py-1">
          <div className="flex items-center justify-between gap-3 pb-1 pt-2.5">
            <span className="text-[13px] font-medium text-n7">{z.queue}</span>
            {online && pending.some((p) => !p.error) && (
              <Btn variant="ghost" size="sm" onClick={() => void flush()}>
                {z.a_retry}
              </Btn>
            )}
          </div>
          {pending.map((item) => {
            const supplier = supplierOf(item.orderId)
            return (
              <div key={item.id} className="flex items-center gap-3 border-t border-line py-2.5">
                <div className="min-w-0 flex-1">
                  <div className="text-[15px] font-medium">{supplier ? `${item.orderNumber} · ${supplier}` : item.orderNumber}</div>
                  <div className={item.error ? 'break-words text-[13px] text-danger' : 'text-[13px] text-n7'}>
                    {item.error
                      ? `${z.q_rejected}: ${item.error}`
                      : `${z.q_wait} · ${f.time(new Date(item.createdAt).toISOString())}`}
                  </div>
                </div>
                {item.error ? (
                  <div className="flex shrink-0 flex-col gap-1.5">
                    {/* Server rad etgan: sabab tuzatilgan bo'lsa (buyurtma holati, narx) — qayta yuborish */}
                    <Btn size="sm" disabled={!online} onClick={() => void retryReceipt(item.id)}>
                      {z.a_resend}
                    </Btn>
                    <Btn size="sm" danger onClick={() => void discard(item.id)}>
                      {z.a_delete}
                    </Btn>
                  </div>
                ) : (
                  <Clock size={20} className="shrink-0 text-n7" />
                )}
              </div>
            )
          })}
        </Blueprint>
      )}

      <Seg
        className="mt-4"
        options={[
          { value: 'exp', label: z.t_expected, count: toReceive.length },
          { value: 'acc', label: z.t_accepted, count: receiptsPending ? undefined : receipts.length },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === 'exp' ? (
        isPending ? (
          <RowsSkeleton n={3} />
        ) : toReceive.length === 0 ? (
          <Empty title={z.all_received} hint={z.no_expected} />
        ) : (
          toReceive.map((po) => {
            const s = status(z, 'order', po.status)
            return (
              <Row
                key={po.id}
                meta={`${po.number} · ${po.storeName} · ${f.dt(po.deliveryDate)}`}
                title={po.supplierName}
                sub={`${po.linesCount} ${z.pos_short}`}
                amount={f.money(po.totalAmount)}
                badge={<Tag tone={s.tone}>{s.label}</Tag>}
                onClick={() => navigate({ to: '/receiving/$orderId', params: { orderId: po.id } })}
              />
            )
          })
        )
      ) : receiptsPending ? (
        <RowsSkeleton n={3} />
      ) : receipts.length === 0 ? (
        <Empty title={z.nothing_found} />
      ) : (
        receipts.map((receipt) => {
          const s = status(z, 'receipt', receipt.status)
          const ik = receipt.export_status ? status(z, 'iiko', receipt.export_status) : null
          return (
            <Row
              key={receipt.id}
              meta={`${receipt.number} · ${receipt.store_name ?? '—'} · ${f.dt(receipt.received_at)}`}
              title={receipt.supplier_name ?? '—'}
              sub={ik && <span className={receipt.export_status === 'failed' ? 'text-danger' : undefined}>{ik.label}</span>}
              amount={f.money(receipt.total)}
              badge={<Tag tone={s.tone}>{s.label}</Tag>}
              onClick={() => navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: receipt.id } })}
            />
          )
        })
      )}
    </div>
  )
}
