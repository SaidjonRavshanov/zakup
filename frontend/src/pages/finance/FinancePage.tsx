import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { balancesQuery, paymentsQuery, type PaymentStatus, type SupplierBalance } from '@/entities/payment'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Cells, Empty, Row, RowsSkeleton, Seg, Tag, status } from '@/shared/kit'

type Tab = 'debts' | 'pays'
type PayFilter = 'all' | PaymentStatus
const PAY_FILTERS: ReadonlyArray<PaymentStatus> = ['SUBMITTED', 'APPROVED', 'PAID', 'REJECTED', 'CANCELLED']

const sum = (items: SupplierBalance[], key: 'debt' | 'overdue') => items.reduce((total, item) => total + Number(item[key]), 0)

export default function FinancePage() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const { z, f } = useZk()
  const [tab, setTab] = useState<Tab>('debts')
  const [filter, setFilter] = useState<PayFilter>('all')
  const { data: balances = [], isPending } = useQuery(balancesQuery)
  const { data: payments = [], isPending: paymentsPending } = useQuery(paymentsQuery())

  // Avval muddati o'tganlar, keyin katta qarz
  const debts = balances
    .filter((b) => Number(b.debt) > 0)
    .sort((a, b) => Number(b.overdue) - Number(a.overdue) || Number(b.debt) - Number(a.debt))
  const shownPayments = filter === 'all' ? payments : payments.filter((p) => p.status === filter)
  const method = (m: 'cash' | 'transfer') => (m === 'cash' ? z.pm_cash : z.pm_bank)
  const openSupplier = (supplierId: string) => navigate({ to: '/finance/suppliers/$supplierId', params: { supplierId } })

  const meta = (b: SupplierBalance) => `${b.open_count} ${z.inv_n}${b.nearest_due ? ` · ${z.near_due} ${f.dt(b.nearest_due)}` : ''}`
  const flag = (b: SupplierBalance) => {
    if (Number(b.overdue) > 0) return <span className="text-danger">{`${z.overdue}: ${f.money(b.overdue)}`}</span>
    if (Number(b.blocked) > 0) return <span className="text-warn">{`${z.dispute}: ${f.money(b.blocked)}`}</span>
    return b.free_limit !== null ? `${z.free_limit}: ${f.cmp(b.free_limit)}` : z.no_limit
  }
  const dash = (value: string) => (Number(value) ? f.money(value) : '—')

  return (
    <div>
      <h1 className="m-0 mb-3 mt-2 text-[34px]">{z.finance}</h1>
      <Cells
        cols={2}
        items={[
          { label: z.debt, value: f.money(sum(debts, 'debt')) },
          { label: z.overdue, value: f.money(sum(debts, 'overdue')), color: 'var(--zk-danger)' },
        ]}
      />

      <Seg
        className="mt-4"
        options={[
          { value: 'debts', label: z.t_debts, count: isPending ? undefined : debts.length },
          { value: 'pays', label: z.t_pays, count: paymentsPending ? undefined : payments.length },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === 'debts' ? (
        isPending ? (
          <RowsSkeleton n={4} />
        ) : debts.length === 0 ? (
          <Empty title={t.finance.noDebts} hint={t.finance.noDebtsHint} />
        ) : (
          <>
            {/* Desktop — jadval */}
            <table className="table mt-3 hidden lg:table">
              <thead>
                <tr>
                  <th>{z.supplier}</th>
                  <th>{z.invoices}</th>
                  <th className="text-right">{z.overdue}</th>
                  <th className="text-right">{z.dispute}</th>
                  <th className="text-right">{z.in_pays}</th>
                  <th className="text-right">{z.debt}</th>
                </tr>
              </thead>
              <tbody>
                {debts.map((b) => (
                  <tr key={b.supplier_id} className="cursor-pointer" onClick={() => void openSupplier(b.supplier_id)}>
                    <td className="font-medium" style={{ padding: '12px 6.8px' }}>
                      {b.supplier_name ?? '—'}
                    </td>
                    <td className="text-n7">{meta(b)}</td>
                    <td className={Number(b.overdue) ? 'whitespace-nowrap text-right text-danger' : 'whitespace-nowrap text-right text-n7'}>
                      {dash(b.overdue)}
                    </td>
                    <td className="whitespace-nowrap text-right">{dash(b.blocked)}</td>
                    <td className="whitespace-nowrap text-right">{dash(b.reserved)}</td>
                    <td className="whitespace-nowrap text-right font-medium">{f.money(b.debt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Telefon — qatorlar */}
            <div className="lg:hidden">
              {debts.map((b) => (
                <button
                  key={b.supplier_id}
                  type="button"
                  onClick={() => void openSupplier(b.supplier_id)}
                  className="zk-hover grid min-h-[76px] w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-0.5 border-b border-line py-3 text-left text-ink"
                >
                  <div className="min-w-0">
                    <div className="text-[16px] font-medium">{b.supplier_name ?? '—'}</div>
                    <div className="text-[13px] text-n7">{meta(b)}</div>
                    <div className="text-[13px] text-n7">{flag(b)}</div>
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap text-[15px] font-medium">
                    {f.money(b.debt)}
                    <ChevronRight size={20} />
                  </div>
                </button>
              ))}
            </div>
          </>
        )
      ) : (
        <>
          <Seg
            className="mt-3"
            scroll
            size="sm"
            options={[
              { value: 'all', label: z.f_all },
              ...PAY_FILTERS.map((value) => ({
                value,
                label: status(z, 'payment', value).label,
                count: payments.filter((p) => p.status === value).length || undefined,
              })),
            ]}
            value={filter}
            onChange={setFilter}
          />
          {paymentsPending ? (
            <RowsSkeleton n={4} />
          ) : shownPayments.length === 0 ? (
            <Empty title={t.finance.noPayments} />
          ) : (
            shownPayments.map((p) => {
              const s = status(z, 'payment', p.status)
              return (
                <Row
                  key={p.id}
                  meta={`${p.number} · ${f.dt(p.requested_at)} · ${method(p.method)}`}
                  title={p.supplier_name ?? '—'}
                  amount={f.money(p.total)}
                  badge={<Tag tone={s.tone}>{s.label}</Tag>}
                  onClick={() => navigate({ to: '/finance/payments/$paymentId', params: { paymentId: p.id } })}
                />
              )
            })
          )}
        </>
      )}
    </div>
  )
}
