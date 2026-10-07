import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { ArrowLeft, ChevronRight, Clock, Copy, Send, X } from 'lucide-react'
import { useState } from 'react'
import {
  CHANNELS,
  ORDERS_KEY,
  ordersApi,
  purchaseOrderQuery,
  type Channel,
  type LineResponseInput,
  type PurchaseOrderDetail,
  type PurchaseOrderLine,
} from '@/entities/purchase-order'
import { REQUESTS_KEY } from '@/entities/purchase-request'
import { useHasRole } from '@/entities/user'
import { ResponseForm } from '@/features/order-response'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { fill, useZk, type ZkFormat, type Zk } from '@/shared/i18n/use-zk'
import {
  Banner,
  Blueprint,
  Btn,
  Chips,
  Empty,
  PageHead,
  RowsSkeleton,
  Section,
  Sheet,
  Tag,
  Textarea,
  confirmAction,
  status,
  toast,
  usePageActions,
  type PageAction,
} from '@/shared/kit'
import { telegram } from '@/shared/lib/telegram'

export default function OrderPage() {
  const { orderId } = useParams({ from: '/shell/orders/$orderId' })
  const { z } = useZk()
  const { data: order, isPending, error } = useQuery(purchaseOrderQuery(orderId))

  if (isPending) return <RowsSkeleton n={5} />
  if (error || !order) return <Empty title={z.not_found} hint={z.not_found_hint} />
  return <OrderView order={order} />
}

// Qabulgacha: tasdiqlangan, lekin kelmagan buyurtma ham bekor qilinadi (backend PurchaseOrder.cancel)
const CANCELLABLE = ['CREATED', 'SENT', 'REAPPROVAL', 'CONFIRMED', 'PARTIALLY_CONFIRMED']
const RECEIVABLE = ['SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED']

function channelLabel(z: Zk, c: Channel): string {
  return { telegram: 'Telegram', whatsapp: 'WhatsApp', phone: z.ch_phone, email: 'E-mail', other: z.ch_other }[c]
}

