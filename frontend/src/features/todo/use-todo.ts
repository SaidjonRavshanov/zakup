/**
 * "Ждёт вас": faol rol uchun bajariladigan ishlar (prototip todo()). Har bir ish — hujjatga havola.
 * Ma'lumot — mavjud ro'yxat so'rovlaridan (backend allaqachon ombor/rol bo'yicha cheklaydi).
 */
import { useQuery } from '@tanstack/react-query'
import { controlQuery, type ControlKind } from '@/entities/analytics'
import { iikoSyncQuery, type SyncRun } from '@/entities/iiko'
import { balancesQuery, paymentsQuery } from '@/entities/payment'
import { OPEN_STATUSES, purchaseOrdersQuery } from '@/entities/purchase-order'
import { OPEN_REQUEST_STATUSES, requestsByStatusQuery } from '@/entities/purchase-request'
import { receiptsQuery } from '@/entities/receipt'
import { meQuery, useActiveRole, usersQuery, type Role } from '@/entities/user'
import { todayIso, useZk, type ZkKey } from '@/shared/i18n/use-zk'
import type { Tone } from '@/shared/kit'
import { usePendingReceipts } from '@/shared/offline/outbox'

export interface TodoItem {
  key: string
  group: 'now' | 'today'
  label: string
  tone: Tone
  title: string
  meta: string
  amount: string
  href: string
}

const CONTROL: Record<ControlKind, { label: ZkKey; href: (id: string) => string }> = {
  price_change: { label: 'ctl_price', href: (id) => `/orders/${id}` },
  discrepancy: { label: 'ctl_mismatch', href: (id) => `/receiving/receipts/${id}` },
  role_conflict: { label: 'ctl_combo', href: (id) => `/requests/${id}` },
  manual_increase: { label: 'ctl_autoinc', href: (id) => `/requests/${id}` },
  payment_without_proof: { label: 'ctl_nopay', href: (id) => `/finance/payments/${id}` },
}

const SYNC_KIND: Record<SyncRun['kind'], ZkKey> = {
  references: 'ik_ref',
  purchase_prices: 'ik_prices',
  stock: 'ik_stock',
  consumption: 'ik_usage',
}

