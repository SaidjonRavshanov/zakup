import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { ChevronDown, ChevronUp, Plus, RefreshCw, TriangleAlert, X } from 'lucide-react'
import { useState } from 'react'
import { productQuery } from '@/entities/catalog'
import { ORDERS_KEY } from '@/entities/purchase-order'
import {
  REQUESTS_KEY,
  requestQuery,
  requestsApi,
  WhyQuantity,
  type Decision,
  type RequestDetail,
  type RequestLine,
} from '@/entities/purchase-request'
import { meQuery, useHasRole } from '@/entities/user'
import { ApiError } from '@/shared/api/client'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { fill, todayIso, useZk, type ZkKey } from '@/shared/i18n/use-zk'
import {
  Banner,
  Btn,
  Cells,
  Check,
  Empty,
  LinkRow,
  PageHead,
  RowsSkeleton,
  Section,
  Seg,
  Sheet,
  Stepper,
  Tag,
  Textarea,
  confirmAction,
  status,
  toast,
  usePageActions,
} from '@/shared/kit'
import { AddProductSheet, type PickedProduct } from './AddProductSheet'
import { L } from './i18n'
import { packInfo, parseQty, qtyBody, qtyStep, typeLabel } from './labels'

export default function RequestPage() {
  const { requestId } = useParams({ from: '/shell/requests/$requestId' })
  const { z } = useZk()
  const { data: request, isPending, error } = useQuery(requestQuery(requestId))

  if (isPending) return <RowsSkeleton n={5} />
  if (error || !request) return <Empty title={z.not_found} hint={z.not_found_hint} />
  return <RequestView request={request} />
}

const LOG_KEY: Record<Decision, ZkKey> = {
  approved: 'log_approved',
  partial: 'log_partial',
  returned: 'log_returned',
  rejected: 'log_rejected',
}

interface Run {
  fn: () => Promise<unknown>
  msg?: (result: unknown) => string
  after?: () => void
}

