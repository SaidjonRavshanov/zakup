/** Katalog formalari uchun kichik yordamchilar (kit'da hali yo'q): native select va o'ng tomonda birlikli input. */
import { ChevronDown } from 'lucide-react'
import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'
import { Input, labellable } from '@/shared/kit'
import { cn } from '@/shared/lib/cn'

export function Select({
  options,
  className,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & { options: ReadonlyArray<{ value: string; label: string }> }) {
  return (
    <div className="relative">
      <select {...rest} className={cn('input min-h-11 appearance-none pr-10 text-[16px]', className)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown size={20} className="pointer-events-none absolute right-3 top-3 text-n7" />
    </div>
  )
}

export function SuffixInput({ suffix, className, ...rest }: InputHTMLAttributes<HTMLInputElement> & { suffix?: ReactNode; invalid?: boolean }) {
  if (!suffix) return <Input {...rest} className={className} />
  return (
    <div className="relative">
      <Input {...rest} className={cn('pr-14', className)} />
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[15px] text-n7">{suffix}</span>
    </div>
  )
}

// Field yorlig'i ichki <select> / <input> bilan bog'lanadi
labellable(Select)
labellable(SuffixInput)

/** Forma bo'limi nomi (13px). */
export function FormSection({ children }: { children: ReactNode }) {
  return <div className="mt-2 text-[13px] font-medium text-n7">{children}</div>
}
