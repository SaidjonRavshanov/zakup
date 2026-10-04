import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Check, Lock } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  FINANCE_KEY,
  OBLIGATION_TONE,
  PAYMENT_TONE,
  paymentsApi,
  paymentsQuery,
  supplierAccountQuery,
  type Obligation,
  type PaymentMethod,
} from '@/entities/payment'
import { useHasRole } from '@/entities/user'
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
  SegmentedControl,
  Skeleton,
  StatusBadge,
  TextField,
} from '@/shared/ui'

/** To'lash mumkin bo'lgan qoldiq: boshqa faol zayavkalarda band summa ayirib tashlanadi. */
const payable = (o: Obligation) => (o.status === 'BLOCKED' ? 0 : Math.max(Number(o.outstanding) - Number(o.reserved), 0))
const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

export default function SupplierAccountPage() {
  const { supplierId } = useParams({ from: '/shell/finance/suppliers/$supplierId' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { t, fmt } = useI18n()
  const canPay = useHasRole('accountant', 'admin')
  const { data: account, isPending, error } = useQuery(supplierAccountQuery(supplierId))
  const { data: history = [] } = useQuery(paymentsQuery(supplierId))
  // Tanlangan nakladnoy → summa (matn: foydalanuvchi kiritayotgan qiymat)
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [method, setMethod] = useState<PaymentMethod>('transfer')
  const [comment, setComment] = useState('')

  useEffect(() => telegram.backButton(() => navigate({ to: '/finance' })), [navigate])

  const create = useMutation({
    mutationFn: () =>
      paymentsApi.create({
        supplier_id: supplierId,
        method,
        comment: comment.trim() || undefined,
        lines: Object.entries(selected).map(([obligation_id, amount]) => ({ obligation_id, amount: decimal(amount) })),
      }),
    onSuccess: async ({ id }) => {
      telegram.haptic.notify('success')
      await queryClient.invalidateQueries({ queryKey: FINANCE_KEY })
      void navigate({ to: '/finance/payments/$paymentId', params: { paymentId: id } })
    },
  })

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  if (error || !account) return <EmptyState code="404" title={t.common.notFound} />

  const { balance, obligations } = account
  const total = Object.values(selected).reduce((sum, amount) => sum + (Number(decimal(amount)) || 0), 0)
  const invalid = Object.entries(selected).some(([id, amount]) => {
    const value = Number(decimal(amount))
    const obligation = obligations.find((o) => o.id === id)
    return !obligation || !(value > 0) || value > payable(obligation)
  })
  const toggle = (o: Obligation) =>
    setSelected((prev) => {
      const next = { ...prev }
      if (o.id in next) delete next[o.id]
      else next[o.id] = String(payable(o))
      return next
    })

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.finance.title} title={balance.supplier_name ?? '—'} />

      <Card index={`01/${t.finance.debt}`} title={<MoneyText value={Number(balance.debt)} className="text-2xl" />}>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-[13px]">
          {(
            [
              [t.finance.overdue, balance.overdue, Number(balance.overdue) > 0 && 'text-danger'],
              [t.finance.blocked, balance.blocked, Number(balance.blocked) > 0 && 'text-warning'],
              [t.finance.reserved, balance.reserved, false],
              [t.finance.freeLimit, balance.free_limit, balance.free_limit !== null && Number(balance.free_limit) < 0 && 'text-danger'],
            ] as const
          ).map(([label, value, tone]) => (
            <div key={label}>
              <dt className="text-text-3">{label}</dt>
              <dd className={cn('tnum font-semibold', tone)}>{value === null ? t.finance.noLimit : fmt.money(Number(value))}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <section className="mt-6 flex flex-col gap-2">
        <MonoLabel className="mb-1">{`02/${t.finance.invoices}`}</MonoLabel>
        {obligations.length === 0 && <EmptyState code="0" title={t.finance.noDebts} />}
        {obligations.map((o) => {
          const isSelected = o.id in selected
          const available = payable(o)
          return (
            <div
              key={o.id}
              className={cn(
                'rounded-row border bg-surface px-4 py-3 shadow-[var(--shadow-card)] transition-colors',
                isSelected ? 'border-[var(--accent-border)]' : 'border-border-soft',
              )}
            >
              <button
                type="button"
                disabled={!canPay || available === 0}
                className="flex w-full items-start gap-3 text-left disabled:cursor-default"
                onClick={() => toggle(o)}
              >
                {canPay && (
                  <span
                    className={cn(
                      'mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border',
                      isSelected ? 'border-transparent bg-accent text-black' : 'border-border',
                    )}
                  >
                    {o.status === 'BLOCKED' ? <Lock size={12} className="text-text-3" /> : isSelected && <Check size={14} />}
                  </span>
                )}
                <span className="min-w-0 flex-1">
                  <MonoLabel className="mb-1">{`${o.receipt_number} · ${o.store_name ?? '—'} · ${fmt.date(o.received_on)}`}</MonoLabel>
                  <span className={cn('block text-[13px]', o.overdue ? 'text-danger' : 'text-text-2')}>
                    {`${t.finance.due} ${fmt.date(o.due_date)}`}
                    {Number(o.paid) > 0 && ` · ${t.finance.paid} ${fmt.money(Number(o.paid))}`}
                    {Number(o.reserved) > 0 && ` · ${t.finance.reserved} ${fmt.money(Number(o.reserved))}`}
                  </span>
                </span>
                <span className="flex shrink-0 flex-col items-end gap-1">
                  <MoneyText value={Number(o.outstanding)} className="text-[14px]" />
                  <StatusBadge tone={o.overdue ? 'danger' : OBLIGATION_TONE[o.status]}>
                    {o.overdue ? t.finance.overdue : t.finance.obligationStatus[o.status]}
                  </StatusBadge>
                </span>
              </button>
              {o.status === 'BLOCKED' && <p className="mt-2 text-[12px] text-warning">{t.finance.blockedHint}</p>}
              {isSelected && (
                <div className="mt-3 border-t border-border-soft pt-3">
                  <TextField
                    label={t.finance.toPay}
                    inputMode="decimal"
                    suffix={t.common.currency}
                    value={selected[o.id]}
                    onChange={(e) => setSelected((prev) => ({ ...prev, [o.id]: e.target.value }))}
                  />
                </div>
              )}
            </div>
          )
        })}
      </section>

      {canPay && Object.keys(selected).length > 0 && (
        <section className="mt-6 flex flex-col gap-3">
          <MonoLabel>{t.finance.method}</MonoLabel>
          <SegmentedControl
            segments={(['transfer', 'cash'] as const).map((value) => ({ value, label: t.paymentMethod[value] }))}
            value={method}
            onChange={setMethod}
          />
          <TextField label={t.finance.comment} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="flex items-center justify-between">
            <MonoLabel>{`${t.finance.selected}: ${Object.keys(selected).length}`}</MonoLabel>
            <MoneyText value={total} className="text-lg" />
          </div>
          <FormError>{create.error && describeError(create.error, t)}</FormError>
          <LaserButton size="lg" block disabled={invalid} loading={create.isPending} onClick={() => create.mutate()}>
            {t.finance.create}
          </LaserButton>
        </section>
      )}

      {history.length > 0 && (
        <section className="mt-8 flex flex-col gap-2">
          <MonoLabel className="mb-1">{`03/${t.finance.supplierHistory}`}</MonoLabel>
          {history.map((p) => (
            <ListRow
              key={p.id}
              meta={`${p.number} · ${fmt.date(p.requested_at)} · ${t.paymentMethod[p.method]}`}
              title={<MoneyText value={Number(p.total)} />}
              badge={<StatusBadge tone={PAYMENT_TONE[p.status]}>{t.finance.paymentStatus[p.status]}</StatusBadge>}
              onClick={() => navigate({ to: '/finance/payments/$paymentId', params: { paymentId: p.id } })}
            />
          ))}
        </section>
      )}
    </div>
  )
}
