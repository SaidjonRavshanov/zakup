/** "Nega shu ball": 100 dan har bir ko'rsatkich qancha ayirgani (backend `penalties` — formula bitta joyda). */
import { pct, type SupplierRating } from '@/entities/analytics'
import { useZk } from '@/shared/i18n/use-zk'
import { Sheet } from '@/shared/kit'
import { fill, L } from './i18n'

const WEIGHTS = { short: 40, defect: 30, price: 20, late: 10 } as const
type Key = keyof typeof WEIGHTS

export function ScoreSheet({ supplier, onClose }: { supplier: SupplierRating | null; onClose: () => void }) {
  const { z, f, locale } = useZk()
  const l = L[locale]
  if (!supplier) return null

  const share = (v: string) => `${f.n(pct(v), 1)}%`
  const rows: Array<{ key: Key; title: string; text: string }> = [
    { key: 'short', title: z.m_short, text: fill(l.whyShort, { v: share(supplier.short_rate) }) },
    { key: 'defect', title: z.m_defect, text: fill(l.whyDefect, { v: share(supplier.defect_rate) }) },
    { key: 'price', title: z.m_price, text: fill(l.whyPrice, { v: share(supplier.price_rate) }) },
    { key: 'late', title: l.whyLateTitle, text: fill(l.whyLate, { v: `${f.n(100 - pct(supplier.on_time_rate), 1)}%` }) },
  ]
  const minus = (key: Key) => Number(supplier.penalties?.[key] ?? 0)

  return (
    <Sheet open title={`${supplier.supplier_name} · ${l.whyTitle}`} onClose={onClose}>
      {supplier.score === null || !supplier.penalties ? (
        <p className="m-0 text-[15px] text-n7">{l.whyNone}</p>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="m-0 text-[14px] text-n7">{l.whyStart}</p>
          {rows.map((row) => (
            <div key={row.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 border-b border-line pb-2.5">
              <div className="min-w-0">
                <div className="text-[15px] font-medium">{row.title}</div>
                <div className="text-[13px] text-n7">{`${row.text} · ${fill(l.whyMax, { n: String(WEIGHTS[row.key]) })}`}</div>
              </div>
              <div className={minus(row.key) > 0 ? 'whitespace-nowrap text-[16px] font-semibold text-danger' : 'whitespace-nowrap text-[16px] text-n7'}>
                {minus(row.key) > 0 ? `−${f.n(minus(row.key), 1)}` : '0'}
              </div>
            </div>
          ))}
          <div className="flex items-baseline justify-between gap-3 pt-1">
            <span className="text-[15px]">{`${l.whyTotal}: 100 − ${f.n(rows.reduce((s, r) => s + minus(r.key), 0), 1)}`}</span>
            <span className="font-head text-[28px]" style={{ fontWeight: 600 }}>
              {Math.round(Number(supplier.score))}
            </span>
          </div>
          <p className="m-0 text-[13px] text-n7">
            {fill(l.whyBasis, { receipts: f.cnt(supplier.receipts, 'receipts_n'), orders: f.cnt(supplier.orders, 'orders_n') })}
          </p>
          <p className="m-0 text-[13px] text-n7">{l.whyScale}</p>
        </div>
      )}
    </Sheet>
  )
}
