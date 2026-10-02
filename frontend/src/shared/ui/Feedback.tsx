import type { ReactNode } from 'react'
import { cn } from '@/shared/lib/cn'
import { MonoLabel } from './MonoLabel'

/** Yuklanish — spinner o'rniga skelet; shimmer faqat transform bilan. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn('relative overflow-hidden rounded-row bg-surface-2', className)}>
      <div className="absolute inset-0 animate-[shimmer_1.4s_infinite] bg-gradient-to-r from-transparent via-[var(--border)] to-transparent" />
    </div>
  )
}

interface StateProps {
  code: string
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ code, title, description, action }: StateProps) {
  return (
    <div className="flex flex-col items-center px-6 py-14 text-center">
      <MonoLabel>{code}</MonoLabel>
      <div className="mt-4 font-display text-2xl font-extrabold uppercase tracking-[-0.05em]">{title}</div>
      {description && <p className="mt-2 max-w-xs text-sm text-text-2">{description}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
