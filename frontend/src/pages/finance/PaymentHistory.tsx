/** To'lovlar tarixi: faqat to'langanlar, kunlar bo'yicha (kun jami), 7 / 30 kunlik jami. */
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { paidPaymentsQuery, ON_DELIVERY_COMMENT, type PaymentListItem } from '@/entities/payment'
import { useZk } from '@/shared/i18n/use-zk'
import { Cells, Empty, Row, RowsSkeleton, Section, Tag } from '@/shared/kit'

const DAY = 86_400_000
/** Qurilma vaqti bo'yicha kun (YYYY-MM-DD) — guruhlash uchun. */
const localDay = (iso: string) => new Date(iso).toLocaleDateString('en-CA')

export function PaymentHistory() {
  const navigate = useNavigate()
  const { z, f } = useZk()
  const { data: paid = [], isPending } = useQuery(paidPaymentsQuery)
  const [now] = useState(() => Date.now()) // 7 / 30 kun hisobi uchun — sahifa ochilgan payt
  if (isPending) return <RowsSkeleton n={5} />
  if (paid.length === 0) return <Empty title={z.no_paid} />

  const since = (days: number) =>
    paid.filter((p) => p.paid_at && now - Date.parse(p.paid_at) <= days * DAY).reduce((s, p) => s + Number(p.total), 0)
  const days = new Map<string, PaymentListItem[]>()
  for (const p of paid) {
    const key = localDay(p.paid_at ?? p.requested_at)
    days.set(key, [...(days.get(key) ?? []), p])
  }
  const method = (p: PaymentListItem) => (p.method === 'cash' ? z.pm_cash : z.pm_bank)

  return (
    <>
      <Cells
        className="mt-3"
        cols={2}
        items={[
          { label: z.paid_7d, value: f.money(since(7)) },
          { label: z.paid_30d, value: f.money(since(30)) },
        ]}
      />
      {[...days.entries()].map(([day, items]) => (
        <div key={day}>
          <Section aside={f.money(items.reduce((s, p) => s + Number(p.total), 0))}>{f.dt(day)}</Section>
          {items.map((p) => (
            <Row
              key={p.id}
              meta={`${p.number} · ${p.paid_at ? f.time(p.paid_at) : '—'} · ${method(p)}`}
              title={p.supplier_name ?? '—'}
              amount={f.money(p.total)}
              badge={p.comment === ON_DELIVERY_COMMENT ? <Tag tone="neutral">{z.on_delivery}</Tag> : undefined}
              onClick={() => navigate({ to: '/finance/payments/$paymentId', params: { paymentId: p.id } })}
            />
          ))}
        </div>
      ))}
    </>
  )
}
