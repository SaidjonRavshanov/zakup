import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'

interface DiffIndicatorProps {
  expected: number
  actual: number
  unit?: string
  /** Ruxsat etilgan og'ish, % (WORKFLOW B9). */
  tolerancePct: number
  className?: string
}

/** "Buyurtma → keldi": 10 → 10.5 kg ▲5% — dopusk ichida neytral, tashqarida ogohlantirish. */
export function DiffIndicator({ expected, actual, unit, tolerancePct, className }: DiffIndicatorProps) {
  const { fmt } = useI18n()
  const diffPct = expected === 0 ? 0 : ((actual - expected) / expected) * 100
  const withinTolerance = Math.abs(diffPct) <= tolerancePct
  const tone = diffPct === 0 ? 'text-text-3' : withinTolerance ? 'text-text-2' : 'text-warning'

  return (
    <span className={cn('tnum inline-flex items-center gap-1.5 font-mono text-[11px] tracking-[0.06em]', className)}>
      <span className="text-text-3">{fmt.qty(expected)}</span>
      <span className="text-text-3">→</span>
      <span className="text-text">
        {fmt.qty(actual)}
        {unit && <span className="ml-0.5 text-text-3">{unit}</span>}
      </span>
      {diffPct !== 0 && (
        <span className={tone}>
          {diffPct > 0 ? '▲' : '▼'}
          {fmt.percent(diffPct)}
        </span>
      )}
    </span>
  )
}
