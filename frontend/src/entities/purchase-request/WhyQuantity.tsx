import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import { useZk } from '@/shared/i18n/use-zk'
import type { AutoCalc } from './index'

/** Avto-zayavka: "nega shuncha" — sarf, qoldiq, yo'lda, formula va qadoqqa yaxlitlash (WORKFLOW B3). */
export function WhyQuantity({ calc, unit, qty }: { calc: AutoCalc; unit: UnitCode; qty: number }) {
  const { z, f } = useZk()
  const { t } = useI18n()
  const n = (value: string | number | null | undefined) => f.n(Number(value ?? 0))
  const q = (value: string | number | null | undefined) => f.qty(Number(value ?? 0), unit)
  const packUnit = calc.pack_unit ? f.pack(calc.pack_unit) : f.unit(unit)
  const stock = Math.max(Number(calc.stock ?? 0), 0)
  const rows: Array<[string, string]> = [
    [z.c_avg, `${q(calc.avg_daily)} / ${z.day_s} · ${calc.days_observed} ${z.days_s}`],
    [
      z.c_stock,
      calc.stock === null ? t.requests.why.noStock : `${q(calc.stock)}${calc.stock_at ? ` · ${f.dtTime(calc.stock_at)}` : ''}`,
    ],
    [z.c_transit, q(calc.in_transit)],
    [z.c_period, `${calc.lead_days} + ${calc.coverage_days} ${z.days_s}`],
    [z.c_safety, q(calc.safety_stock)],
    [
      z.c_formula,
      `${n(calc.avg_daily)} × (${calc.lead_days} + ${calc.coverage_days}) + ${n(calc.safety_stock)} − ${n(stock)} − ${n(
        calc.in_transit,
      )} = ${n(calc.need)}`,
    ],
    [
      z.c_round,
      Number(calc.pack_factor) === 1
        ? `${q(calc.need)} → ${q(qty)}`
        : `${q(calc.need)} → ${n(calc.packs)} ${packUnit} (${q(qty)})`,
    ],
  ]
  if (calc.trigger) rows.push([z.c_reason, calc.trigger === 'reorder_point' ? z.why_below : z.why_day])
  return (
    <div className="border border-line px-3 py-0.5">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-dashed border-line py-[7px] text-[13px] last:border-b-0">
          <span className="text-n7">{k}</span>
          <span className="text-right">{v}</span>
        </div>
      ))}
    </div>
  )
}
