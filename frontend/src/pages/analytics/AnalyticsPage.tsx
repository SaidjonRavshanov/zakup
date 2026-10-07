/** Analitika (prototip "analytics", vmAnalytics): davr, bo'limlar, yetkazib beruvchilar reytingi, narxlar, ombor, nazorat. */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ChevronDown, ChevronRight, ChevronUp } from 'lucide-react'
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
import { useZk, type Zk, type ZkKey } from '@/shared/i18n/use-zk'
import { Cells, Empty, PageHead, RowsSkeleton, Seg, Skeleton, Tag } from '@/shared/kit'
import { L } from './i18n'
import { Sparkline } from './Sparkline'

type Tab = 'suppliers' | 'prices' | 'stock' | 'control'

/** Davr [from, to) — oxirgi kun: to - 1. */
const lastDay = (to: string) => new Date(Date.parse(`${to}T00:00:00Z`) - 86_400_000).toISOString().slice(0, 10)

const MUTED = 'var(--color-neutral-700)'
const OK = 'var(--color-accent-700)'
const WARN = 'var(--zk-warn)'
const DANGER = 'var(--zk-danger)'

export default function AnalyticsPage() {
  const { z, f } = useZk()
  const isController = useHasRole('auditor', 'approver', 'admin')
  const [tab, setTab] = useState<Tab>('suppliers')
  const { data: rating } = useQuery(supplierRatingQuery)

  const options: Array<{ value: Tab; label: string }> = [
    { value: 'suppliers', label: z.an_sup },
    { value: 'prices', label: z.an_price },
    { value: 'stock', label: z.an_stock },
  ]
  if (isController) options.push({ value: 'control', label: z.an_ctl })

  const period = rating ? `${f.dt(rating.period.date_from)} — ${f.dt(lastDay(rating.period.date_to))}` : z.period30

  return (
    <div className="mx-auto w-full max-w-[1040px]">
      <PageHead title={z.analytics} aside={<span className="text-[14px] text-n7">{period}</span>} />
      <Seg className="mt-3" scroll options={options} value={tab} onChange={setTab} />
      {tab === 'suppliers' && <Suppliers />}
      {tab === 'prices' && <Prices />}
      {tab === 'stock' && <Stock />}
      {tab === 'control' && <Control />}
    </div>
  )
}

function Loading() {
  return (
    <div className="mt-3">
      <RowsSkeleton n={4} />
    </div>
  )
}

// ---------------------------------------------------------------- yetkazib beruvchilar

function scoreView(score: SupplierRating['score'], z: Zk, noScore: string) {
  if (score === null) return { value: '—', label: noScore, color: MUTED }
  const n = Number(score)
  return {
    value: String(Math.round(n)),
    label: n >= 80 ? z.sc_good : n >= 60 ? z.sc_mid : z.sc_bad,
    color: n >= 80 ? OK : n >= 60 ? WARN : DANGER,
  }
}

