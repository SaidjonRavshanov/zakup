import type { HTMLAttributes } from 'react'
import { cn } from '@/shared/lib/cn'

export function MonoLabel({ className, ...rest }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      {...rest}
      className={cn('block font-mono text-[10px] font-medium uppercase leading-none tracking-[0.24em] text-text-3', className)}
    />
  )
}
