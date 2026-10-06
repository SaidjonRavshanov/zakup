/** Bosh sahifa (prototip "home", vmHome): bugun, asosiy son, "Ждёт вас" (3 ta), oy ko'rsatkichlari, bugungi yetkazmalar. */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { ChartLine, ChevronRight, Plus } from 'lucide-react'
import { summaryQuery } from '@/entities/analytics'
import { purchaseOrdersQuery } from '@/entities/purchase-order'
import { requestsQuery } from '@/entities/purchase-request'
import { meQuery, useActiveRole, useHasRole } from '@/entities/user'
import { TodoList, useTodo } from '@/features/todo'
import { healthQuery } from '@/shared/api/health'
import { todayIso, useZk } from '@/shared/i18n/use-zk'
import { Banner, Blueprint, Btn, Cells, Corners, Empty, Row, RowsSkeleton, Section, Tag, status } from '@/shared/kit'
import { usePendingReceipts } from '@/shared/offline/outbox'

const FULL = ['buyer', 'approver', 'accountant', 'auditor', 'admin']

function longDate(locale: 'ru' | 'uz'): string {
  const s = new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'uz-Latn-UZ', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    timeZone: 'Asia/Tashkent',
  }).format(new Date())
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { z, f, locale } = useZk()
  const { data: me } = useQuery(meQuery)
  const role = useActiveRole(me)
  const full = role !== null && FULL.includes(role)
  const canCreate = useHasRole('initiator', 'buyer', 'admin')
  const canReceive = useHasRole('storekeeper', 'buyer', 'admin')

  const health = useQuery(healthQuery)
  const { data: summary } = useQuery({ ...summaryQuery, enabled: full })
  const { data: orders, isPending } = useQuery({ ...purchaseOrdersQuery(), enabled: role !== 'initiator' })
  const { data: requests } = useQuery({ ...requestsQuery, enabled: role === 'initiator' })
  const { items: todo } = useTodo()
  const queue = usePendingReceipts()

  const today = (orders ?? []).filter(
    (o) => o.deliveryDate === todayIso() && ['CREATED', 'SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED'].includes(o.status),
  )
  const top = role === 'storekeeper' ? todo.filter((x) => x.group === 'now') : todo
  const mine = (requests ?? []).filter((r) => r.initiator_id === me?.id)
  const online = health.data?.database === 'ok'

  let hero: { label: string; value: string; sub: string; delta?: string }
  if (full) {
    const prev = Number(summary?.purchases_prev ?? 0)
    const delta = prev > 0 ? (Number(summary?.purchases) / prev - 1) * 100 : null
    hero = {
      label: z.month_buy,
      value: summary ? f.cmp(summary.purchases) : '—',
      sub: summary ? `${summary.receipts} ${z.receipts_n}` : '',
      delta: delta === null ? '' : `${f.pct(delta)} ${z.vs_prev}`,
    }
  } else if (role === 'initiator') {
    const drafts = mine.filter((r) => r.status === 'DRAFT').length
    const pending = mine.filter((r) => r.status === 'PENDING_APPROVAL').length
    hero = { label: z.my_reqs, value: String(drafts + pending), sub: `${drafts} ${z.drafts_n} · ${pending} ${z.pending_n}` }
  } else {
    hero = {
      label: z.deliveries_today,
      value: String(today.length),
      sub: `${f.cmp(today.reduce((a, o) => a + o.totalAmount, 0))} ${z.sum}`,
    }
  }

  const bad = (v: string | number) => (Number(v) > 0 ? 'var(--zk-danger)' : undefined)

  return (
    <div>
      <div className="flex items-start justify-between gap-3 pt-2">
        <div>
          <h1 className="m-0 text-[34px]">{z.today}</h1>
          <div className="text-[14px] text-n7">{longDate(locale)}</div>
        </div>
        <div className="flex items-center gap-1.5 pt-3 text-[13px] text-n7">
          <span className="block size-2" style={{ background: online ? 'var(--color-accent)' : 'var(--zk-danger)' }} />
          {online ? z.srv_ok : health.isPending ? '…' : z.offline}
        </div>
      </div>

      <div className="blueprint mt-4 p-4">
        <Corners />
        <div className="text-[14px] text-n7">{hero.label}</div>
        <div className="font-head text-[52px] leading-[1.05] tracking-[-0.02em]" style={{ fontWeight: 600 }}>
          {hero.value}
        </div>
        <div className="mt-1 flex flex-wrap gap-3 text-[14px] text-n7">
          <span>{hero.sub}</span>
          {hero.delta && <span className="text-a7">{hero.delta}</span>}
        </div>
        {canCreate && (
          <Btn variant="primary" size="lg" block icon={<Plus size={20} />} className="mt-4" onClick={() => navigate({ to: '/requests/new' })}>
            {z.new_req}
          </Btn>
        )}
      </div>

      {queue.some((q) => q.error) && (
        <Banner tone="danger" className="mt-4" onClick={() => navigate({ to: '/receiving' })}>
          {z.queue_err_alert}
        </Banner>
      )}

      <Section
        className="min-h-9"
        aside={
          top.length > 3 && (
            <Btn variant="ghost" size="sm" onClick={() => navigate({ to: '/todo' })}>
              {z.all_tasks} · {todo.length}
            </Btn>
          )
        }
      >
        {z.waits_you}
      </Section>
      <TodoList items={top.slice(0, 3)} />
      {!top.length && <div className="border-b border-line py-4 text-[15px] text-n7">{z.no_tasks}</div>}

      {full && (
        <>
          <Section className="mb-2">{z.month_kpi}</Section>
          {summary ? (
            <Cells
              items={[
                { label: z.kp_pending, value: summary.pending_requests },
                { label: z.kp_transit, value: summary.orders_in_transit },
                { label: z.kp_price, value: summary.price_change_pct === null ? '—' : f.pct(summary.price_change_pct) },
                { label: z.kp_save, value: f.cmp(summary.savings) },
                { label: z.kp_over, value: f.cmp(summary.overpay) },
                { label: z.kp_defect, value: f.cmp(summary.defect_loss), color: bad(summary.defect_loss) },
                { label: z.kp_debt, value: f.cmp(summary.debt) },
                { label: z.kp_overdue, value: f.cmp(summary.overdue), color: bad(summary.overdue) },
              ]}
            />
          ) : (
            <RowsSkeleton n={2} />
          )}
        </>
      )}

      {role !== 'initiator' && (
        <>
          <Section>{z.deliveries_today}</Section>
          {isPending ? (
            <RowsSkeleton n={2} />
          ) : (
            today.map((o) => {
              const s = status(z, 'order', o.status)
              const recv = canReceive && o.status !== 'CREATED'
              return (
                <Row
                  key={o.id}
                  meta={`${o.number} · ${o.storeName} · ${f.dt(o.deliveryDate)}`}
                  title={o.supplierName}
                  sub={`${o.linesCount} ${z.pos_short}`}
                  amount={f.money(o.totalAmount)}
                  badge={<Tag tone={s.tone}>{s.label}</Tag>}
                  onClick={() =>
                    recv
                      ? navigate({ to: '/receiving/$orderId', params: { orderId: o.id } })
                      : navigate({ to: '/orders/$orderId', params: { orderId: o.id } })
                  }
                />
              )
            })
          )}
          {!isPending && !today.length && <Empty className="py-4 text-left" title="" hint={z.no_deliveries} />}
        </>
      )}

      {full && (
        <Blueprint className="mt-6 flex items-center gap-3 p-4" onClick={() => navigate({ to: '/analytics' })}>
          <span className="text-a7">
            <ChartLine size={24} />
          </span>
          <div className="flex-1">
            <div className="font-head text-[20px]" style={{ fontWeight: 600 }}>
              {z.analytics}
            </div>
            <div className="text-[14px] text-n7">{z.an_card}</div>
          </div>
          <ChevronRight size={20} />
        </Blueprint>
      )}
    </div>
  )
}
