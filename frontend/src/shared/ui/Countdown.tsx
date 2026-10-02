import { useEffect, useState } from 'react'
import { cn } from '@/shared/lib/cn'

interface CountdownProps {
  /** ISO vaqt: cut-off, javob deadline'i, to'lov muddati. */
  until: string
  className?: string
}

const pad = (n: number) => String(n).padStart(2, '0')

function useNow(intervalMs: number): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), intervalMs)
    return () => window.clearInterval(id)
  }, [intervalMs])
  return now
}

/** < 1 soat → warning, o'tib ketgan → danger (DESIGN_SYSTEM.md §5.1). */
export function Countdown({ until, className }: CountdownProps) {
  const now = useNow(1000)
  const left = new Date(until).getTime() - now
  const overdue = left <= 0
  const abs = Math.abs(left)
  const h = Math.floor(abs / 3_600_000)
  const m = Math.floor((abs % 3_600_000) / 60_000)
  const s = Math.floor((abs % 60_000) / 1000)

  return (
    <time
      dateTime={until}
      className={cn(
        'tnum font-display font-extrabold leading-none tracking-[-0.05em]',
        overdue ? 'text-danger' : left < 3_600_000 ? 'text-warning' : 'text-text',
        className,
      )}
    >
      {overdue && '−'}
      {pad(h)}:{pad(m)}
      <span className="text-text-3">:{pad(s)}</span>
    </time>
  )
}
