import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { PAYMENT_TONE, balancesQuery, paymentsQuery, type SupplierBalance } from '@/entities/payment'
import { useI18n } from '@/shared/i18n'
import { EmptyState, ListRow, MoneyText, PageHeader, SegmentedControl, Skeleton, StatTile, StatusBadge } from '@/shared/ui'

type Tab = 'debts' | 'payments'

const sum = (items: SupplierBalance[], key: 'debt' | 'overdue' | 'blocked') =>
  items.reduce((total, item) => total + Number(item[key]), 0)

export default function FinancePage() {
  const navigate = useNavigate()
  const { t, fmt } = useI18n()
  const [tab, setTab] = useState<Tab>('debts')
  const { data: balances = [], isPending } = useQuery(balancesQuery)
  const { data: payments = [], isPending: paymentsPending } = useQuery({ ...paymentsQuery(), enabled: tab === 'payments' })
  const awaiting = payments.filter((p) => p.status === 'SUBMITTED' || p.status === 'APPROVED').length

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.modules.finance} title={t.finance.title} />

      <div className="grid grid-cols-2 gap-2">
        <StatTile label={t.finance.debt} value={fmt.money(sum(balances, 'debt'))} unit={t.common.currency} />
        <StatTile label={t.finance.overdue} value={fmt.money(sum(balances, 'overdue'))} unit={t.common.currency} />
      </div>

      <SegmentedControl
        className="-mx-4 mt-4 px-4"
        segments={(['debts', 'payments'] as const).map((value) => ({
          value,
          label: t.finance.tabs[value],
          count: value === 'debts' ? balances.length : awaiting || undefined,
        }))}
        value={tab}
        onChange={setTab}
      />

      <div className="mt-4 flex flex-col gap-2">
        {tab === 'debts' ? (
          isPending ? (
            Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
          ) : balances.length === 0 ? (
            <EmptyState code="0" title={t.finance.noDebts} description={t.finance.noDebtsHint} />
          ) : (
            balances.map((b) => {
              const overdue = Number(b.overdue)
              return (
                <ListRow
                  key={b.supplier_id}
                  meta={`${t.finance.invoices}: ${b.open_count}${b.nearest_due ? ` · ${t.finance.due} ${fmt.date(b.nearest_due)}` : ''}`}
                  title={b.supplier_name ?? '—'}
                  subtitle={
                    overdue > 0 ? (
                      <span className="text-danger">{`${t.finance.overdue}: ${fmt.money(overdue)}`}</span>
                    ) : Number(b.blocked) > 0 ? (
                      `${t.finance.blocked}: ${fmt.money(Number(b.blocked))}`
                    ) : b.free_limit !== null ? (
                      `${t.finance.freeLimit}: ${fmt.money(Number(b.free_limit))}`
                    ) : undefined
                  }
                  badge={
                    overdue > 0 ? (
                      <StatusBadge tone="danger">{t.finance.overdue}</StatusBadge>
                    ) : Number(b.blocked) > 0 ? (
                      <StatusBadge tone="warning">{t.finance.blocked}</StatusBadge>
                    ) : undefined
                  }
                  trailing={<MoneyText value={Number(b.debt)} className="text-[13px]" />}
                  onClick={() => navigate({ to: '/finance/suppliers/$supplierId', params: { supplierId: b.supplier_id } })}
                />
              )
            })
          )
        ) : paymentsPending ? (
          Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
        ) : payments.length === 0 ? (
          <EmptyState code="0" title={t.finance.noPayments} />
        ) : (
          payments.map((p) => (
            <ListRow
              key={p.id}
              meta={`${p.number} · ${fmt.date(p.requested_at)} · ${t.paymentMethod[p.method]}`}
              title={p.supplier_name ?? '—'}
              badge={<StatusBadge tone={PAYMENT_TONE[p.status]}>{t.finance.paymentStatus[p.status]}</StatusBadge>}
              trailing={<MoneyText value={Number(p.total)} className="text-[13px]" />}
              onClick={() => navigate({ to: '/finance/payments/$paymentId', params: { paymentId: p.id } })}
            />
          ))
        )}
      </div>
    </div>
  )
}
