import { Minus, Plus } from 'lucide-react'
import { useState } from 'react'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { parseDecimal } from '@/shared/lib/format'
import { telegram } from '@/shared/lib/telegram'

interface QtyStepperProps {
  value: number
  onChange: (value: number) => void
  step?: number
  min?: number
  unit?: string
  label?: string
  className?: string
}

/** Qabulda miqdor kiritish: katta tugmalar (qo'lqopda ham), vergul/nuqta ikkalasi ham. */
export function QtyStepper({ value, onChange, step = 1, min = 0, unit, label, className }: QtyStepperProps) {
  const { t, fmt } = useI18n()
  const [draft, setDraft] = useState(() => fmt.qty(value))
  const [synced, setSynced] = useState({ value, fmt })
  // Qiymat yoki til (o'nlik ajratgich) o'zgarsa — render paytida moslash (effect'siz)
  if (synced.value !== value || synced.fmt !== fmt) {
    setSynced({ value, fmt })
    setDraft(fmt.qty(value))
  }

  const commit = (next: number) => {
    const clamped = Math.max(min, Math.round(next * 10_000) / 10_000)
    onChange(clamped)
    setDraft(fmt.qty(clamped))
  }

  const stepBy = (delta: number) => {
    telegram.haptic.select()
    commit(value + delta)
  }

  const buttonClass =
    'grid size-12 shrink-0 place-items-center rounded-full border border-border text-text transition-transform duration-150 active:scale-90 disabled:opacity-30'

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <button type="button" aria-label={t.common.decrease} className={buttonClass} disabled={value <= min} onClick={() => stepBy(-step)}>
        <Minus size={18} />
      </button>
      <label className="flex h-12 min-w-0 flex-1 items-center justify-center gap-1.5 rounded-full bg-surface-2 px-3">
        <input
          inputMode="decimal"
          aria-label={label}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={() => {
            const parsed = parseDecimal(draft)
            if (parsed === null) setDraft(fmt.qty(value))
            else commit(parsed)
          }}
          onFocus={(event) => event.target.select()}
          className="tnum w-full min-w-0 bg-transparent text-center font-display text-xl font-extrabold tracking-[-0.03em] outline-none"
        />
        {unit && <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-3">{unit}</span>}
      </label>
      <button type="button" aria-label={t.common.increase} className={buttonClass} onClick={() => stepBy(step)}>
        <Plus size={18} />
      </button>
    </div>
  )
}
