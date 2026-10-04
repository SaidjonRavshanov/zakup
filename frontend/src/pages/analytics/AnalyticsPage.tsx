import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import {
  controlQuery,
  pct,
  priceHistoryQuery,
  pricesQuery,
  stockQuery,
  supplierRatingQuery,
  type ControlItem,
  type ProductPrice,
  type SupplierRating,
} from '@/entities/analytics'
import { useHasRole } from '@/entities/user'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { EmptyState, MoneyText, MonoLabel, PageHeader, SegmentedControl, Skeleton, StatTile, StatusBadge, type Tone } from '@/shared/ui'
import { Sparkline } from '@/shared/ui/Sparkline'

type Tab = 'suppliers' | 'prices' | 'stock' | 'control'

/** Davr [from, to) — oxirgi kun: to - 1. */
const lastDay = (to: string) => new Date(Date.parse(`${to}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10)

export default function AnalyticsPage() {
  const { t } = useI18n()
  const isController = useHasRole('auditor', 'approver', 'admin')
  const tabs: Tab[] = isController ? ['suppliers', 'prices', 'stock', 'control'] : ['suppliers', 'prices', 'stock']
  const [tab, setTab] = useState<Tab>('suppliers')

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.analytics.meta} title={t.analytics.title} />
      <SegmentedControl
        className="-mx-4 px-4"
        segments={tabs.map((value) => ({ value, label: t.analytics.tabs[value] }))}
        value={tab}
        onChange={setTab}
      />
      <div className="mt-4">
        {tab === 'suppliers' && <Suppliers />}
        {tab === 'prices' && <Prices />}
        {tab === 'stock' && <Stock />}
        {tab === 'control' && <Control />}
      </div>
    </div>
  )
}

function Loading() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 4 }, (_, i) => (
        <Skeleton key={i} className="h-[76px]" />
      ))}
    </div>
  )
}

const scoreTone = (score: number): Tone => (score >= 80 ? 'accent' : score >= 60 ? 'warning' : 'danger')

function Suppliers() {
  const { t, fmt } = useI18n()
  const { data, isPending } = useQuery(supplierRatingQuery)
  if (isPending) return <Loading />
  if (!data?.items.length) return <EmptyState code="0" title={t.analytics.empty} description={t.analytics.periodHint} />
  return (
    <div className="flex flex-col gap-2">
      <MonoLabel className="mb-1">{t.analytics.period(fmt.date(data.period.date_from), fmt.date(lastDay(data.period.date_to)))}</MonoLabel>
      {data.items.map((s) => (
        <SupplierRow key={s.supplier_id} s={s} />
      ))}
    </div>
  )
}

function SupplierRow({ s }: { s: SupplierRating }) {
  const { t, fmt } = useI18n()
  const metrics: Array<[string, number, boolean]> = [
    [t.analytics.short, pct(s.short_rate), Number(s.short_rate) > 0],
    [t.analytics.defectRate, pct(s.defect_rate), Number(s.defect_rate) > 0],
    [t.analytics.priceRate, pct(s.price_rate), Number(s.price_rate) > 0],
    [t.analytics.onTime, pct(s.on_time_rate), Number(s.on_time_rate) < 1],
  ]
  return (
    <div className="rounded-row border border-border-soft bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-[15px] font-semibold">{s.supplier_name}</div>
          <div className="mt-0.5 text-[12px] text-text-2">
            {`${t.analytics.orders}: ${s.orders} · ${t.analytics.receipts}: ${s.receipts}`}
            {s.response_hours !== null && ` · ${t.analytics.response(fmt.qty(Number(s.response_hours)))}`}
          </div>
        </div>
        <div className="shrink-0 text-right">
          {s.score !== null ? (
            <StatusBadge tone={scoreTone(Number(s.score))}>{`${s.score} / 100`}</StatusBadge>
          ) : (
            <StatusBadge>{t.analytics.noScore}</StatusBadge>
          )}
          <MoneyText value={Number(s.amount)} className="mt-1 block text-[12px] font-normal text-text-2" />
        </div>
      </div>
      {s.receipts > 0 && (
        <dl className="mt-2 grid grid-cols-4 gap-2 text-[11px]">
          {metrics.map(([label, value, bad]) => (
            <div key={label}>
              <dt className="text-text-3">{label}</dt>
              <dd className={cn('tnum font-semibold', bad && 'text-warning')}>{`${fmt.qty(value)}%`}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  )
}

function Prices() {
  const { t, fmt } = useI18n()
  const { data, isPending } = useQuery(pricesQuery)
  const [open, setOpen] = useState<string | null>(null)
  if (isPending) return <Loading />
  if (!data?.items.length) return <EmptyState code="0" title={t.analytics.empty} description={t.analytics.periodHint} />
  const overpay = data.items.reduce((sum, p) => sum + Number(p.overpay), 0)
  return (
    <div className="flex flex-col gap-2">
      <StatTile label={t.analytics.lostVsBest} value={fmt.moneyCompact(overpay)} unit={t.common.currency} className="mb-2" />
      {data.items.map((p) => (
        <PriceRow key={p.product_id} p={p} open={open === p.product_id} onToggle={() => setOpen(open === p.product_id ? null : p.product_id)} />
      ))}
    </div>
  )
}

function PriceRow({ p, open, onToggle }: { p: ProductPrice; open: boolean; onToggle: () => void }) {
  const { t, fmt } = useI18n()
  const unit = t.units[p.base_unit] ?? p.base_unit
  const change = p.change_pct === null ? null : Number(p.change_pct)
  return (
    <div className="rounded-row border border-border-soft bg-surface shadow-[var(--shadow-card)]">
      <button type="button" className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left" onClick={onToggle}>
        <span className="min-w-0">
          <span className="block truncate text-[15px] font-semibold">{p.product_name}</span>
          <span className="block text-[12px] text-text-2">
            {`${fmt.money(Number(p.avg_price))} / ${unit} · ${fmt.qty(Number(p.qty))} ${unit}`}
          </span>
          {p.best_price !== null && Number(p.overpay) > 0 && (
            <span className="block text-[12px] text-warning">
              {t.analytics.bestOffer(fmt.money(Number(p.best_price)), p.best_supplier ?? '—', fmt.money(Number(p.overpay)))}
            </span>
          )}
        </span>
        <span className="shrink-0 text-right">
          <MoneyText value={Number(p.amount)} className="text-[13px]" />
          {change !== null && (
            <span className={cn('tnum block text-[12px] font-semibold', change > 0 ? 'text-danger' : 'text-accent-text')}>
              {`${change > 0 ? '+' : ''}${fmt.qty(change)}%`}
            </span>
          )}
        </span>
      </button>
      {open && <PriceHistory productId={p.product_id} unit={unit} />}
    </div>
  )
}

function PriceHistory({ productId, unit }: { productId: string; unit: string }) {
  const { t, fmt } = useI18n()
  const { data = [], isPending } = useQuery(priceHistoryQuery(productId))
  if (isPending) return <Skeleton className="mx-4 mb-3 h-14" />
  const receipts = data.filter((point) => point.source === 'receipt')
  const series = (receipts.length >= 2 ? receipts : data).map((point) => Number(point.price))
  return (
    <div className="border-t border-border-soft px-4 py-3">
      <Sparkline values={series} className="w-full" />
      <ul className="mt-2 flex flex-col gap-0.5 text-[11px] text-text-2">
        {data.slice(-6).map((point, i) => (
          <li key={`${point.day}-${i}`} className="tnum flex justify-between gap-3">
            <span className="truncate">{`${fmt.date(point.day)} · ${point.supplier_name}`}</span>
            <span>{`${fmt.money(Number(point.price))} / ${unit}${point.source === 'receipt' ? ` · ${t.analytics.fact}` : ''}`}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Stock() {
  const { t, fmt } = useI18n()
  const { data, isPending } = useQuery(stockQuery)
  if (isPending) return <Loading />
  if (!data?.items.length) return <EmptyState code="0" title={t.analytics.noStock} description={t.analytics.noStockHint} />
  return (
    <div className="flex flex-col gap-2">
      <div className="mb-2 grid grid-cols-2 gap-2">
        <StatTile label={t.analytics.stockValue} value={fmt.moneyCompact(Number(data.total_value))} unit={t.common.currency} />
        <StatTile label={t.analytics.deadValue} value={fmt.moneyCompact(Number(data.dead_value))} unit={t.common.currency} />
      </div>
      {data.items.map((s) => {
        const unit = t.units[s.base_unit] ?? s.base_unit
        return (
          <div
            key={`${s.store_id}-${s.product_id}`}
            className="flex items-center justify-between gap-3 rounded-row border border-border-soft bg-surface px-4 py-3 shadow-[var(--shadow-card)]"
          >
            <div className="min-w-0">
              <MonoLabel className="mb-1 truncate">{s.store_name}</MonoLabel>
              <div className="truncate text-[15px] font-semibold">{s.product_name}</div>
              <div className="text-[12px] text-text-2">
                {`${fmt.qty(Number(s.qty))} ${unit} · `}
                {s.days_cover !== null ? t.analytics.daysCover(fmt.qty(Number(s.days_cover))) : t.analytics.noConsumption}
              </div>
            </div>
            <div className="shrink-0 text-right">
              <MoneyText value={Number(s.value)} className="text-[13px]" />
              {s.dead && <StatusBadge tone="warning">{t.analytics.dead}</StatusBadge>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

const CONTROL_TONE: Record<ControlItem['kind'], Tone> = {
  price_change: 'warning',
  discrepancy: 'warning',
  role_conflict: 'danger',
  manual_increase: 'info',
  payment_without_proof: 'danger',
}

function Control() {
  const { t, fmt } = useI18n()
  const navigate = useNavigate()
  const { data, isPending } = useQuery(controlQuery)
  if (isPending) return <Loading />
  if (!data?.items.length) return <EmptyState code="0" title={t.analytics.controlClean} description={t.analytics.periodHint} />
  const open = (item: ControlItem) => {
    if (item.kind === 'price_change') void navigate({ to: '/orders/$orderId', params: { orderId: item.entity_id } })
    else if (item.kind === 'discrepancy') void navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: item.entity_id } })
    else if (item.kind === 'payment_without_proof') void navigate({ to: '/finance/payments/$paymentId', params: { paymentId: item.entity_id } })
    else void navigate({ to: '/requests/$requestId', params: { requestId: item.entity_id } })
  }
  return (
    <div className="flex flex-col gap-2">
      {data.items.map((item) => (
        <button
          key={`${item.kind}-${item.entity_id}`}
          type="button"
          onClick={() => open(item)}
          className="flex items-start justify-between gap-3 rounded-row border border-border-soft bg-surface px-4 py-3 text-left shadow-[var(--shadow-card)]"
        >
          <span className="min-w-0">
            <MonoLabel className="mb-1">{`${item.number} · ${fmt.date(item.at)}`}</MonoLabel>
            <span className="block truncate text-[15px] font-semibold">{item.title}</span>
            {item.detail && <span className="block truncate text-[12px] text-text-2">{controlDetail(item, t)}</span>}
          </span>
          <span className="shrink-0 text-right">
            <StatusBadge tone={CONTROL_TONE[item.kind]}>{t.analytics.control[item.kind]}</StatusBadge>
            {item.amount !== null && <MoneyText value={Number(item.amount)} className="mt-1 block text-[12px] font-normal" />}
          </span>
        </button>
      ))}
    </div>
  )
}

function controlDetail(item: ControlItem, t: ReturnType<typeof useI18n>['t']): string {
  if (item.kind === 'discrepancy') {
    return item.detail
      .split(', ')
      .map((kind) => t.receiving.discrepancy[kind as keyof typeof t.receiving.discrepancy] ?? kind)
      .join(', ')
  }
  if (item.kind === 'payment_without_proof') return t.paymentMethod[item.detail as 'cash' | 'transfer'] ?? item.detail
  if (item.kind === 'role_conflict') return t.analytics.decision[item.detail as keyof typeof t.analytics.decision] ?? item.detail
  return item.detail
}
