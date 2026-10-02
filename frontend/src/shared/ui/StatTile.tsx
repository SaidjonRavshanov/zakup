import type { ReactNode } from 'react'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { MonoLabel } from './MonoLabel'

interface StatTileProps {
  label: string
  value: ReactNode
  unit?: string
  /** O'tgan davrga nisbatan o'zgarish, %. */
  delta?: number
  /** delta oshishi yaxshimi (tejash) yoki yomonmi (xarajat). */
  deltaGoodWhen?: 'up' | 'down'
  className?: string
}

export function StatTile({ label, value, unit, delta, deltaGoodWhen = 'down', className }: StatTileProps) {
  const { fmt } = useI18n()
  const good = delta === undefined || delta === 0 ? null : (delta > 0) === (deltaGoodWhen === 'up')
  return (
    <div
      className={cn(
        'flex min-h-32 flex-col justify-between rounded-card border border-border-soft bg-surface p-4 shadow-[var(--shadow-card)]',
        className,
      )}
    >
      <MonoLabel>{label}</MonoLabel>
      <div className="mt-4">
        <div className="tnum flex items-baseline gap-1.5 font-display text-[28px] font-extrabold leading-none tracking-[-0.05em]">
          {value}
          {unit && <span className="font-mono text-[10px] font-medium tracking-[0.2em] text-text-3">{unit}</span>}
        </div>
        {delta !== undefined && (
          <div
            className={cn(
              'tnum mt-2 font-mono text-[10px] tracking-[0.12em]',
              good === null ? 'text-text-3' : good ? 'text-accent-text' : 'text-danger',
            )}
          >
            {delta > 0 ? '▲' : delta < 0 ? '▼' : '•'} {fmt.percent(delta)}
          </div>
        )}
      </div>
    </div>
  )
}