function RequestView({ request }: { request: RequestDetail }) {
  const { z, f, locale } = useZk()
  const { t } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: me } = useQuery(meQuery)
  const isManager = useHasRole('buyer', 'admin')
  const isDecider = useHasRole('buyer', 'approver', 'admin')
  const canEdit = request.status === 'DRAFT' && (me?.id === request.initiator_id || isManager)
  const pending = request.status === 'PENDING_APPROVAL'
  const canDecide = pending && isDecider
  const canSup = canEdit || (pending && isManager)

  const [deselected, setDeselected] = useState<ReadonlySet<string>>(new Set())
  const [why, setWhy] = useState<string | null>(null)
  const [lineId, setLineId] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [addKey, setAddKey] = useState(0)
  const [deciding, setDeciding] = useState(false)
  const [reason, setReason] = useState('')

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: REQUESTS_KEY }),
      queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
    ])
  const action = useMutation({
    mutationFn: (run: Run) => run.fn(),
    onSuccess: async (result, run) => {
      if (run.msg) toast(run.msg(result))
      run.after?.()
      await refresh()
    },
  })
  const run = (r: Run) => action.mutate(r)

  const add = useMutation({
    mutationFn: (p: PickedProduct) => requestsApi.addLine(request.id, { product_id: p.product.id, qty: qtyBody(p.qty), note: null }),
    onSuccess: async () => {
      toast(z.toast_added)
      setAdding(false)
      setAddKey((k) => k + 1)
      await refresh()
    },
  })

  // Qoralama sanasini o'zgartirish (comment o'zgarmaydi — backend ikkalasini birga oladi)
  const revise = useMutation({
    mutationFn: (neededBy: string) => requestsApi.revise(request.id, { needed_by: neededBy, comment: request.comment }),
    onSuccess: async () => {
      toast(z.toast_saved)
      await refresh()
    },
  })
  const neededPast = request.needed_by < todayIso()
  const needOptions = [
    { value: todayIso(), label: z.today_l },
    { value: todayIso(1), label: z.tomorrow_l },
    { value: todayIso(2), label: f.dt(todayIso(2)) },
  ]

  const selected = request.lines.filter((l) => !deselected.has(l.id))
  const partial = selected.length < request.lines.length
  const selTotal = selected.reduce((a, l) => a + Number(l.order_amount ?? l.amount), 0)
  const toggle = (id: string) =>
    setDeselected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const cancel = async () => {
    const ok = await confirmAction({
      title: fill(z.cf_cancel_req, { id: request.number }),
      body: z.cf_irrev,
      label: z.a_cancel_req,
      cancel: z.cancel,
      danger: true,
    })
    if (ok) run({ fn: () => requestsApi.cancel(request.id), msg: () => z.toast_cancelled })
  }

  const decide = (kind: 'return' | 'reject') => {
    const comment = reason.trim()
    if (!comment) return
    run({
      fn: () => (kind === 'return' ? requestsApi.returnBack(request.id, comment) : requestsApi.reject(request.id, comment)),
      msg: () => (kind === 'return' ? z.toast_returned : z.toast_rejected),
      after: () => {
        setDeciding(false)
        setReason('')
      },
    })
  }

  usePageActions(
    canEdit
      ? {
          primary: {
            label: z.a_submit,
            onClick: () => run({ fn: () => requestsApi.submit(request.id), msg: () => z.toast_submitted }),
            disabled: request.lines.length === 0,
            loading: action.isPending,
          },
          secondary: { label: z.a_cancel_req, onClick: () => void cancel(), danger: true },
        }
      : canDecide
        ? {
            primary: {
              label: partial ? `${z.a_approve_sel} (${selected.length})` : z.a_approve,
              onClick: () =>
                run({
                  fn: () => requestsApi.approve(request.id, partial ? selected.map((l) => l.id) : null),
                  msg: (r) => `${z.toast_approved} · ${z.orders_created}: ${(r as { order_ids: string[] }).order_ids.length}`,
                  after: () => setDeselected(new Set()),
                }),
              disabled: selected.length === 0,
              loading: action.isPending,
            },
            secondary: { label: z.a_return_reject, onClick: () => setDeciding(true) },
          }
        : {},
  )

  const s = status(z, 'request', request.status)
  const sheetLine = request.lines.find((l) => l.id === lineId) ?? null
  const conflict = action.error instanceof ApiError && action.error.status === 409

  return (
    <div className="mx-auto max-w-[720px]">
      <PageHead
        kicker={`${request.store_name ?? '—'} · ${typeLabel(z, request.type)}`}
        title={request.number}
        aside={<Tag tone={s.tone} className="text-[13px]">{s.label}</Tag>}
      />

      {action.error && (
        <Banner
          tone="danger"
          onClose={() => action.reset()}
          action={
            conflict && (
              <Btn
                size="sm"
                icon={<RefreshCw size={18} />}
                style={{ color: 'var(--zk-danger)', borderColor: 'var(--zk-danger)' }}
                onClick={() => {
                  action.reset()
                  void refresh().then(() => toast(z.toast_refreshed))
                }}
              >
                {z.a_refresh}
              </Btn>
            )
          }
        >
          {conflict ? z.err_conflict : describeError(action.error, t)}
        </Banner>
      )}

      <Cells
        className="mt-4"
        cols={2}
        size={22}
        items={[
          { label: z.need_to, value: f.dt(request.needed_by) },
          { label: z.total, value: f.money(request.order_total ?? request.total) },
        ]}
      />
      {canEdit && (
        <>
          <div className="mb-2 mt-4 text-[13px] font-medium text-n7">{z.need_to}</div>
          <Seg
            options={needOptions}
            value={request.needed_by}
            onChange={(date) => date !== request.needed_by && !revise.isPending && revise.mutate(date)}
          />
          {neededPast && <Banner tone="warn">{L[locale].needed_past}</Banner>}
          {revise.error && (
            <Banner tone="danger" onClose={() => revise.reset()}>
              {describeError(revise.error, t)}
            </Banner>
          )}
        </>
      )}
      {request.type === 'auto' && <div className="mt-2.5 text-[14px] text-n7">{`${z.author}: ${z.autoreq}`}</div>}
      {request.comment && <div className="mt-1.5 border-l-2 border-line pl-2.5 text-[15px]">{request.comment}</div>}

      <Section aside={canDecide ? `${z.selected}: ${selected.length} · ${f.money(selTotal)}` : undefined}>
        {`${z.positions} · ${request.lines.length}`}
      </Section>
      {request.lines.map((line) => (
        <LineRow
          key={line.id}
          line={line}
          selectable={canDecide}
          selected={!deselected.has(line.id)}
          onToggle={() => toggle(line.id)}
          whyOpen={why === line.id}
          onWhy={() => setWhy(why === line.id ? null : line.id)}
          onTap={canSup ? () => setLineId(line.id) : undefined}
        />
      ))}
      {canEdit && (
        <Btn size="lg" block className="mt-4" icon={<Plus size={20} />} onClick={() => setAdding(true)}>
          {z.add_item}
        </Btn>
      )}

      {request.orders.length > 0 && (
        <>
          <Section>{z.orders}</Section>
          {request.orders.map((order) => {
            const os = status(z, 'order', order.status)
            return (
              <LinkRow
                key={order.id}
                aside={<Tag tone={os.tone}>{os.label}</Tag>}
                onClick={() => navigate({ to: '/orders/$orderId', params: { orderId: order.id } })}
              >
                <span className="font-medium">{order.number}</span>
                {` · ${order.supplier_name ?? '—'}`}
              </LinkRow>
            )
          })}
        </>
      )}

      {request.approvals.length > 0 && (
        <>
          <Section className="mb-1">{z.decisions}</Section>
          {request.approvals.map((a, i) => (
            <div key={i} className="flex flex-col gap-1 border-b border-line py-2.5">
              <div className="flex justify-between gap-3 text-[15px]">
                <span>
                  <span className="font-medium">{capitalize(z[LOG_KEY[a.decision]])}</span>
                  {` · ${f.money(a.amount)}`}
                </span>
                <span className="whitespace-nowrap text-[13px] text-n7">{f.dtTime(a.decided_at)}</span>
              </div>
              {a.comment && <div className="text-[14px] text-n7">{`«${a.comment}»`}</div>}
              {a.role_conflict && (
                <Tag tone="warn" className="self-start">
                  {z.combo}
                </Tag>
              )}
            </div>
          ))}
        </>
      )}

      <Sheet open={!!sheetLine} title={sheetLine?.product_name ?? ''} onClose={() => setLineId(null)}>
        {sheetLine && (
          <LineSheet
            key={sheetLine.id}
            request={request}
            line={sheetLine}
            editable={canEdit}
            onChanged={refresh}
            onDeleted={() => setLineId(null)}
          />
        )}
      </Sheet>

      {canEdit && (
        <AddProductSheet
          key={addKey}
          open={adding}
          onClose={() => {
            setAdding(false)
            add.reset()
          }}
          exclude={new Set(request.lines.map((l) => l.product_id))}
          onAdd={(p) => add.mutate(p)}
          busy={add.isPending}
          error={add.error ? describeError(add.error, t) : null}
        />
      )}

      <Sheet open={deciding} title={z.decide_title} onClose={() => setDeciding(false)}>
        <Textarea
          className="min-h-24"
          value={reason}
          maxLength={500}
          placeholder={z.reason_ph}
          onChange={(e) => setReason(e.target.value)}
        />
        <div className="mt-1.5 text-[13px] text-n7">{z.reason_req}</div>
        {action.error && <Banner tone="danger">{describeError(action.error, t)}</Banner>}
        <div className="mt-4 flex gap-2.5">
          <Btn size="lg" className="flex-1" disabled={!reason.trim() || action.isPending} onClick={() => decide('return')}>
            {z.a_return}
          </Btn>
          <Btn
            size="lg"
            danger
            className="flex-1"
            style={{ borderColor: 'var(--zk-danger)' }}
            disabled={!reason.trim() || action.isPending}
            onClick={() => decide('reject')}
          >
            {z.a_reject}
          </Btn>
        </div>
      </Sheet>
    </div>
  )
}

