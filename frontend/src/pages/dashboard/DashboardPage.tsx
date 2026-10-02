import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { OrderRow, purchaseOrdersQuery } from '@/entities/purchase-order'
import { useI18n } from '@/shared/i18n'
import { ActorStack, Countdown, MonoLabel, PageHeader, Skeleton, StatTile } from '@/shared/ui'
import { ApiStatus } from '@/widgets/api-status/ApiStatus'

/** Keyingi cut-off: bugun 16:00, o'tib ketgan bo'lsa — ertaga (WORKFLOW B6). */
function nextCutoff(hour = 16): string {
  const date = new Date()
  date.setHours(hour, 0, 0, 0)
  if (date.getTime() <= Date.now()) date.setDate(date.getDate() + 1)
  return date.toISOString()
}

const today = () => new Date().toISOString().slice(0, 10)

export default function DashboardPage() {
  const navigate = useNavigate()
  const { t, fmt, locale } = useI18n()
  const { data: orders, isPending } = useQuery(purchaseOrdersQuery(locale))
  const arriving = orders?.filter((po) => po.deliveryDate === today() && po.status !== 'CANCELLED') ?? []
  const todayTotal = arriving.reduce((sum, po) => sum + po.totalAmount, 0)

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${t.modules.procurement} · ${t.roles.buyer}`} title={t.dashboard.title} action={<ApiStatus />} />

      {/* Hero: 3D shisha plita ustida asosiy son */}
      <section className="relative mb-3 [perspective:1000px]">
        <div
          aria-hidden
          className="glow absolute inset-x-6 -bottom-3 top-6 -z-10 rounded-card border border-border bg-accent-wash [transform:rotateX(15deg)]"
        />
        <div className="rounded-card border-[6px] border-text bg-surface p-5 shadow-[var(--shadow-card)]">
          <div className="flex items-start justify-between">
            <MonoLabel>{`01/${t.dashboard.todayPurchase}`}</MonoLabel>
            <ActorStack
              actors={[
                { id: '1', name: 'Aziz Karimov', done: true },
                { id: '2', name: 'Dilnoza Rahimova', done: true },
                { id: '3', name: 'Bobur Aliyev', done: false },
              ]}
            />
          </div>
          <div className="tnum mt-6 font-display text-[clamp(2.6rem,14vw,4.5rem)] font-extrabold uppercase leading-[0.85] tracking-[-0.05em]">
            {fmt.moneyCompact(todayTotal)}
          </div>
          <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.3em] text-text-3">{t.common.currency} · {t.dashboard.deliveries(arriving.length)}</div>

          <div className="mt-6 flex items-end justify-between border-t border-border pt-4">
            <div>
              <MonoLabel className="mb-2">{t.dashboard.status}</MonoLabel>
              <span className="inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-accent-text">
                <span className="size-1.5 animate-pulse rounded-full bg-accent" /> {t.dashboard.receivingOpen}
              </span>
            </div>
            <div className="text-right">
              <MonoLabel className="mb-2">{t.dashboard.untilCutoff}</MonoLabel>
              <Countdown until={nextCutoff()} className="text-[28px]" />
            </div>
          </div>
        </div>
      </section>

      {/* Bento: KPI plitkalari */}
      <section className="grid grid-cols-2 gap-3">
        <StatTile label={`02/${t.dashboard.pendingApproval}`} value="3" unit={t.dashboard.pcs} />
        <StatTile label={`03/${t.dashboard.inTransit}`} value="4" unit={t.dashboard.pcs} />
        <StatTile label={`04/${t.dashboard.priceChange}`} value={`+${fmt.qty(2.4)}`} unit="%" delta={2.4} deltaGoodWhen="down" />
        <StatTile label={`05/${t.dashboard.savings}`} value={fmt.qty(1.8)} unit={t.dashboard.mln} delta={4.2} deltaGoodWhen="up" />
      </section>

      <section className="mt-8">
        <div className="mb-3 flex items-center justify-between">
          <MonoLabel>{`06/${t.dashboard.arrivingToday}`}</MonoLabel>
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
