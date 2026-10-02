import { ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/shared/lib/cn'
import { MonoLabel } from './MonoLabel'

interface ListRowProps {
  meta?: string
  title: ReactNode
  subtitle?: ReactNode
  trailing?: ReactNode
  badge?: ReactNode
  onClick?: () => void
  className?: string
}

/** Ro'yxat qatori: qat'iy balandlik (virtualizatsiyaga mos), blur yo'q. */
export function ListRow({ meta, title, subtitle, trailing, badge, onClick, className }: ListRowProps) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      onClick={onClick}
      className={cn(
        'flex h-[76px] w-full items-center gap-3 rounded-row border border-border-soft bg-surface px-4 text-left shadow-[var(--shadow-card)]',
        onClick && 'transition-[border-color,transform] duration-300 ease-expo hover:border-[var(--accent-border)] active:scale-[0.985]',
        className,
      )}
    >
      <div className="min-w-0 flex-1">
        {meta && <MonoLabel className="mb-1.5 truncate">{meta}</MonoLabel>}
        <div className="truncate text-[15px] font-semibold leading-tight">{title}</div>
        {subtitle && <div className="mt-1 truncate text-[13px] text-text-2">{subtitle}</div>}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1.5">
        {badge}
        {trailing}
      </div>
      {onClick && <ChevronRight size={16} className="shrink-0 text-text-3" />}
    </Tag>
  )
}
