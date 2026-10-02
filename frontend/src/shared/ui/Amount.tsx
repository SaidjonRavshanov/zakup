import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'

export function MoneyText({ value, className }: { value: number; className?: string }) {
  const { t, fmt } = useI18n()
  return (
    <span className={cn('tnum whitespace-nowrap font-semibold', className)}>
      {fmt.money(value)}
      <span className="ml-1 font-mono text-[9px] font-medium uppercase tracking-[0.2em] text-text-3">{t.common.currency}</span>
    </span>
  )
}

export function QtyText({ value, unit, className }: { value: number; unit: string; className?: string }) {
  const { fmt } = useI18n()
  return (
    <span className={cn('tnum whitespace-nowrap', className)}>
      {fmt.qty(value)}
      <span className="ml-1 font-mono text-[9px] uppercase tracking-[0.2em] text-text-3">{unit}</span>
    </span>
  )
}
