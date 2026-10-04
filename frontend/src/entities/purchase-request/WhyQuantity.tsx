import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import type { AutoCalc } from './index'

/** Avto-zayavka: "nega shuncha" — sarf, qoldiq, yo'lda, formula va qadoqqa yaxlitlash (WORKFLOW B3). */
export function WhyQuantity({ calc, unit, qty }: { calc: AutoCalc; unit: UnitCode; qty: number }) {
  const { t, fmt } = useI18n()
  const u = t.units[unit]
  const n = (value: string | null | undefined) => fmt.qty(Number(value ?? 0))
  const packUnit = calc.pack_unit ? (t.units[calc.pack_unit as UnitCode] ?? calc.pack_unit) : u
  const w = t.requests.why
  const rows: Array<[string, string]> = [
    [w.avgDaily, `${n(calc.avg_daily)} ${u} / ${w.day} · ${w.observed(Number(calc.days_observed))}`],
    [
      w.stock,
      calc.stock === null
        ? w.noStock
        : `${n(calc.stock)} ${u}${calc.stock_at ? ` · ${fmt.date(calc.stock_at)} ${fmt.time(calc.stock_at)}` : ''}`,
    ],
    [w.inTransit, `${n(calc.in_transit)} ${u}`],
    [w.period, w.periodValue(Number(calc.lead_days), Number(calc.coverage_days))],
    [w.safety, `${n(calc.safety_stock)} ${u}`],
  ]
  return (
    <div className="mt-2 rounded-md bg-surface-2 px-3 py-2 text-[12px] leading-relaxed text-text-2">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-text-3">{label}</dt>
            <dd className="tnum">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="tnum mt-2 font-mono text-[11px] text-text">
        {`${n(calc.avg_daily)} × (${calc.lead_days} + ${calc.coverage_days}) + ${n(calc.safety_stock)} − ${n(
          Math.max(Number(calc.stock ?? 0), 0).toString(),
        )} − ${n(calc.in_transit)} = ${n(calc.need)} ${u}`}
      </p>
      <p className="tnum mt-1 font-mono text-[11px] text-text">
        {Number(calc.pack_factor) === 1
          ? `${w.rounded}: ${n(calc.need)} → ${fmt.qty(qty)} ${u}`
          : `${w.rounded}: ${n(calc.packs)} × ${packUnit} (${n(calc.pack_factor)} ${u}) = ${fmt.qty(qty)} ${u}`}
      </p>
      {calc.trigger && (
        <p className="mt-1 text-text-3">
          {calc.trigger === 'reorder_point' ? w.triggerReorder(`${n(calc.reorder_point)} ${u}`) : w.triggerOrderDay}
        </p>
      )}
    </div>
  )
}