export function useTodo(): { items: TodoItem[]; role: Role | null; loading: boolean } {
  const { z, f } = useZk()
  const { data: me } = useQuery(meQuery)
  const role = useActiveRole(me)
  const has = (...roles: Role[]) => role !== null && roles.includes(role)

  const users = useQuery({ ...usersQuery, enabled: has('admin') })
  const iiko = useQuery({ ...iikoSyncQuery, enabled: has('admin') })
  const orders = useQuery({ ...purchaseOrdersQuery(OPEN_STATUSES), enabled: has('storekeeper', 'buyer', 'approver', 'admin') })
  const requests = useQuery({ ...requestsByStatusQuery(OPEN_REQUEST_STATUSES), enabled: has('approver', 'admin', 'buyer', 'initiator') })
  const payments = useQuery({ ...paymentsQuery(), enabled: has('approver', 'admin', 'accountant') })
  const receipts = useQuery({ ...receiptsQuery, enabled: has('buyer', 'approver', 'admin') })
  const balances = useQuery({ ...balancesQuery, enabled: has('accountant') })
  const control = useQuery({ ...controlQuery, enabled: has('auditor') })
  const queue = usePendingReceipts()

  const items: TodoItem[] = []
  const add = (item: Omit<TodoItem, 'key'>) => items.push({ ...item, key: `${items.length}:${item.href}` })
  const pos = (n: number) => `${n} ${z.pos_short}`

  if (has('admin')) {
    for (const u of users.data?.filter((x) => !x.is_active) ?? []) {
      add({ group: 'now', label: z.k_user, tone: 'warn', title: u.full_name, meta: `ID ${u.telegram_id}`, amount: '', href: `/admin/users/${u.id}` })
    }
    // Har server+tur bo'yicha oxirgi ishga tushirish xato bo'lsa
    const latest = new Map<string, SyncRun>()
    for (const run of iiko.data?.runs ?? []) {
      const k = `${run.server_code}:${run.kind}`
      if (!latest.has(k)) latest.set(k, run)
    }
    for (const run of latest.values()) {
      if (run.status !== 'failed') continue
      add({
        group: 'now',
        label: z.k_iiko,
        tone: 'danger',
        title: `iiko · ${run.server_code}`,
        meta: `${z[SYNC_KIND[run.kind]]} · ${f.dtTime(run.finished_at ?? run.created_at)}`,
        amount: '',
        href: '/admin/iiko',
      })
    }
  }

  if (has('storekeeper')) {
    for (const q of queue.filter((x) => x.error)) {
      add({ group: 'now', label: z.k_queue_err, tone: 'danger', title: q.orderNumber, meta: q.error ?? '', amount: '', href: '/receiving' })
    }
  }

  const po = orders.data ?? []
  const rq = requests.data ?? []
  const today = todayIso()

  if (has('storekeeper', 'buyer')) {
    const queued = new Set(queue.map((q) => q.orderId))
    for (const o of po.filter(
      (x) => x.deliveryDate === today && ['SENT', 'CONFIRMED', 'PARTIALLY_CONFIRMED'].includes(x.status) && !queued.has(x.id),
    )) {
      add({ group: 'today', label: z.k_delivery, tone: 'accent', title: o.supplierName, meta: `${o.number} · ${o.storeName}`, amount: f.money(o.totalAmount), href: `/receiving/${o.id}` })
    }
  }

  const reqMeta = (r: (typeof rq)[number], withType: boolean) =>
    `${withType ? `${z[`rt_${r.type === 'manual' ? 'regular' : r.type === 'event' ? 'banquet' : 'auto'}`]} · ` : ''}${pos(r.lines_count)} · ${z.need_to} ${f.dt(r.needed_by)}`
  const reqTitle = (r: (typeof rq)[number]) => `${r.number} · ${r.store_name ?? ''}`

  if (has('approver', 'admin', 'buyer')) {
    for (const r of rq.filter((x) => x.status === 'PENDING_APPROVAL')) {
      add({ group: 'now', label: z.k_approve, tone: 'accent', title: reqTitle(r), meta: reqMeta(r, true), amount: f.money(r.total), href: `/requests/${r.id}` })
    }
  }
  if (has('buyer', 'admin')) {
    for (const r of rq.filter((x) => x.status === 'DRAFT' && x.type === 'auto')) {
      add({ group: 'now', label: z.k_autocheck, tone: 'warn', title: reqTitle(r), meta: reqMeta(r, false), amount: f.money(r.total), href: `/requests/${r.id}` })
    }
    for (const o of po.filter((x) => x.status === 'CREATED')) {
      add({ group: 'now', label: z.k_send, tone: 'neutral', title: o.supplierName, meta: `${o.number} · ${o.storeName}`, amount: f.money(o.totalAmount), href: `/orders/${o.id}` })
    }
  }
  if (has('buyer')) {
    for (const o of po.filter((x) => x.status === 'SENT' && x.responseDeadline)) {
      add({
        group: 'today',
        label: z.k_waitresp,
        tone: 'accent',
        title: o.supplierName,
        meta: `${o.number} · ${z.resp_until} ${f.time(o.responseDeadline as string)}`,
        amount: f.money(o.totalAmount),
        href: `/orders/${o.id}`,
      })
    }
  }
  if (has('approver', 'admin')) {
    for (const o of po.filter((x) => x.status === 'REAPPROVAL')) {
      add({ group: 'now', label: z.k_price, tone: 'warn', title: o.supplierName, meta: `${o.number} · ${o.storeName}`, amount: f.money(o.confirmedTotal || o.totalAmount), href: `/orders/${o.id}` })
    }
    for (const p of payments.data?.filter((x) => x.status === 'SUBMITTED') ?? []) {
      add({ group: 'now', label: z.k_payapprove, tone: 'accent', title: p.supplier_name ?? '', meta: `${p.number} · ${p.method === 'cash' ? z.pm_cash : z.pm_bank}`, amount: f.money(p.total), href: `/finance/payments/${p.id}` })
    }
  }
  if (has('buyer', 'approver', 'admin')) {
    for (const r of receipts.data?.filter((x) => x.dispute_open) ?? []) {
      add({ group: 'now', label: z.k_dispute, tone: 'warn', title: r.supplier_name ?? r.number, meta: `${r.number} · ${r.store_name ?? ''}`, amount: '', href: `/receiving/receipts/${r.id}` })
    }
  }
  if (has('accountant', 'admin')) {
    for (const p of payments.data?.filter((x) => x.status === 'APPROVED') ?? []) {
      add({ group: 'now', label: z.k_topay, tone: 'solid', title: p.supplier_name ?? '', meta: `${p.number} · ${p.method === 'cash' ? z.pm_cash : z.pm_bank}`, amount: f.money(p.total), href: `/finance/payments/${p.id}` })
    }
  }
  if (has('accountant')) {
    for (const b of balances.data?.filter((x) => Number(x.overdue) > 0) ?? []) {
      add({ group: 'today', label: z.k_overdue, tone: 'danger', title: b.supplier_name ?? '', meta: z.overdue, amount: f.money(b.overdue), href: `/finance/suppliers/${b.supplier_id}` })
    }
  }
  if (has('initiator') && me) {
    const mine = rq.filter((x) => x.initiator_id === me.id)
    for (const r of mine.filter((x) => x.status === 'DRAFT')) {
      add({ group: 'now', label: z.k_draft, tone: 'neutral', title: reqTitle(r), meta: reqMeta(r, false), amount: f.money(r.total), href: `/requests/${r.id}` })
    }
    for (const r of mine.filter((x) => x.status === 'REJECTED')) {
      add({ group: 'today', label: z.k_rejected, tone: 'danger', title: reqTitle(r), meta: f.dt(r.needed_by), amount: '', href: `/requests/${r.id}` })
    }
  }
  if (has('auditor')) {
    for (const c of control.data?.items ?? []) {
      const k = CONTROL[c.kind]
      add({ group: 'now', label: z[k.label], tone: 'warn', title: c.number, meta: c.detail || c.title, amount: c.amount ? f.money(c.amount) : '', href: k.href(c.entity_id) })
    }
  }

  const loading = [users, iiko, orders, requests, payments, receipts, balances, control].some((q) => q.isLoading)
  return { items, role, loading }
}
