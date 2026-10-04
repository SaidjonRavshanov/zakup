import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate } from '@tanstack/react-router'
import { summaryQuery, type Summary } from '@/entities/analytics'
import { OrderRow, purchaseOrdersQuery } from '@/entities/purchase-order'
import { useHasRole } from '@/entities/user'
import { useI18n } from '@/shared/i18n'
import { Card, MonoLabel, PageHeader, Skeleton, StatTile } from '@/shared/ui'
import { ApiStatus } from '@/widgets/api-status/ApiStatus'

const today = () => new Date().toISOString().slice(0, 10)

export default function DashboardPage() {
  const navigate = useNavigate()
  const { t, fmt } = useI18n()
  const canAnalyze = useHasRole('buyer', 'approver', 'admin', 'auditor', 'accountant')
  const { data: summary } = useQuery({ ...summaryQuery, enabled: canAnalyze })
  const { data: orders, isPending } = useQuery(purchaseOrdersQuery())
  const arriving = orders?.filter((po) => po.deliveryDate === today() && po.status !== 'CANCELLED') ?? []
  const arrivingTotal = arriving.reduce((sum, po) => sum + po.totalAmount, 0)

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.modules.procurement} title={t.dashboard.title} action={<ApiStatus />} />

      {/* Hero: 3D shisha plita ustida asosiy son */}
      <section className="relative mb-3 [perspective:1000px]">
        <div
          aria-hidden
          className="glow absolute inset-x-6 -bottom-3 top-6 -z-10 rounded-card border border-border bg-accent-wash [transform:rotateX(15deg)]"
        />
        <div className="rounded-card border-[6px] border-text bg-surface p-5 shadow-[var(--shadow-card)]">
          <MonoLabel>{`01/${canAnalyze ? t.dashboard.monthPurchase : t.dashboard.todayPurchase}`}</MonoLabel>
          <div className="tnum mt-6 font-display text-[clamp(2.6rem,14vw,4.5rem)] font-extrabold uppercase leading-[0.85] tracking-[-0.05em]">
            {fmt.moneyCompact(canAnalyze ? Number(summary?.purchases ?? 0) : arrivingTotal)}
          </div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.3em] text-text-3">
            {canAnalyze && summary
              ? `${t.common.currency} · ${t.dashboard.receipts(summary.receipts)}`
              : `${t.common.currency} · ${t.dashboard.deliveries(arriving.length)}`}
          </div>
          {canAnalyze && summary && <HeroFooter summary={summary} />}
        </div>
      </section>

      {canAnalyze &&
        (summary ? (
          <section className="grid grid-cols-2 gap-3">
            <StatTile label={`02/${t.dashboard.pendingApproval}`} value={summary.pending_requests} unit={t.dashboard.pcs} />
            <StatTile label={`03/${t.dashboard.inTransit}`} value={summary.orders_in_transit} unit={t.dashboard.pcs} />
            <StatTile
              label={`04/${t.dashboard.priceChange}`}
              value={summary.price_change_pct === null ? '—' : signed(Number(summary.price_change_pct), fmt.qty)}
              unit={summary.price_change_pct === null ? undefined : '%'}
            />
            <StatTile label={`05/${t.dashboard.savings}`} value={fmt.moneyCompact(Number(summary.savings))} unit={t.common.currency} />
            <StatTile label={`06/${t.dashboard.overpay}`} value={fmt.moneyCompact(Number(summary.overpay))} unit={t.common.currency} />
            <StatTile label={`07/${t.dashboard.defect}`} value={fmt.moneyCompact(Number(summary.defect_loss))} unit={t.common.currency} />
            <StatTile label={`08/${t.dashboard.debt}`} value={fmt.moneyCompact(Number(summary.debt))} unit={t.common.currency} />
            <StatTile
              label={`09/${t.dashboard.overdue}`}
              value={fmt.moneyCompact(Number(summary.overdue))}
              unit={t.common.currency}
              className={Number(summary.overdue) > 0 ? 'border-danger/40' : undefined}
            />
          </section>
        ) : (
          <Skeleton className="h-64" />
        ))}

      {canAnalyze && summary && (summary.open_disputes > 0 || summary.auto_drafts > 0) && (
        <div className="mt-3 flex flex-col gap-2">
          {summary.auto_drafts > 0 && (
            <Link to="/requests">
              <Card index={t.dashboard.autoDrafts} title={String(summary.auto_drafts)} interactive />
            </Link>
          )}
          {summary.open_disputes > 0 && (
            <Link to="/receiving">
              <Card index={t.dashboard.disputes} title={String(summary.open_disputes)} interactive />
            </Link>
          )}
        </div>
      )}

      {canAnalyze && (
        <Link to="/analytics" className="mt-3 block">
          <Card index={t.analytics.meta} title={t.analytics.title} interactive>
            <p className="mt-1 text-sm text-text-2">{t.analytics.hint}</p>
          </Card>
        </Link>
      )}

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <MonoLabel>{t.dashboard.arrivingToday}</MonoLabel>
          <MonoLabel>{arriving.length}</MonoLabel>
        </div>
        <div className="flex flex-col gap-2">
          {isPending
            ? Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
            : arriving.map((po) => (
                <OrderRow key={po.id} order={po} onClick={() => navigate({ to: '/receiving/$orderId', params: { orderId: po.id } })} />
              ))}
        </div>
      </section>
    </div>
  )
}

function signed(value: number, format: (n: number) => string): string {
  return value > 0 ? `+${format(value)}` : format(value)
}

function HeroFooter({ summary }: { summary: Summary }) {
  const { t, fmt } = useI18n()
  const prev = Number(summary.purchases_prev)
  const delta = prev > 0 ? Math.round((Number(summary.purchases) / prev - 1) * 1000) / 10 : null
  return (
    <div className="mt-6 flex items-end justify-between border-t border-border pt-4">
      <div>
        <MonoLabel className="mb-2">{t.dashboard.vsPrev}</MonoLabel>
        <span className="tnum font-display text-[22px] font-bold">{delta === null ? '—' : `${signed(delta, fmt.qty)}%`}</span>
      </div>
      <div className="text-right">
        <MonoLabel className="mb-2">{t.dashboard.arrivingToday}</MonoLabel>
        <span className="tnum font-display text-[22px] font-bold">{summary.arriving_today}</span>
      </div>
    </div>
  )
}
