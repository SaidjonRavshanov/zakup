import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Check, CornerUpLeft, Plus, Send, Trash2, X } from 'lucide-react'
import { useDeferredValue, useEffect, useState } from 'react'
import { productQuery, productsQuery } from '@/entities/catalog'
import { ORDERS_KEY, PO_STATUS_TONE } from '@/entities/purchase-order'
import {
  REQUESTS_KEY,
  REQUEST_STATUS_TONE,
  requestQuery,
  requestsApi,
  type RequestDetail,
  type RequestLine,
} from '@/entities/purchase-request'
import { meQuery, useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import {
  Card,
  EmptyState,
  FormError,
  LaserButton,
  ListRow,
  MoneyText,
  MonoLabel,
  PageHeader,
  SearchPill,
  SelectField,
  Skeleton,
  StatusBadge,
  TextField,
} from '@/shared/ui'

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

export default function RequestPage() {
  const { requestId } = useParams({ from: '/shell/requests/$requestId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: request, isPending, error } = useQuery(requestQuery(requestId))

  useEffect(() => telegram.backButton(() => navigate({ to: '/requests' })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (error || !request) return <EmptyState code="404" title={t.common.notFound} />
  return <RequestView request={request} />
}

function RequestView({ request }: { request: RequestDetail }) {
  const { t, fmt } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: me } = useQuery(meQuery)
  const isManager = useHasRole('buyer', 'admin')
  const isDecider = useHasRole('buyer', 'approver', 'admin')
  const canEdit = request.status === 'DRAFT' && (me?.id === request.initiator_id || isManager)
  const pending = request.status === 'PENDING_APPROVAL'
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [openLine, setOpenLine] = useState<string | null>(null)
  const [comment, setComment] = useState('')

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: REQUESTS_KEY }),
      queryClient.invalidateQueries({ queryKey: ORDERS_KEY }),
    ])
  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      setSelected(new Set())
      setComment('')
      await refresh()
    },
  })
  const run = (fn: () => Promise<unknown>) => action.mutate(fn)

  const partial = selected.size > 0 && selected.size < request.lines.length

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={`${request.number} · ${request.store_name ?? '—'}`}
        title={t.requestType[request.type]}
        action={<StatusBadge tone={REQUEST_STATUS_TONE[request.status]}>{t.requestStatus[request.status]}</StatusBadge>}
      />

      <Card index={`01/${t.requests.neededBy}`} title={fmt.date(request.needed_by)}>
        {request.comment && <p className="mt-2 text-[13px] text-text-2">{request.comment}</p>}
        <div className="mt-3 flex items-baseline justify-between">
          <MonoLabel>{t.requests.total}</MonoLabel>
          <MoneyText value={Number(request.total)} className="text-lg" />
        </div>
      </Card>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`02/${t.requests.lines}`}</MonoLabel>
        <div className="flex flex-col gap-2">
          {request.lines.map((line) => (
            <LineCard
              key={line.id}
              request={request}
              line={line}
              open={openLine === line.id}
              onToggle={() => setOpenLine(openLine === line.id ? null : line.id)}
              editable={canEdit}
              supplierEditable={canEdit || (pending && isManager)}
              selectable={pending && isDecider}
              selected={selected.has(line.id)}
              onSelect={(on) =>
                setSelected((prev) => {
                  const next = new Set(prev)
                  if (on) next.add(line.id)
                  else next.delete(line.id)
                  return next
                })
              }
              onChanged={refresh}
            />
          ))}
          {canEdit && <AddProduct request={request} onAdded={refresh} />}
        </div>
      </section>

      <FormError>{action.error && describeError(action.error, t)}</FormError>

      {canEdit && (
        <div className="mt-6 flex flex-col gap-2">
          <LaserButton
            size="lg"
            block
            icon={<Send size={16} />}
            disabled={request.lines.length === 0}
            loading={action.isPending}
            onClick={() => run(() => requestsApi.submit(request.id))}
          >
            {t.requests.submit}
          </LaserButton>
          <LaserButton variant="ghost" block icon={<X size={14} />} onClick={() => run(() => requestsApi.cancel(request.id))}>
            {t.requests.cancel}
          </LaserButton>
        </div>
      )}

      {pending && isDecider && (
        <div className="mt-6 flex flex-col gap-2">
          <LaserButton
            size="lg"
            block
            icon={<Check size={16} />}
            loading={action.isPending}
            onClick={() => run(() => requestsApi.approve(request.id, partial ? [...selected] : null))}
          >
            {partial ? t.requests.approveSelected(selected.size) : t.requests.approve}
          </LaserButton>
          <TextField label={t.requests.comment} placeholder={t.requests.commentPlaceholder} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="grid grid-cols-2 gap-2">
            <LaserButton
              variant="ghost"
              icon={<CornerUpLeft size={14} />}
              disabled={!comment.trim()}
              onClick={() => run(() => requestsApi.returnBack(request.id, comment.trim()))}
            >
              {t.requests.returnBack}
            </LaserButton>
            <LaserButton
              variant="danger"
              icon={<X size={14} />}
              disabled={!comment.trim()}
              onClick={() => run(() => requestsApi.reject(request.id, comment.trim()))}
            >
              {t.requests.reject}
            </LaserButton>
          </div>
        </div>
      )}

      {request.orders.length > 0 && (
        <section className="mt-6">
          <MonoLabel className="mb-3">{`03/${t.requests.orders}`}</MonoLabel>
          <div className="flex flex-col gap-2">
            {request.orders.map((order) => (
              <ListRow
                key={order.id}
                meta={order.number}
                title={order.supplier_name ?? '—'}
                badge={<StatusBadge tone={PO_STATUS_TONE[order.status]}>{t.poStatus[order.status]}</StatusBadge>}
                trailing={<MoneyText value={Number(order.total)} className="text-[13px]" />}
                onClick={() => navigate({ to: '/orders/$orderId', params: { orderId: order.id } })}
              />
            ))}
          </div>
        </section>
      )}

      {request.approvals.length > 0 && (
        <section className="mt-6">
          <MonoLabel className="mb-3">{`04/${t.requests.history}`}</MonoLabel>
          <div className="rounded-card border border-border-soft bg-surface px-4">
            {request.approvals.map((a, i) => (
              <div key={i} className="border-b border-border-soft py-3 last:border-0">
                <div className="flex items-center justify-between gap-3 text-[13px]">
                  <span className="font-semibold">{t.requests.decision[a.decision]}</span>
                  <span className="text-text-3">{`${fmt.date(a.decided_at)} ${fmt.time(a.decided_at)}`}</span>
                </div>
                {a.comment && <p className="mt-1 text-[13px] text-text-2">{a.comment}</p>}
                {a.role_conflict && <StatusBadge tone="warning" className="mt-2">{t.requests.roleConflict}</StatusBadge>}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

interface LineCardProps {
  request: RequestDetail
  line: RequestLine
  open: boolean
  onToggle: () => void
  editable: boolean
  supplierEditable: boolean
  selectable: boolean
  selected: boolean
  onSelect: (on: boolean) => void
  onChanged: () => Promise<unknown>
}

function LineCard({ request, line, open, onToggle, editable, supplierEditable, selectable, selected, onSelect, onChanged }: LineCardProps) {
  const { t, fmt } = useI18n()
  const unit = t.units[line.base_unit]
  const rejected = line.decision === 'rejected'
  return (
    <div className={cn('rounded-row border border-border-soft bg-surface shadow-[var(--shadow-card)]', rejected && 'opacity-50')}>
      <div className="flex items-center gap-3 px-4 py-3">
        {selectable && (
          <button
            type="button"
            aria-pressed={selected}
            aria-label={line.product_name}
            onClick={() => onSelect(!selected)}
            className={cn(
              'grid size-6 shrink-0 place-items-center rounded-md border',
              selected ? 'border-[var(--accent-border)] bg-accent text-accent-ink' : 'border-border',
            )}
          >
            {selected && <Check size={14} />}
          </button>
        )}
        <button type="button" className="min-w-0 flex-1 text-left" onClick={supplierEditable ? onToggle : undefined}>
          <div className="truncate text-[15px] font-semibold">{line.product_name}</div>
          <div className={cn('mt-0.5 truncate text-[12px]', line.supplier_name ? 'text-text-2' : 'text-warning')}>
            {line.supplier_name ?? t.requests.noSupplier}
            {rejected && ` · ${t.requests.lineRejected}`}
          </div>
        </button>
        <div className="shrink-0 text-right">
          <div className="tnum text-[14px] font-semibold">{`${fmt.qty(Number(line.qty))} ${unit}`}</div>
          <MoneyText value={Number(line.amount)} className="text-[12px] font-normal text-text-2" />
        </div>
      </div>
      {open && supplierEditable && <LineEditor request={request} line={line} editable={editable} onChanged={onChanged} />}
    </div>
  )
}

function LineEditor({
  request,
  line,
  editable,
  onChanged,
}: {
  request: RequestDetail
  line: RequestLine
  editable: boolean
  onChanged: () => Promise<unknown>
}) {
  const { t, fmt } = useI18n()
  const { data: product } = useQuery(productQuery(line.product_id))
  const [qty, setQty] = useState(String(Number(line.qty)))
  const offers = (product?.offers ?? []).filter((o) => !o.archived)
  const save = useMutation({
    mutationFn: (run: () => Promise<unknown>) => run(),
    onSuccess: () => onChanged(),
  })

  return (
    <div className="flex flex-col gap-3 border-t border-border-soft px-4 py-3">
      <SelectField
        label={t.requests.supplier}
        value={line.offer_id ?? ''}
        hint={offers.length === 0 ? t.requests.noOffers : undefined}
        options={[
          { value: '', label: t.requests.noSupplier },
          ...offers.map((o) => ({
            value: o.id,
            label: `${o.supplier_name} · ${fmt.money(Number(o.base_unit_price))} / ${t.units[o.base_unit]}`,
          })),
        ]}
        onChange={(e) => save.mutate(() => requestsApi.chooseOffer(request.id, line.id, e.target.value || null))}
      />
      {editable && (
        <div className="flex items-end gap-2">
          <TextField
            className="flex-1"
            label={t.requests.qty}
            inputMode="decimal"
            suffix={t.units[line.base_unit]}
            value={qty}
            onChange={(e) => setQty(decimal(e.target.value))}
          />
          <LaserButton
            type="button"
            className="h-12"
            icon={<Check size={14} />}
            disabled={!(Number(qty) > 0) || Number(qty) === Number(line.qty)}
            loading={save.isPending}
            onClick={() => save.mutate(() => requestsApi.changeLine(request.id, line.id, { qty, note: line.note }))}
          >
            {t.requests.save}
          </LaserButton>
          <LaserButton
            type="button"
            variant="danger"
            className="h-12"
            aria-label={t.requests.remove}
            icon={<Trash2 size={14} />}
            onClick={() => save.mutate(() => requestsApi.removeLine(request.id, line.id))}
          >
            {''}
          </LaserButton>
        </div>
      )}
      <FormError>{save.error && describeError(save.error, t)}</FormError>
    </div>
  )
}

function AddProduct({ request, onAdded }: { request: RequestDetail; onAdded: () => Promise<unknown> }) {
  const { t } = useI18n()
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim())
  const [picked, setPicked] = useState<{ id: string; name: string; unit: string } | null>(null)
  const [qty, setQty] = useState('')
  const { data: products = [] } = useQuery({ ...productsQuery(query), enabled: query.length >= 2 })
  const inRequest = new Set(request.lines.map((line) => line.product_id))

  const add = useMutation({
    mutationFn: () => requestsApi.addLine(request.id, { product_id: picked!.id, qty, note: null }),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      setPicked(null)
      setQty('')
      setSearch('')
      await onAdded()
    },
  })

  return (
    <div className="mt-2 rounded-card border border-dashed border-border p-3">
      <MonoLabel className="mb-2">{t.requests.addProduct}</MonoLabel>
      {picked ? (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2 text-[15px] font-semibold">
            {picked.name}
            <button type="button" aria-label="x" className="text-text-3" onClick={() => setPicked(null)}>
              <X size={16} />
            </button>
          </div>
          <div className="flex items-end gap-2">
            <TextField
              className="flex-1"
              label={t.requests.qty}
              inputMode="decimal"
              autoFocus
              suffix={picked.unit}
              value={qty}
              onChange={(e) => setQty(decimal(e.target.value))}
            />
            <LaserButton type="button" className="h-12" icon={<Plus size={14} />} disabled={!(Number(qty) > 0)} loading={add.isPending} onClick={() => add.mutate()}>
              {t.requests.add}
            </LaserButton>
          </div>
          <FormError>{add.error && describeError(add.error, t)}</FormError>
        </div>
      ) : (
        <>
          <SearchPill placeholder={t.requests.searchProduct} value={search} onChange={(e) => setSearch(e.target.value)} />
          {query.length >= 2 && (
            <div className="mt-2 flex flex-col">
              {products
                .filter((p) => !inRequest.has(p.id))
                .slice(0, 8)
                .map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="flex items-center justify-between gap-3 border-b border-border-soft px-2 py-2.5 text-left text-[14px] last:border-0"
                    onClick={() => setPicked({ id: p.id, name: p.name, unit: t.units[p.base_unit] })}
                  >
                    <span className="truncate">{p.name}</span>
                    <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.2em] text-text-3">{t.units[p.base_unit]}</span>
                  </button>
                ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
