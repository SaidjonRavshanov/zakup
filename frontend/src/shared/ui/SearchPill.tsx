import { Search } from 'lucide-react'
import type { InputHTMLAttributes } from 'react'
import { cn } from '@/shared/lib/cn'

export function SearchPill({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label
      className={cn(
        'flex h-12 items-center gap-3 rounded-full border border-border-soft bg-surface-2 pl-5 pr-2',
        'transition-colors duration-300 focus-within:border-[var(--accent-border)]',
        className,
      )}
    >
      <input
        type="search"
        {...rest}
        className="min-w-0 flex-1 bg-transparent font-mono text-[12px] tracking-[0.08em] text-text outline-none placeholder:uppercase placeholder:tracking-[0.2em] placeholder:text-text-3"
      />
      <span className="grid size-9 place-items-center rounded-full bg-accent text-accent-ink">
        <Search size={16} strokeWidth={2.5} />
      </span>
    </label>
  )
}