function Suppliers() {
  const { t } = useI18n()
  const { z, f, locale } = useZk()
  const { data, isPending } = useQuery(supplierRatingQuery)
  if (isPending) return <Loading />
  if (!data?.items.length) return <Empty title={t.analytics.empty} hint={z.period30} />

  const rate = (v: string) => `${f.n(pct(v), 1)}%`
  const resp = (s: SupplierRating) => (s.response_hours === null ? '—' : `${f.n(Number(s.response_hours), 1)} ${L[locale].hours}`)

  return (
    <>
      {/* desktop: jadval */}
      <table className="zk-table mt-3 hidden min-[900px]:table">
        <thead>
          <tr>
            <th>{z.supplier}</th>
            <th>{z.score}</th>
            <th>{z.orders_rc}</th>
            <th>{z.resp_time}</th>
            <th className="text-right">{z.m_short}</th>
            <th className="text-right">{z.m_defect}</th>
            <th className="text-right">{z.m_price}</th>
            <th className="text-right">{z.m_ontime}</th>
            <th className="text-right">{z.sum_l}</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((s) => {
            const sc = scoreView(s.score, z, L[locale].noScore)
            return (
              <tr key={s.supplier_id}>
                <td className="font-medium" style={{ padding: '12px 6.8px' }}>
                  {s.supplier_name}
                </td>
                <td className="whitespace-nowrap">
                  <span className="font-semibold" style={{ color: sc.color }}>
                    {sc.value}
                  </span>{' '}
                  <span className="text-[12px] text-n7">{sc.label}</span>
                </td>
                <td>{`${s.orders} / ${s.receipts}`}</td>
                <td className="whitespace-nowrap">{resp(s)}</td>
                <td className="text-right">{rate(s.short_rate)}</td>
                <td className="text-right">{rate(s.defect_rate)}</td>
                <td className="text-right">{rate(s.price_rate)}</td>
                <td className="text-right">{rate(s.on_time_rate)}</td>
                <td className="whitespace-nowrap text-right">{f.money(s.amount)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* telefon: qatorlar */}
      <div className="min-[900px]:hidden">
        {data.items.map((s) => {
          const sc = scoreView(s.score, z, L[locale].noScore)
          const metrics: Array<[string, string]> = [
            [z.m_short, rate(s.short_rate)],
            [z.m_defect, rate(s.defect_rate)],
            [z.m_price, rate(s.price_rate)],
            [z.m_ontime, rate(s.on_time_rate)],
          ]
          return (
            <div key={s.supplier_id} className="grid grid-cols-[60px_minmax(0,1fr)] gap-3 border-b border-line py-3.5">
              <div
                className="flex h-[60px] flex-col items-center justify-center"
                style={{ border: `1px solid ${sc.color}`, color: sc.color }}
              >
                <span className="font-head text-[26px] leading-none" style={{ fontWeight: 600 }}>
                  {sc.value}
                </span>
                <span className="text-center text-[11px] leading-tight">{sc.label}</span>
              </div>
              <div className="min-w-0">
                <div className="flex justify-between gap-2">
                  <span className="text-[16px] font-medium">{s.supplier_name}</span>
                  <span className="whitespace-nowrap text-[14px]">{`${f.cmp(s.amount)} ${z.sum}`}</span>
                </div>
                <div className="text-[13px] text-n7">
                  {`${s.orders} ${z.orders_n} · ${s.receipts} ${z.receipts_n} · ${z.resp_time} ${resp(s)}`}
                </div>
                {s.receipts > 0 && (
                  <div className="mt-1.5 grid grid-cols-4 gap-1.5">
                    {metrics.map(([k, v]) => (
                      <div key={k}>
                        <div className="text-[11px] leading-tight text-n7">{k}</div>
                        <div className="text-[14px] font-medium">{v}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}

// ---------------------------------------------------------------- narxlar

function Prices() {
  const { t } = useI18n()
  const { z, f } = useZk()
  const { data, isPending } = useQuery(pricesQuery)
  const [open, setOpen] = useState<string | null>(null)
  if (isPending) return <Loading />
  if (!data?.items.length) return <Empty title={t.analytics.empty} hint={z.period30} />
  const overpay = data.items.reduce((sum, p) => sum + Number(p.overpay), 0)
  return (
    <>
      <div className="mt-3 border border-line p-3">
        <div className="text-[13px] text-n7">{z.overpay_best}</div>
        <div className="font-head text-[26px]" style={{ fontWeight: 600, color: DANGER }}>
          {f.money(overpay)}
        </div>
      </div>
      {data.items.map((p) => (
        <PriceRow
          key={p.product_id}
          p={p}
          open={open === p.product_id}
          onToggle={() => setOpen(open === p.product_id ? null : p.product_id)}
        />
      ))}
    </>
  )
}

function PriceRow({ p, open, onToggle }: { p: ProductPrice; open: boolean; onToggle: () => void }) {
  const { z, f, locale } = useZk()
  const change = p.change_pct === null ? null : Number(p.change_pct)
  const chgColor = change === null ? MUTED : change > 3 ? DANGER : change > 0 ? WARN : OK
  const overpay = Number(p.overpay)
  return (
    <div className="border-b border-line">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="zk-hover grid w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 py-3 text-left text-ink"
      >
        <div className="text-[16px] font-medium">{p.product_name}</div>
        <div className="whitespace-nowrap text-[15px] font-medium" style={{ color: chgColor }}>
          {change === null ? '—' : f.pct(change)}
        </div>
        <div className="text-[13px] text-n7">{`${f.money(p.avg_price)} / ${f.unit(p.base_unit)} · ${f.qty(p.qty, p.base_unit)}`}</div>
        <div className="text-n7">{open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</div>
        {p.best_price !== null && (
          <div className="col-span-full text-[13px] text-a7">
            {`${z.best}: ${f.money(p.best_price)} · ${p.best_supplier ?? '—'}`}
            {overpay > 0 && <span style={{ color: WARN }}>{` · ${L[locale].overpay} ${f.money(overpay)}`}</span>}
          </div>
        )}
      </button>
      {open && <PriceHistory productId={p.product_id} />}
    </div>
  )
}

function PriceHistory({ productId }: { productId: string }) {
  const { t } = useI18n()
  const { f } = useZk()
  const { data = [], isPending } = useQuery(priceHistoryQuery(productId))
  if (isPending) return <Skeleton className="mb-3 h-24" />
  const receipts = data.filter((point) => point.source === 'receipt')
  const series = (receipts.length >= 2 ? receipts : data).map((point) => Number(point.price))
  const last = data.slice(-6)
  return (
    <div className="pb-3">
      <Sparkline values={series} />
      {last.length > 0 && (
        <div className="mt-2 grid grid-cols-3 gap-px border border-line bg-line">
          {last.map((point, i) => (
            <div key={`${point.day}-${i}`} className="min-w-0 bg-ground px-2 py-1.5">
              <div className="truncate text-[12px] text-n7">{`${f.dt(point.day)} · ${point.supplier_name}`}</div>
              <div className="text-[14px]">
                {f.n(Number(point.price))}
                {point.source === 'receipt' && <span className="text-[12px] text-n7">{` · ${t.analytics.fact}`}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------- ombor

function Stock() {
  const { t } = useI18n()
  const { z, f } = useZk()
  const { data, isPending } = useQuery(stockQuery)
  if (isPending) return <Loading />
  if (!data?.items.length) return <Empty title={t.analytics.noStock} hint={t.analytics.noStockHint} />
  return (
    <>
      <Cells
        className="mt-3"
        cols={2}
        size={22}
        items={[
          { label: z.money_stock, value: f.money(data.total_value) },
          { label: z.illiquid, value: f.money(data.dead_value), color: WARN },
        ]}
      />
      {data.items.map((s) => {
        const days = s.days_cover === null ? null : Number(s.days_cover)
        const color = days !== null && days < 1 ? DANGER : s.dead ? WARN : MUTED
        const daysText = days === null ? t.analytics.noConsumption : `${z.enough_for} ${f.n(days, 1)} ${z.days_s}`
        return (
          <div
            key={`${s.store_id}-${s.product_id}`}
            className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-0.5 border-b border-line py-3"
          >
            <div className="text-[16px] font-medium">{s.product_name}</div>
            <div className="whitespace-nowrap text-[15px] font-medium">{f.money(s.value)}</div>
            <div className="text-[13px] text-n7">{`${s.store_name} · ${f.qty(s.qty, s.base_unit)}`}</div>
            <div className="whitespace-nowrap text-[13px]" style={{ color }}>
              {s.dead ? `${t.analytics.dead} · ${daysText}` : daysText}
            </div>
          </div>
        )
      })}
    </>
  )
}

// ---------------------------------------------------------------- nazorat

const CONTROL_KEY: Record<ControlItem['kind'], ZkKey> = {
  price_change: 'ctl_price',
  discrepancy: 'ctl_mismatch',
  role_conflict: 'ctl_combo',
  manual_increase: 'ctl_autoinc',
  payment_without_proof: 'ctl_nopay',
}

function Control() {
  const { t } = useI18n()
  const { z, f } = useZk()
  const navigate = useNavigate()
  const { data, isPending } = useQuery(controlQuery)
  if (isPending) return <Loading />
  if (!data?.items.length) return <Empty title={t.analytics.controlClean} hint={z.period30} />
  const open = (item: ControlItem) => {
    if (item.kind === 'price_change') void navigate({ to: '/orders/$orderId', params: { orderId: item.entity_id } })
    else if (item.kind === 'discrepancy') void navigate({ to: '/receiving/receipts/$receiptId', params: { receiptId: item.entity_id } })
    else if (item.kind === 'payment_without_proof') void navigate({ to: '/finance/payments/$paymentId', params: { paymentId: item.entity_id } })
    else void navigate({ to: '/requests/$requestId', params: { requestId: item.entity_id } })
  }
  return (
    <div className="mt-1">
      {data.items.map((item) => {
        const detail = item.detail ? controlDetail(item, t) : ''
        const who = [f.dtTime(item.at), item.amount !== null ? f.money(item.amount) : null].filter(Boolean).join(' · ')
        return (
          <button
            key={`${item.kind}-${item.entity_id}`}
            type="button"
            onClick={() => open(item)}
            className="zk-hover grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 border-b border-line py-3 text-left text-ink"
          >
            <div className="flex min-w-0 flex-col items-start gap-1">
              <Tag tone="warn">{z[CONTROL_KEY[item.kind]]}</Tag>
              <div className="text-[15px]">
                <span className="font-medium">{item.number}</span>
                {` · ${item.title}`}
                {detail && <span className="text-n7">{` · ${detail}`}</span>}
              </div>
              <div className="text-[13px] text-n7">{who}</div>
            </div>
            <ChevronRight size={20} />
          </button>
        )
      })}
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
