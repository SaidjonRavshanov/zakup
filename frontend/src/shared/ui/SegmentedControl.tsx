import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'

export interface Segment<T extends string> {
  value: T
  label: string
  count?: number
}

interface SegmentedControlProps<T extends string> {
  segments: ReadonlyArray<Segment<T>>
  value: T
  onChange: (value: T) => void
  className?: string
}

export function SegmentedControl<T extends string>({ segments, value, onChange, className }: SegmentedControlProps<T>) {
  return (
    <div role="tablist" className={cn('flex gap-1.5 overflow-x-auto [scrollbar-width:none]', className)}>
      {segments.map((segment) => {
        const active = segment.value === value
        return (
          <button
            key={segment.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => {
              if (active) return
              telegram.haptic.select()
              onChange(segment.value)
            }}
            className={cn(
              'flex h-9 shrink-0 items-center gap-2 rounded-full border px-4 font-mono text-[10px] font-medium uppercase tracking-[0.2em]',
              'transition-colors duration-200',
              active ? 'border-text bg-text text-bg' : 'border-border text-text-2',
            )}
          >
            {segment.label}
            {segment.count !== undefined && <span className={cn('tnum', active ? 'opacity-60' : 'text-text-3')}>{segment.count}</span>}
          </button>
        )
      })}
    </div>
  )
}
