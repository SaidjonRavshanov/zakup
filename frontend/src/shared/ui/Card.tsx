import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/shared/lib/cn'
import { MonoLabel } from './MonoLabel'

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Yuqoridagi mono indeks, masalan "01/ZAYAVKA". */
  index?: string
  title?: ReactNode
  footer?: ReactNode
  interactive?: boolean
  padded?: boolean
}

/** Luminosity Card (DESIGN_SYSTEM.md §5.1): yuqori-chap burchakdan laym nur. */
export function Card({ index, title, footer, interactive = false, padded = true, className, children, ...rest }: CardProps) {
  return (
    <div
      {...rest}
      className={cn(
        'relative flex flex-col overflow-hidden rounded-card border border-border-soft bg-surface shadow-[var(--shadow-card)]',
        'bg-[radial-gradient(circle_at_top_left,var(--accent-wash),transparent_60%)]',
        'transition-[border-color,transform] duration-500 ease-expo',
        interactive && 'cursor-pointer hover:border-[var(--accent-border)] active:scale-[0.985]',
        padded && 'p-5',
        className,
      )}
    >
      {index && <MonoLabel className="mb-3">{index}</MonoLabel>}
      {title && <div className="font-display text-lg font-extrabold uppercase leading-tight tracking-[-0.03em]">{title}</div>}
      {children}
      {footer && <div className="mt-auto pt-4">{footer}</div>}
    </div>
  )
}
