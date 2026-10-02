import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import './laser-button.css'

type Variant = 'primary' | 'ghost' | 'danger'
type Size = 'md' | 'lg'

interface LaserButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
  block?: boolean
}

const VARIANTS: Record<Variant, string> = {
  primary: 'laser bg-accent text-accent-ink shadow-[0_0_20px_var(--accent-glow)]',
  ghost: 'border border-border bg-transparent text-text hover:border-[var(--accent-border)]',
  danger: 'border border-danger/40 bg-transparent text-danger',
}

const SIZES: Record<Size, string> = {
  md: 'h-11 px-5 text-[11px]',
  lg: 'h-14 px-7 text-xs',
}

export function LaserButton({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  block = false,
  disabled,
  className,
  children,
  onClick,
  ...rest
}: LaserButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      onClick={(event) => {
        telegram.haptic.impact('light')
        onClick?.(event)
      }}
      className={cn(
        'relative inline-flex select-none items-center justify-center gap-2 overflow-hidden rounded-full',
        'font-mono font-medium uppercase tracking-[0.2em] transition-[transform,opacity] duration-150 ease-expo',
        'active:scale-[0.97] disabled:pointer-events-none disabled:opacity-40',
        VARIANTS[variant],
        SIZES[size],
        block && 'w-full',
        className,
      )}
    >
      {loading ? <span className="size-4 animate-spin rounded-full border-2 border-current border-r-transparent" /> : icon}
      <span>{children}</span>
    </button>
  )
}
