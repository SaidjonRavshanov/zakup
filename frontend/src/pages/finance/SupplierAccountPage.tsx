import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Lock } from 'lucide-react'
import { useState } from 'react'
import { FINANCE_KEY, paymentsApi, paymentsQuery, supplierAccountQuery, type Obligation, type PaymentMethod } from '@/entities/payment'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Blueprint, Check, Empty, Field, Input, RowsSkeleton, Section, Seg, Tag, status, toast, usePageActions } from '@/shared/kit'

/** To'lash mumkin bo'lgan qoldiq: boshqa faol zayavkalarda band summa ayirib tashlanadi. */
const payable = (o: Obligation) => (o.status === 'BLOCKED' ? 0 : Math.max(Number(o.outstanding) - Number(o.reserved), 0))
const decimal = (value: string) => value.replace(/\s/g, '').replace(',', '.').replace(/[^\d.]/g, '')

export default function SupplierAccountPage() {
  const { supplierId } = useParams({ from: '/shell/finance/suppliers/$supplierId' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const { z, f } = useZk()
  const canPay = useHasRole('accountant', 'admin')
  const { data: account, isPending, error } = useQuery(supplierAccountQuery(supplierId))
  const { data: history = [] } = useQuery(paymentsQuery(supplierId))
  // Tanlangan nakladnoy → summa (matn: foydalanuvchi kiritayotgan qiymat)
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [method, setMethod] = useState<PaymentMethod>('transfer')
  const [comment, setComment] = useState('')

  const create = useMutation({
    mutationFn: () =>
      paymentsApi.create({
        supplier_id: supplierId,
        method,
        comment: comment.trim() || undefined,
        lines: Object.entries(selected).map(([obligation_id, amount]) => ({ obligation_id, amount: decimal(amount) })),
      }),
    onSuccess: async ({ id }) => {
      toast(z.toast_pay_created)
      setSelected({})
      await queryClient.invalidateQueries({ queryKey: FINANCE_KEY })
      void navigate({ to: '/finance/payments/$paymentId', params: { paymentId: id } })
    },
  })

  const obligations = account?.obligations ?? []
  const ids = Object.keys(selected)
  const total = Object.values(selected).reduce((sum, amount) => sum + (Number(decimal(amount)) || 0), 0)
  const invalid = Object.entries(selected).some(([id, amount]) => {
    const value = Number(decimal(amount))
    const obligation = obligations.find((o) => o.id === id)
    return !obligation || !(value > 0) || value > payable(obligation)
  })

  usePageActions({
    primary:
      canPay && ids.length > 0
        ? { label: z.a_create_pay, onClick: () => create.mutate(), disabled: invalid || total <= 0, loading: create.isPending }
        : null,
  })

  if (isPending) return <RowsSkeleton n={5} />
  if (error || !account) return <Empty title={z.not_found} />

  const { balance } = account
  const toggle = (o: Obligation) =>
    setSelected((prev) => {
      const next = { ...prev }
      if (o.id in next) delete next[o.id]
      else next[o.id] = String(payable(o))
      return next
    })
  const methodLabel = (m: PaymentMethod, short = false) =>
    m === 'cash' ? (short ? z.pm_cash : z.pay_cash) : short ? z.pm_bank : z.pay_bank
  const freeNegative = balance.free_limit !== null && Number(balance.free_limit) < 0
  const stats: Array<[string, string, string | undefined]> = [
    [z.overdue, f.money(balance.overdue), Number(balance.overdue) > 0 ? 'var(--zk-danger)' : undefined],
    [z.dispute, f.money(balance.blocked), Number(balance.blocked) > 0 ? 'var(--zk-warn)' : undefined],
    [z.in_pays, f.money(balance.reserved), undefined],
    [z.free_limit, balance.free_limit === null ? z.no_limit : f.money(balance.free_limit), freeNegative ? 'var(--zk-danger)' : undefined],
  ]

  return (
    <div>
      <div className="pt-2">
        <div className="text-[14px] text-n7">{z.supplier}</div>
        <h1 className="m-0 text-[32px]">{balance.supplier_name ?? '—'}</h1>
      </div>

      <Blueprint className="mt-4 p-4">
        <div className="text-[14px] text-n7">{z.debt}</div>
        <div className="font-head text-[44px] leading-[1.05]" style={{ fontWeight: 600 }}>
          {f.money(balance.debt)}
        </div>
        <div className="mt-3 grid gap-x-4 gap-y-2.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}>
          {stats.map(([label, value, color]) => (
            <div key={label}>
              <div className="text-[13px] text-n7">{label}</div>
              <div className="whitespace-nowrap text-[16px] font-medium" style={{ color: color ?? 'var(--color-text)' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      </Blueprint>

      <Section>{z.invoices}</Section>
      {obligations.length === 0 && <Empty title={t.finance.noDebts} />}
      {obligations.map((o) => {
        const isSelected = o.id in selected
        const locked = o.status === 'BLOCKED'
        const canSel = canPay && !locked && payable(o) > 0
        const s = status(z, 'invoice', o.overdue ? 'OVERDUE' : o.status)
        const extra = [
          Number(o.paid) > 0 ? `${z.paid_l} ${f.money(o.paid)}` : '',
          Number(o.reserved) > 0 ? `${z.in_pays} ${f.money(o.reserved)}` : '',
        ]
          .filter(Boolean)
          .join(' · ')
        return (
          <div key={o.id} className="flex gap-1 border-b border-line py-3">
            {canSel && <Check on={isSelected} onToggle={() => toggle(o)} label={o.receipt_number} />}
            {locked && (
              <span className="w-10 shrink-0 pt-0.5 text-warn">
                <Lock size={20} />
              </span>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex justify-between gap-3">
                <button
                  type="button"
                  className="min-w-0 truncate text-left text-[13px] text-n7 hover:underline"
                  onClick={() => navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: o.receipt_id } })}
                >
                  {`${o.receipt_number} · ${o.store_name ?? '—'} · ${f.dt(o.received_on)}`}
                </button>
                <Tag tone={s.tone}>{s.label}</Tag>
              </div>
              <div className="mt-0.5 flex items-baseline justify-between gap-3">
                <div className={o.overdue ? 'text-[14px] text-danger' : 'text-[14px] text-n7'}>{`${z.due} ${f.dt(o.due_date)}`}</div>
                <div className="whitespace-nowrap text-[16px] font-medium">{f.money(o.outstanding)}</div>
              </div>
              {extra && <div className="text-[13px] text-n7">{extra}</div>}
              {locked && <div className="text-[13px] text-warn">{z.locked_dispute}</div>}
              {isSelected && (
                <Field label={z.to_pay} className="mt-2">
                  <Input
                    inputMode="decimal"
                    value={selected[o.id]}
                    invalid={!(Number(decimal(selected[o.id] ?? '')) > 0) || Number(decimal(selected[o.id] ?? '')) > payable(o)}
                    onChange={(e) => setSelected((prev) => ({ ...prev, [o.id]: e.target.value }))}
                  />
                </Field>
              )}
            </div>
          </div>
        )
      })}

      {canPay && ids.length > 0 && (
        <>
          <div className="mb-2 mt-5 text-[13px] font-medium text-n7">{z.pay_method}</div>
          <Seg
            options={(['transfer', 'cash'] as const).map((value) => ({ value, label: methodLabel(value) }))}
            value={method}
            onChange={setMethod}
          />
          <Field label={z.comment} className="mt-3">
            <Input maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
          </Field>
          <div className="mt-3 text-[15px] font-medium">{`${z.selected}: ${ids.length} · ${f.money(total)}`}</div>
          {create.error && <Banner tone="danger">{describeError(create.error, t)}</Banner>}
        </>
      )}

      {history.length > 0 && (
        <>
          <Section>{z.pay_history}</Section>
          {history.map((p) => {
            const s = status(z, 'payment', p.status)
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => navigate({ to: '/finance/payments/$paymentId', params: { paymentId: p.id } })}
                className="zk-hover flex min-h-14 w-full items-center justify-between gap-3 border-b border-line text-left text-ink"
              >
                <span className="text-[14px]">{`${p.number} · ${f.dt(p.requested_at)} · ${methodLabel(p.method, true)}`}</span>
                <span className="flex items-center gap-2">
                  <span className="whitespace-nowrap text-[15px] font-medium">{f.money(p.total)}</span>
                  <Tag tone={s.tone}>{s.label}</Tag>
                </span>
              </button>
            )
          })}
        </>
      )}
    </div>
  )
}