function OrderView({ order }: { order: PurchaseOrderDetail }) {
  const { z, f } = useZk()
  const { t } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isManager = useHasRole('buyer', 'admin')
  const isDecider = useHasRole('buyer', 'approver', 'admin')
  const canReceive = useHasRole('storekeeper', 'buyer', 'admin')
  const [channel, setChannel] = useState<Channel>(order.sentChannel ?? 'telegram')
  const [sent, setSent] = useState<{ message: string; response_url: string } | null>(null)
  const [responding, setResponding] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [reason, setReason] = useState('')

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
      queryClient.invalidateQueries({ queryKey: REQUESTS_KEY }),
    ])
  // Har amalning o'z holati: bekor qilish xatosi javob oynasida chiqmasin (va aksincha)
  const approve = useMutation({
    mutationFn: () => ordersApi.approveChanges(order.id),
    onSuccess: async () => {
      toast(z.toast_price_ok)
      await refresh()
    },
  })
  const respond = useMutation({
    mutationFn: (lines: LineResponseInput[]) => ordersApi.respond(order.id, lines),
    onSuccess: async () => {
      toast(z.toast_resp)
      setResponding(false)
      await refresh()
    },
  })
  const cancel = useMutation({
    mutationFn: () => ordersApi.cancel(order.id, reason.trim()),
    onSuccess: async () => {
      toast(z.toast_po_cancelled)
      setCancelling(false)
      setReason('')
      await refresh()
    },
  })
  const send = useMutation({
    mutationFn: () => ordersApi.send(order.id, channel),
    onSuccess: async (result) => {
      setSent(result)
      toast(z.toast_sent)
      await refresh()
    },
  })

  const copy = async () => {
    if (!sent) return
    try {
      await navigator.clipboard.writeText(sent.message)
      toast(z.toast_copied)
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
  const canCancel = isDecider && CANCELLABLE.includes(order.status)

  const approvePrice = async () => {
    const ok = await confirmAction({
      title: `${z.a_approve_price}?`,
      body: fill(z.cf_price, { s: f.money(order.confirmedTotal) }),
      label: z.a_approve,
      cancel: z.cancel,
    })
    if (ok) approve.mutate()
  }

  let primary: PageAction | null = null
  if (order.status === 'CREATED' && canSend)
    primary = { label: z.a_send, onClick: () => send.mutate(), loading: send.isPending }
  else if (canRespond) primary = { label: z.a_enter_resp, onClick: () => setResponding(true) }
  else if (order.status === 'REAPPROVAL' && isDecider)
    primary = { label: z.a_approve_price, onClick: () => void approvePrice(), loading: approve.isPending }
  if (!primary && RECEIVABLE.includes(order.status) && canReceive)
    primary = { label: z.a_receive, onClick: () => navigate({ to: '/receiving/$orderId', params: { orderId: order.id } }) }
  usePageActions({
    primary,
    secondary: canCancel ? { label: z.a_cancel_po, onClick: () => setCancelling(true), danger: true } : null,
  })

  const s = status(z, 'order', order.status)
  const hasConf = order.lines.some((l) => l.response !== null)
  const error = approve.error ?? send.error

  return (
    <div className="mx-auto max-w-[720px]">
      <PageHead kicker={order.storeName} title={order.number} aside={<Tag tone={s.tone} className="text-[13px]">{s.label}</Tag>} />

      {error && (
        <Banner tone="danger" onClose={() => {
            approve.reset()
            send.reset()
          }}>
          {describeError(error, t)}
        </Banner>
      )}

      <Blueprint className="mt-4 px-4 py-3.5">
        <div className="font-head text-[22px]" style={{ fontWeight: 600 }}>
          {order.supplierName}
        </div>
        {(order.supplierPhone || order.supplierTelegram) && (
          <div className="flex flex-wrap gap-x-3.5 gap-y-1 text-[14px] text-n7">
            {order.supplierPhone && <span>{order.supplierPhone}</span>}
            {order.supplierTelegram && <span>{order.supplierTelegram}</span>}
          </div>
        )}
        <div className="mt-3 grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
          <div>
            <div className="text-[13px] text-n7">{z.delivery}</div>
            <div className="text-[17px] font-medium">{f.dt(order.deliveryDate)}</div>
          </div>
          <div>
            <div className="text-[13px] text-n7">{z.total}</div>
            <div className="whitespace-nowrap text-[17px] font-medium">{f.money(order.totalAmount)}</div>
          </div>
          {hasConf && (
            <div>
              <div className="text-[13px] text-n7">{z.confirmed_sum}</div>
              <div className="whitespace-nowrap text-[17px] font-medium">{f.money(order.confirmedTotal)}</div>
            </div>
          )}
        </div>
      </Blueprint>

      {order.status === 'SENT' && order.responseDeadline && (
        <Banner tone="info" icon={<Clock size={20} />}>
          {`${z.resp_until} ${f.dtTime(order.responseDeadline)}`}
        </Banner>
      )}
      {order.warnings.includes('below_min_order') && (
        <Banner tone="warn">{`${z.min_order}: ${f.money(order.minOrderAmount)}`}</Banner>
      )}
      {order.cancelReason && (
        <Banner tone="danger" icon={<X size={20} />}>
          {`${z.cancel_reason}: ${order.cancelReason}`}
        </Banner>
      )}

      <Section>{z.positions_pack}</Section>
      {order.lines.map((line) => (
        <OrderLineRow key={line.id} line={line} z={z} f={f} />
      ))}

      {canSend && (
        <>
          <Section className="mb-2">{z.send_channel}</Section>
          <Chips options={CHANNELS.map((c) => ({ value: c, label: channelLabel(z, c) }))} value={channel} onChange={setChannel} />
          {order.status === 'SENT' && (
            <Btn variant="ghost" className="mt-2" icon={<Send size={20} />} loading={send.isPending} onClick={() => send.mutate()}>
              {z.a_resend}
            </Btn>
          )}
        </>
      )}

      {sent && (
        <>
          <Section className="mb-2">{z.msg_ready}</Section>
          <div className="whitespace-pre-wrap break-words border border-line p-3 text-[14px]" style={{ background: 'var(--color-surface)' }}>{sent.message}</div>
          <div className="mt-2 grid grid-cols-3 gap-2">
            <Btn icon={<Copy size={20} />} onClick={() => void copy()}>
              {z.a_copy}
            </Btn>
            <Btn onClick={() => telegram.openLink(shareUrl('telegram'))}>Telegram</Btn>
            <Btn onClick={() => telegram.openLink(shareUrl('whatsapp'))}>WhatsApp</Btn>
          </div>
        </>
      )}

      <div className="mt-5 flex flex-wrap gap-x-4 gap-y-2">
        {order.requestId && (
          <Btn
            variant="ghost"
            icon={<ArrowLeft size={20} />}
            onClick={() => navigate({ to: '/requests/$requestId', params: { requestId: order.requestId! } })}
          >
            {z.request}
          </Btn>
        )}
        {sent && (
          <Btn variant="ghost" onClick={() => telegram.openLink(sent.response_url)}>
            {z.as_supplier}
            <ChevronRight size={20} />
          </Btn>
        )}
      </div>

      <Sheet open={responding} title={z.supplier_resp} onClose={() => setResponding(false)}>
        <ResponseForm
          lines={order.lines}
          busy={respond.isPending}
          onSubmit={(lines) => respond.mutate(lines)}
        />
        {respond.error && <Banner tone="danger">{describeError(respond.error, t)}</Banner>}
      </Sheet>

      <Sheet open={cancelling} title={z.cancel_po_title} onClose={() => setCancelling(false)}>
        <Textarea
          className="min-h-24"
          value={reason}
          maxLength={500}
          placeholder={z.reason_ph}
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="mt-1.5 text-[13px] text-n7">{z.reason_req}</div>
        {cancel.error && <Banner tone="danger">{describeError(cancel.error, t)}</Banner>}
        <Btn
          size="lg"
          block
          danger
          className="mt-4"
          style={{ borderColor: 'var(--zk-danger)' }}
          disabled={!reason.trim()}
          loading={cancel.isPending}
          onClick={() => cancel.mutate()}
        >
          {z.a_cancel_po}
        </Btn>
      </Sheet>
    </div>
  )
}

function OrderLineRow({ line, z, f }: { line: PurchaseOrderLine; z: Zk; f: ZkFormat }) {
  const packed = line.unit !== line.baseUnit || line.packFactor !== 1
  const qty = packed
    ? `${f.n(line.qtyOrdered)} ${f.pack(line.unit)} (${f.qty(line.qtyOrdered * line.packFactor, line.baseUnit)})`
    : f.qty(line.qtyOrdered, line.baseUnit)
  let resp = ''
  let color = 'var(--color-neutral-700)'
  if (line.response === 'confirmed') {
    resp = z.r_ok
    color = 'var(--color-accent-700)'
  } else if (line.response === 'price_changed') {
    resp = `${z.r_price}${line.priceConfirmed !== null ? ` ${f.money(line.priceConfirmed)}` : ''}`
    color = line.needsReapproval ? 'var(--zk-warn)' : 'var(--color-neutral-700)'
  } else if (line.response === 'qty_changed') {
    resp = `${z.r_qty}${line.qtyConfirmed !== null ? ` ${f.n(line.qtyConfirmed)} ${f.pack(line.unit)}` : ''}`
    color = 'var(--zk-warn)'
  } else if (line.response === 'out_of_stock') {
    resp = z.r_no
    color = 'var(--zk-danger)'
  }
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 border-b border-line py-3">
      <div className="text-[16px] font-medium">{line.productName}</div>
      <div className="whitespace-nowrap text-[15px] font-medium">{f.money(line.amount)}</div>
      <div className="col-span-full text-[14px] text-n7">{`${qty} × ${f.n(line.priceOrdered)}`}</div>
      {line.response && (
        <div className="col-span-full flex flex-wrap items-center gap-2 text-[14px]" style={{ color }}>
          {`${z.supplier_says}: ${resp}`}
          {line.needsReapproval && <Tag tone="warn">{z.over_tol}</Tag>}
        </div>
      )}
    </div>
  )
}
