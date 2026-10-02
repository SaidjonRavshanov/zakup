import { cn } from '@/shared/lib/cn'

export type Tone = 'neutral' | 'accent' | 'info' | 'warning' | 'danger'

const TONES: Record<Tone, string> = {
  neutral: 'text-text-2 border-border',
  accent: 'text-accent-text border-[var(--accent-border)] bg-accent-wash',
  info: 'text-info border-info/30',
  warning: 'text-warning border-warning/30',
  danger: 'text-danger border-danger/30',
}

interface StatusBadgeProps {
  tone?: Tone
  children: string
  className?: string
}

/** Status — rang + matn (faqat rangga tayanmaymiz, a11y). */
export function StatusBadge({ tone = 'neutral', children, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex h-6 shrink-0 items-center gap-1.5 rounded-full border px-2.5 font-mono text-[9px] font-medium uppercase tracking-[0.18em]',
        TONES[tone],
        className,
      )}
    >
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {children}
    </span>
  )
}