const capitalize = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

function LineRow({
  line,
  selectable,
  selected,
  onToggle,
  whyOpen,
  onWhy,
  onTap,
}: {
  line: RequestLine
  selectable: boolean
  selected: boolean
  onToggle: () => void
  whyOpen: boolean
  onWhy: () => void
  onTap?: () => void
}) {
  const { z, f } = useZk()
  const unit = line.base_unit
  const suggested = line.qty_suggested !== null ? Number(line.qty_suggested) : null
  const changed = suggested !== null && suggested !== Number(line.qty)
  const Body = onTap ? 'button' : 'div'
  return (
    <div className="flex items-stretch border-b border-line" style={{ opacity: line.decision === 'rejected' ? 0.45 : 1 }}>
      {selectable && (
        <div className="pt-3">
          <Check on={selected} onToggle={onToggle} label={line.product_name} />
        </div>
      )}
      <div className="min-w-0 flex-1 py-3">
        <Body
          type={onTap ? 'button' : undefined}
          onClick={onTap}
          className="grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 text-left text-ink"
          style={{ cursor: onTap ? 'pointer' : 'default' }}
        >
          <div className="text-[16px] font-medium leading-tight">{line.product_name}</div>
          <div className="whitespace-nowrap text-right text-[15px] font-medium">
            {line.supplier_name ? f.money(line.order_amount ?? line.amount) : '—'}
          </div>
          <div className="col-span-full text-[14px]">
            {f.qty(line.qty, unit)}
            {/* Qadoqqa yaxlitlash: "40 kg → 2 qop" (buyurtmaga shunday ketadi) */}
            {line.qty_packs && line.pack_unit && !(Number(line.pack_factor) === 1 && line.pack_unit === unit) && (
              <span className="text-warn">{` → ${f.n(Number(line.qty_packs))} ${f.pack(line.pack_unit)}`}</span>
            )}
          </div>
          {line.supplier_name ? (
            <div className="col-span-full text-[13px] text-n7">
              {line.price_per_base !== null
                ? `${line.supplier_name} · ${f.money(line.price_per_base)} / ${f.unit(unit)}`
                : line.supplier_name}
            </div>
          ) : (
            <div className="col-span-full flex items-center gap-1.5 text-[14px] text-warn">
              <TriangleAlert size={16} />
              {z.no_sup}
            </div>
          )}
        </Body>
        {suggested !== null && line.calc && (
          <>
            <button
              type="button"
              onClick={onWhy}
              className="mt-1 flex min-h-9 items-center gap-1 py-1.5 text-[14px]"
              style={{ color: changed ? 'var(--zk-warn)' : 'var(--color-accent-700)' }}
            >
              {changed ? `${z.changed_auto}: ${f.qty(suggested, unit)}` : z.why_much}
              {whyOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            {whyOpen && <WhyQuantity calc={line.calc} unit={unit} qty={suggested} />}
          </>
        )}
      </div>
    </div>
  )
}

function LineSheet({
  request,
  line,
  editable,
  onChanged,
  onDeleted,
}: {
  request: RequestDetail
  line: RequestLine
  editable: boolean
  onChanged: () => Promise<unknown>
  onDeleted: () => void
}) {
  const { z, f } = useZk()
  const { t } = useI18n()
  const { data: product } = useQuery(productQuery(line.product_id))
  // Aniq qiymat (4 kasrgacha, yaxlitlanmaydi) — tahrirsiz "o'zgardi" bo'lib qolmasin
  const [qty, setQty] = useState(String(Number(line.qty)).replace('.', ','))
  const offers = (product?.offers ?? []).filter((o) => !o.archived)
  const current = offers.find((o) => o.id === line.offer_id) ?? null
  const save = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: () => onChanged(),
  })
  const value = parseQty(qty)
  const packed = current && !(Number(current.pack_factor) === 1 && current.pack_unit === line.base_unit)
  const step = packed ? Number(current.pack_factor) : qtyStep(line.base_unit)
  const pk = current && value > 0 ? packInfo(value, current, f, line.base_unit) : null
  const dirty = value > 0 && qtyBody(qty) !== String(Number(line.qty))

  const packText = pk?.label ? `= ${pk.label} · ${f.money(pk.sum)}` : ''

  return (
    <>
      <div className="mb-2 mt-1 text-[13px] font-medium text-n7">{z.supplier}</div>
      {offers.length === 0 && <div className="py-2 text-[14px] text-n7">{t.requests.noOffers}</div>}
      <div className="flex flex-col gap-2">
        {offers.map((o) => {
          const on = o.id === line.offer_id
          const packOf = !(Number(o.pack_factor) === 1 && o.pack_unit === o.base_unit)
          return (
            <button
              key={o.id}
              type="button"
              disabled={save.isPending}
              onClick={() => !on && save.mutate(() => requestsApi.chooseOffer(request.id, line.id, o.id))}
              className="flex min-h-14 items-center gap-3 bg-transparent px-3 py-2 text-left text-ink"
              style={{ border: `1px solid ${on ? 'var(--color-accent)' : 'var(--color-divider)'}` }}
            >
              <span
                className="size-[18px] shrink-0 rounded-full"
                style={{
                  border: `1.5px solid ${on ? 'var(--color-accent)' : 'var(--color-divider)'}`,
                  boxShadow: 'inset 0 0 0 4px var(--color-bg)',
                  background: on ? 'var(--color-accent)' : 'transparent',
                }}
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[16px] font-medium">{o.supplier_name}</span>
                <span className="block text-[13px] text-n7">
                  {`${f.money(o.base_unit_price)} / ${f.unit(o.base_unit)}`}
                  {packOf && ` · 1 ${f.pack(o.pack_unit)} = ${f.qty(o.pack_factor, o.base_unit)}`}
                </span>
              </span>
            </button>
          )
        })}
      </div>
      {editable && (
        <>
          <div className="mb-2 mt-5 text-[13px] font-medium text-n7">{packed ? z.qty_packs : `${z.qty} · ${f.unit(line.base_unit)}`}</div>
          {/* min — bitta qadoq; undan kichik qiymat "−" bilan yuqoriga sakramaydi (Stepper) */}
          <Stepper size={56} value={qty} onChange={setQty} step={step} min={step} unit={f.unit(line.base_unit)} label={z.qty} />
          {packText && <div className="mt-2 text-[14px] text-n7">{packText}</div>}
          {dirty && (
            <Btn
              variant="primary"
              size="lg"
              block
              className="mt-4"
              loading={save.isPending}
              onClick={() => save.mutate(() => requestsApi.changeLine(request.id, line.id, { qty: qtyBody(qty), note: line.note }))}
            >
              {z.a_save}
            </Btn>
          )}
          <Btn
            variant="ghost"
            danger
            className="mt-4"
            icon={<X size={20} />}
            disabled={save.isPending}
            onClick={() =>
              save.mutate(async () => {
                await requestsApi.removeLine(request.id, line.id)
                onDeleted()
              })
            }
          >
            {z.a_delete_line}
          </Btn>
        </>
      )}
      {save.error && <Banner tone="danger">{describeError(save.error, t)}</Banner>}
    </>
  )
}
