import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Check, Copy, Send, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  CHANNELS,
  ORDERS_KEY,
  PO_STATUS_TONE,
  ordersApi,
  purchaseOrderQuery,
  type Channel,
  type PurchaseOrderDetail,
} from '@/entities/purchase-order'
import { REQUESTS_KEY } from '@/entities/purchase-request'
import { ResponseForm } from '@/features/order-response'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import {
  Card,
  EmptyState,
  FormError,
  LaserButton,
  MoneyText,
  MonoLabel,
  PageHeader,
  SegmentedControl,
  Skeleton,
  StatusBadge,
  TextField,
} from '@/shared/ui'

export default function OrderPage() {
  const { orderId } = useParams({ from: '/shell/orders/$orderId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: order, isPending, error } = useQuery(purchaseOrderQuery(orderId))

  useEffect(() => telegram.backButton(() => navigate({ to: '/orders' })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (error || !order) return <EmptyState code="404" title={t.common.notFound} />
  return <OrderView order={order} />
}

function OrderView({ order }: { order: PurchaseOrderDetail }) {
  const { t, fmt } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isManager = useHasRole('buyer', 'admin')
  const isDecider = useHasRole('buyer', 'approver', 'admin')
  const [channel, setChannel] = useState<Channel>('telegram')
  const [sent, setSent] = useState<{ message: string; response_url: string } | null>(null)
  const [copied, setCopied] = useState(false)
  const [reason, setReason] = useState('')

  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
        queryClient.invalidateQueries({ queryKey: REQUESTS_KEY }),
      ])
    },
  })
  const send = useMutation({
    mutationFn: () => ordersApi.send(order.id, channel),
    onSuccess: async (result) => {
      setSent(result)
      await queryClient.invalidateQueries({ queryKey: ORDERS_KEY })
    },
  })

  const copy = async () => {
    if (!sent) return
    try {
      await navigator.clipboard.writeText(sent.message)
      setCopied(true)
    } catch {
      /* clipboard ruxsati yo'q — foydalanuvchi matnni qo'lda belgilaydi */
    }
  }
  const shareUrl = (target: 'telegram' | 'whatsapp') =>
    target === 'telegram'
      ? `https://t.me/share/url?url=${encodeURIComponent(sent?.response_url ?? '')}&text=${encodeURIComponent(sent?.message ?? '')}`
      : `https://wa.me/?text=${encodeURIComponent(sent?.message ?? '')}`

  const canSend = isManager && (order.status === 'CREATED' || order.status === 'SENT')
  const canRespond = isManager && order.status === 'SENT'
  const canCancel = isDecider && ['CREATED', 'SENT', 'REAPPROVAL'].includes(order.status)

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={`${order.number} · ${order.storeName}`}
        title={t.orderPage.title}
        action={<StatusBadge tone={PO_STATUS_TONE[order.status]}>{t.poStatus[order.status]}</StatusBadge>}
      />

      <Card index={`01/${t.orderPage.delivery} ${fmt.date(order.deliveryDate)}`} title={order.supplierName}>
        {(order.supplierPhone || order.supplierTelegram) && (
          <p className="mt-2 text-[13px] text-text-2">{[order.supplierPhone, order.supplierTelegram].filter(Boolean).join(' · ')}</p>
        )}
        <div className="mt-3 flex items-baseline justify-between">
          <MonoLabel>{t.requests.total}</MonoLabel>
          <MoneyText value={order.totalAmount} className="text-lg" />
        </div>
        {order.confirmedTotal !== order.totalAmount && (
          <div className="mt-1 flex items-baseline justify-between">
            <MonoLabel>{t.orderPage.confirmedTotal}</MonoLabel>
            <MoneyText value={order.confirmedTotal} />
          </div>
        )}
        {order.warnings.includes('below_min_order') && (
          <p className="mt-3 text-[12px] text-warning">{t.orderPage.belowMin(`${fmt.money(order.minOrderAmount)} ${t.common.currency}`)}</p>
        )}
        {order.responseDeadline && order.status === 'SENT' && (
          <p className="mt-2 text-[12px] text-text-3">{`${t.orderPage.deadline}: ${fmt.date(order.responseDeadline)} ${fmt.time(order.responseDeadline)}`}</p>
        )}
        {order.cancelReason && <p className="mt-2 text-[12px] text-danger">{order.cancelReason}</p>}
      </Card>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`02/${t.requests.lines}`}</MonoLabel>
        <div className="flex flex-col gap-2">
          {order.lines.map((line) => (
            <div key={line.id} className="rounded-row border border-border-soft bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-[15px] font-semibold">{line.productName}</div>
                  <div className="mt-0.5 text-[12px] text-text-2">
                    {`${fmt.qty(line.qtyOrdered)} ${t.units[line.unit]}`}
                    {(line.unit !== line.baseUnit || line.packFactor !== 1) &&
                      ` (${fmt.qty(line.qtyOrdered * line.packFactor)} ${t.units[line.baseUnit]})`}
                    {` × ${fmt.money(line.priceOrdered)}`}
                  </div>
                </div>
                <MoneyText value={line.amount} className="shrink-0 text-[13px]" />
              </div>
              {line.response && (
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[12px]">
                  <StatusBadge tone={line.response === 'confirmed' ? 'accent' : 'warning'}>{t.orderPage.responseKinds[line.response]}</StatusBadge>
                  {line.response === 'price_changed' && line.priceConfirmed !== null && <span>{fmt.money(line.priceConfirmed)}</span>}
                  {line.response === 'qty_changed' && line.qtyConfirmed !== null && (
                    <span>{`${fmt.qty(line.qtyConfirmed)} ${t.units[line.unit]}`}</span>
                  )}
                  {line.needsReapproval && <StatusBadge tone="danger">{t.orderPage.needsReapproval}</StatusBadge>}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <FormError>{(action.error ?? send.error) && describeError(action.error ?? send.error, t)}</FormError>

      {canSend && (
        <section className="mt-6 flex flex-col gap-3">
          <MonoLabel>{`03/${t.orderPage.channel}`}</MonoLabel>
          <SegmentedControl
            className="-mx-4 px-4"
            segments={CHANNELS.map((value) => ({ value, label: t.orderPage.channels[value] }))}
            value={channel}
            onChange={setChannel}
          />
          <LaserButton size="lg" block icon={<Send size={16} />} loading={send.isPending} onClick={() => send.mutate()}>
            {order.status === 'SENT' ? t.orderPage.resend : t.orderPage.send}
          </LaserButton>
        </section>
      )}

      {sent && (
        <Card index={t.orderPage.message} className="mt-4">
          <pre className="mt-1 whitespace-pre-wrap break-words font-sans text-[13px] text-text-2">{sent.message}</pre>
          <div className="mt-4 grid grid-cols-1 gap-2">
            <LaserButton variant="ghost" icon={copied ? <Check size={14} /> : <Copy size={14} />} onClick={() => void copy()}>
              {copied ? t.orderPage.copied : t.orderPage.copy}
            </LaserButton>
            <a className="contents" href={shareUrl('telegram')} target="_blank" rel="noreferrer">
              <LaserButton variant="ghost">{t.orderPage.shareTelegram}</LaserButton>
            </a>
            <a className="contents" href={shareUrl('whatsapp')} target="_blank" rel="noreferrer">
              <LaserButton variant="ghost">{t.orderPage.shareWhatsapp}</LaserButton>
            </a>
          </div>
        </Card>
      )}

      {canRespond && <ResponseForm lines={order.lines} onSubmit={(lines) => action.mutate(() => ordersApi.respond(order.id, lines))} busy={action.isPending} />}

      {order.status === 'REAPPROVAL' && isDecider && (
        <LaserButton size="lg" block className="mt-6" icon={<Check size={16} />} loading={action.isPending} onClick={() => action.mutate(() => ordersApi.approveChanges(order.id))}>
          {t.orderPage.approveChanges}
        </LaserButton>
      )}

      {canCancel && (
        <section className="mt-6 flex flex-col gap-2">
          <TextField label={t.orderPage.cancelReason} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
          <LaserButton variant="danger" block icon={<X size={14} />} disabled={!reason.trim()} onClick={() => action.mutate(() => ordersApi.cancel(order.id, reason.trim()))}>
            {t.orderPage.cancel}
          </LaserButton>
        </section>
      )}

      {order.requestId && (
        <button
          type="button"
          className="mt-6 font-mono text-[10px] uppercase tracking-[0.2em] text-text-3"
          onClick={() => navigate({ to: '/requests/$requestId', params: { requestId: order.requestId! } })}
        >
          {`← ${t.orderPage.request}`}
        </button>
      )}
    </div>
  )
}
