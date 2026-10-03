import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import { MonoLabel } from './MonoLabel'

const control =
  'h-12 w-full rounded-full border border-border-soft bg-surface-2 px-5 text-[15px] text-text outline-none transition-colors duration-300 focus:border-[var(--accent-border)] disabled:opacity-50'

interface FieldShellProps {
  label: string
  hint?: ReactNode
  className?: string
  children: ReactNode
}

function FieldShell({ label, hint, className, children }: FieldShellProps) {
  return (
    <label className={cn('flex min-w-0 flex-col gap-2', className)}>
      <MonoLabel>{label}</MonoLabel>
      {children}
      {hint && <span className="px-2 text-[12px] text-text-3">{hint}</span>}
    </label>
  )
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: ReactNode
  /** Birlik / valyuta — maydon ichida o'ngda. */
  suffix?: string
}

export function TextField({ label, hint, suffix, className, ...rest }: TextFieldProps) {
  return (
    <FieldShell label={label} hint={hint} className={className}>
      <span className="relative block">
        <input {...rest} className={cn(control, suffix && 'pr-16', 'tnum')} />
        {suffix && (
          <span className="pointer-events-none absolute right-5 top-1/2 -translate-y-1/2 font-mono text-[10px] uppercase tracking-[0.2em] text-text-3">
            {suffix}
          </span>
        )}
      </span>
    </FieldShell>
  )
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  hint?: ReactNode
  options: ReadonlyArray<{ value: string; label: string }>
}

export function SelectField({ label, hint, options, className, ...rest }: SelectFieldProps) {
  return (
    <FieldShell label={label} hint={hint} className={className}>
      <select {...rest} className={cn(control, 'appearance-none bg-[length:12px] pr-10')}>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  )
}

interface ChipsFieldProps<T extends string | number> {
  label: string
  options: ReadonlyArray<{ value: T; label: string }>
  value: ReadonlyArray<T>
  onChange: (value: T[]) => void
  hint?: ReactNode
}

/** Bir nechta tanlov (hafta kunlari va h.k.): tugmalar qatori. */
export function ChipsField<T extends string | number>({ label, options, value, onChange, hint }: ChipsFieldProps<T>) {
  return (
    <div className="flex flex-col gap-2">
      <MonoLabel>{label}</MonoLabel>
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const on = value.includes(option.value)
          return (
            <button
              key={String(option.value)}
              type="button"
              aria-pressed={on}
              onClick={() => {
                telegram.haptic.select()
                onChange(on ? value.filter((v) => v !== option.value) : [...value, option.value])
              }}
              className={cn(
                'h-10 min-w-11 rounded-full border px-3 font-mono text-[11px] font-medium uppercase tracking-[0.12em] transition-colors duration-200',
                on ? 'border-[var(--accent-border)] bg-accent-wash text-accent-text' : 'border-border text-text-2',
              )}
            >
              {option.label}
            </button>
          )
        })}
      </div>
      {hint && <span className="px-2 text-[12px] text-text-3">{hint}</span>}
    </div>
  )
}

/** Forma xatosi (backend xabari foydalanuvchi tilida keladi). */
export function FormError({ children }: { children: ReactNode }) {
  return children ? <p className="rounded-row border border-danger/30 px-4 py-3 text-sm text-danger">{children}</p> : null
}
