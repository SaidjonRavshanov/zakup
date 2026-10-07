/**
 * Industry dizayn-tizimi komponentlari (Claude Design prototipi bo'yicha): to'rtburchak, ingichka chiziq,
 * burchaklarda "+" belgilar (blueprint). Rang — faqat tokenlardan (app/styles/tokens.css).
 */
import { ChevronRight, Info, Loader2, Minus, Plus, Search, TriangleAlert, X } from 'lucide-react'
import { cloneElement, isValidElement, useId } from 'react'
import type { CSSProperties, ChangeEvent, InputHTMLAttributes, KeyboardEvent, ReactElement, ReactNode, TextareaHTMLAttributes } from 'react'
import { cn } from '@/shared/lib/cn'
import { LABELLABLE, labellable } from './field-controls'

// ---------------------------------------------------------------- blueprint ramka

export function Corners() {
  return (
    <>
      <i className="corner tl" />
      <i className="corner tr" />
      <i className="corner bl" />
      <i className="corner br" />
    </>
  )
}

interface BlueprintProps {
  children?: ReactNode
  className?: string
  style?: CSSProperties
  onClick?: () => void
}

/** Ramka + burchak belgilar. Bosiladigan bo'lsa — hover fon. */
export function Blueprint({ children, className, style, onClick }: BlueprintProps) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      style={style}
      className={cn(
        'blueprint block w-full text-left text-ink',
        onClick && 'zk-hover cursor-pointer bg-transparent',
        className,
      )}
    >
      <Corners />
      {children}
    </Tag>
  )
}

// ---------------------------------------------------------------- tugmalar

type BtnVariant = 'primary' | 'secondary' | 'ghost'

interface BtnProps {
  children?: ReactNode
  variant?: BtnVariant
  /** 44px (md) yoki 48px (lg) — barmoq uchun. */
  size?: 'sm' | 'md' | 'lg'
  icon?: ReactNode
  block?: boolean
  danger?: boolean
  disabled?: boolean
  loading?: boolean
  type?: 'button' | 'submit'
  className?: string
  style?: CSSProperties
  onClick?: () => void
}

const BTN_SIZE = { sm: 'min-h-9 text-[14px] px-3', md: 'min-h-11 text-[15px] px-3.5', lg: 'min-h-12 text-[17px] px-4' }

export function Btn({
  children,
  variant = 'secondary',
  size = 'md',
  icon,
  block,
  danger,
  disabled,
  loading,
  type = 'button',
  className,
  style,
  onClick,
}: BtnProps) {
  const primary = variant === 'primary'
  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      style={{
        ...(danger && !primary ? { color: 'var(--zk-danger)' } : null),
        ...(danger && primary ? { background: 'var(--zk-danger)', borderColor: 'var(--zk-danger)' } : null),
        ...style,
      }}
      className={cn(
        'btn',
        `btn-${variant}`,
        primary && 'blueprint',
        BTN_SIZE[size],
        variant === 'ghost' && 'px-1.5',
        block && 'w-full',
        className,
      )}
    >
      {primary && <Corners />}
      {loading ? <Loader2 size={18} className="animate-spin" /> : icon}
      {children}
    </button>
  )
}

// ---------------------------------------------------------------- tag (holat)

export type Tone = 'neutral' | 'accent' | 'solid' | 'ok' | 'warn' | 'danger'

const TONE: Record<Tone, [string, string, string]> = {
  neutral: ['var(--color-neutral-200)', 'var(--color-neutral-800)', 'var(--color-neutral-200)'],
  accent: ['var(--color-accent-100)', 'var(--color-accent-800)', 'var(--color-accent-100)'],
  solid: ['var(--color-accent)', 'var(--color-bg)', 'var(--color-accent)'],
  ok: ['transparent', 'var(--color-accent-700)', 'var(--color-accent)'],
  warn: ['var(--zk-warn-bg)', 'var(--zk-warn)', 'var(--zk-warn-bg)'],
  danger: ['var(--zk-danger-bg)', 'var(--zk-danger)', 'var(--zk-danger-bg)'],
}

export function Tag({ tone = 'neutral', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  const [bg, fg, bd] = TONE[tone]
  return (
    <span
      className={cn('tag whitespace-nowrap text-[12px]', className)}
      style={{ background: bg, color: fg, border: `1px solid ${bd}` }}
    >
      {children}
    </span>
  )
}

// ---------------------------------------------------------------- tanlovlar

export interface SegOption<T extends string> {
  value: T
  label: ReactNode
  count?: number | string | null
}

interface SegProps<T extends string> {
  options: ReadonlyArray<SegOption<T>>
  value: T
  onChange: (value: T) => void
  /** Ko'p variant (filtrlar) — gorizontal aylanadi. */
  scroll?: boolean
  size?: 'sm' | 'md'
  className?: string
}

/** Segment: bitta ramkada yonma-yon tugmalar, tanlangani — accent fon. */
export function Seg<T extends string>({ options, value, onChange, scroll, size = 'md', className }: SegProps<T>) {
  return (
    <div className={cn('flex border border-line', scroll && 'zk-noscroll overflow-x-auto', className)} role="tablist">
      {options.map((o) => {
        const on = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            role="tab"
            aria-selected={on}
            onClick={() => onChange(o.value)}
            className={cn(
              'flex items-center justify-center gap-1.5 whitespace-nowrap border-r border-line last:border-r-0',
              scroll ? 'flex-[1_0_auto] px-3' : 'flex-1 px-2',
              size === 'sm' ? 'min-h-10 text-[13px]' : 'min-h-11 text-[14px]',
              !on && 'zk-hover',
            )}
            style={on ? { background: 'var(--color-accent)', color: 'var(--color-bg)' } : { color: 'var(--color-text)' }}
          >
            {o.label}
            {o.count !== undefined && o.count !== null && o.count !== '' && (
              <span className="text-[12px] opacity-75">{o.count}</span>
            )}
          </button>
        )
      })}
    </div>
  )
}

/** Chiplar: alohida ramkali tugmalar, o'raladi (omborlar, kanallar, rollar). */
export function Chips<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: ReadonlyArray<SegOption<T>>
  value: T | ReadonlyArray<T>
  onChange: (value: T) => void
  className?: string
}) {
  const selected = (v: T) => (Array.isArray(value) ? value.includes(v) : value === v)
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {options.map((o) => {
        const on = selected(o.value)
        return (
          <button
            key={o.value}
            type="button"
            aria-pressed={on}
            onClick={() => onChange(o.value)}
            className={cn('min-h-11 border border-line px-3.5 text-[15px]', !on && 'zk-hover')}
            style={on ? { background: 'var(--color-accent)', color: 'var(--color-bg)' } : { color: 'var(--color-text)' }}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------- sarlavhalar

/** Sahifa sarlavhasi: kichik izoh (kicker) + katta sarlavha + o'ng tomonda badge / tugma. */
export function PageHead({
  title,
  kicker,
  sub,
  aside,
  size = 34,
}: {
  title: ReactNode
  kicker?: ReactNode
  sub?: ReactNode
  aside?: ReactNode
  size?: 32 | 34
}) {
  return (
    <div className="flex items-start justify-between gap-3 pt-2">
      <div className="min-w-0">
        {kicker && <div className="text-[14px] text-n7">{kicker}</div>}
        <h1 className="m-0 break-words" style={{ fontSize: size }}>
          {title}
        </h1>
        {sub && <div className="text-[14px] text-n7">{sub}</div>}
      </div>
      {aside && <div className="mt-1.5 flex shrink-0 items-center gap-2">{aside}</div>}
    </div>
  )
}

/** Bo'lim nomi (13px, kul rang) — o'ng tomonda ixtiyoriy matn / tugma. */
export function Section({ children, aside, className }: { children: ReactNode; aside?: ReactNode; className?: string }) {
  return (
    <div className={cn('mt-6 flex min-h-6 items-center justify-between gap-3', className)}>
      <div className="text-[13px] font-medium text-n7">{children}</div>
      {aside && <div className="text-[13px] text-n7">{aside}</div>}
    </div>
  )
}

// ---------------------------------------------------------------- ro'yxat qatori

interface RowProps {
  meta?: ReactNode
  title: ReactNode
  sub?: ReactNode
  amount?: ReactNode
  badge?: ReactNode
  /** Badge chap tomonda tepada, o'ngda summa + strelka (vazifalar ro'yxati). */
  badgeTop?: boolean
  lead?: ReactNode
  onClick?: () => void
  className?: string
}

export function Row({ meta, title, sub, amount, badge, badgeTop, lead, onClick, className }: RowProps) {
  const Tag = onClick ? 'button' : 'div'
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={cn(
        'grid w-full min-h-[72px] items-center gap-x-3 gap-y-0.5 border-b border-line py-3 text-left text-ink',
        lead ? 'grid-cols-[auto_minmax(0,1fr)_auto]' : 'grid-cols-[minmax(0,1fr)_auto]',
        onClick && 'zk-hover cursor-pointer',
        className,
      )}
    >
      {lead && <div className="self-start">{lead}</div>}
      <div className={cn('min-w-0', badgeTop && 'flex flex-col items-start gap-1')}>
        {badgeTop && badge}
        {meta && <div className="truncate text-[13px] text-n7">{meta}</div>}
        <div className="text-[16px] font-medium leading-tight">{title}</div>
        {sub && <div className="text-[13px] text-n7">{sub}</div>}
      </div>
      {badgeTop ? (
        <div className="flex items-center gap-1.5 whitespace-nowrap text-[15px] font-medium">
          {amount}
          {onClick && <ChevronRight size={20} />}
        </div>
      ) : (
        <div className="flex flex-col items-end gap-1.5">
          {amount !== undefined && amount !== null && (
            <div className="whitespace-nowrap text-[15px] font-medium">{amount}</div>
          )}
          {badge}
        </div>
      )}
    </Tag>
  )
}

/** Oddiy havola-qator: matn + strelka (bog'langan hujjatlar). */
export function LinkRow({ children, aside, onClick }: { children: ReactNode; aside?: ReactNode; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="zk-hover flex min-h-[52px] w-full items-center gap-3 border-b border-line text-left text-[15px] text-ink"
    >
      <div className="min-w-0 flex-1">{children}</div>
      {aside}
      <ChevronRight size={20} />
    </button>
  )
}

// ---------------------------------------------------------------- raqamlar

export interface Cell {
  label: ReactNode
  value: ReactNode
  color?: string
}

/** Kataklar to'ri (KPI): 1px chiziq bilan ajratilgan. `cols` — aniq ustunlar, yo'q bo'lsa avto (≥150px). */
export function Cells({ items, cols, size = 24, className }: { items: Cell[]; cols?: number; size?: number; className?: string }) {
  return (
    <div
      className={cn('grid gap-px border border-line bg-line', className)}
      style={{ gridTemplateColumns: cols ? `repeat(${cols}, minmax(0, 1fr))` : 'repeat(auto-fill, minmax(150px, 1fr))' }}
    >
      {items.map((c, i) => (
        <div key={i} className="flex min-h-[76px] flex-col justify-between gap-1 bg-ground p-3">
          <div className="text-[13px] leading-tight text-n7">{c.label}</div>
          <div
            className="whitespace-nowrap font-head leading-none"
            style={{ fontSize: size, fontWeight: 600, color: c.color ?? 'var(--color-text)' }}
          >
            {c.value}
          </div>
        </div>
      ))}
    </div>
  )
}

/** Kalit — qiymat ro'yxati. */
export function KV({ rows, className }: { rows: Array<[ReactNode, ReactNode] | null | false>; className?: string }) {
  return (
    <div className={className}>
      {rows.filter(Boolean).map((row, i) => {
        const [k, v] = row as [ReactNode, ReactNode]
        return (
          <div key={i} className="flex justify-between gap-3 border-b border-line py-2.5 text-[15px]">
            <span className="text-n7">{k}</span>
            <span className="text-right">{v}</span>
          </div>
        )
      })}
    </div>
  )
}

/** Jami qatori: chapda nom, o'ngda katta summa. */
export function TotalLine({ label, value, size = 24 }: { label: ReactNode; value: ReactNode; size?: number }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-line py-3.5">
      <span className="text-[15px] text-n7">{label}</span>
      <span className="whitespace-nowrap font-head" style={{ fontSize: size, fontWeight: 600 }}>
        {value}
      </span>
    </div>
  )
}

// ---------------------------------------------------------------- xabarlar

const BANNER: Record<'warn' | 'danger' | 'info', { bg: string; fg: string }> = {
  warn: { bg: 'var(--zk-warn-bg)', fg: 'var(--zk-warn)' },
  danger: { bg: 'var(--zk-danger-bg)', fg: 'var(--zk-danger)' },
  info: { bg: 'var(--color-accent-100)', fg: 'var(--color-accent-800)' },
}

export function Banner({
  tone = 'warn',
  icon,
  children,
  action,
  onClose,
  onClick,
  className,
}: {
  tone?: 'warn' | 'danger' | 'info'
  icon?: ReactNode
  children: ReactNode
  action?: ReactNode
  onClose?: () => void
  onClick?: () => void
  className?: string
}) {
  const c = BANNER[tone]
  // Bosiladigan banner — klaviaturadan ham (Enter / Space)
  const clickable = onClick
    ? {
        role: 'button',
        tabIndex: 0,
        onClick,
        onKeyDown: (e: KeyboardEvent<HTMLDivElement>) => {
          if (e.target !== e.currentTarget || (e.key !== 'Enter' && e.key !== ' ')) return
          e.preventDefault()
          onClick()
        },
      }
    : { role: tone === 'danger' ? 'alert' : undefined }
  return (
    <div
      {...clickable}
      className={cn('mt-3 flex items-start gap-2.5 p-3 text-[14px]', onClick && 'cursor-pointer', className)}
      style={{ background: c.bg, color: c.fg }}
    >
      <span className="mt-px">{icon ?? (tone === 'info' ? <Info size={20} /> : <TriangleAlert size={20} />)}</span>
      <div className="flex min-w-0 flex-1 flex-col items-start gap-2">
        <div className="break-words">{children}</div>
        {action}
      </div>
      {onClose && (
        <button type="button" onClick={onClose} className="grid size-7 place-items-center" aria-label="×">
          <X size={18} />
        </button>
      )}
      {onClick && !onClose && <ChevronRight size={20} />}
    </div>
  )
}

export function Empty({ title, hint, className }: { title: ReactNode; hint?: ReactNode; className?: string }) {
  return (
    <div className={cn('py-12 text-center', className)}>
      <div className="font-head text-[22px]" style={{ fontWeight: 600 }}>
        {title}
      </div>
      {hint && <div className="text-[14px] text-n7">{hint}</div>}
    </div>
  )
}

export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return <span className={cn('block bg-n2', className)} style={{ animation: 'zkPulse 1.4s ease-in-out infinite', ...style }} />
}

/** Ro'yxat yuklanmoqda: n ta qator. */
export function RowsSkeleton({ n = 4 }: { n?: number }) {
  return (
    <div className="flex flex-col">
      {Array.from({ length: n }, (_, i) => (
        <div key={i} className="flex flex-col gap-2 border-b border-line py-3.5">
          <Skeleton className="h-3 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------- formalar

export function Field({ label, hint, error, children, className, id }: {
  label?: ReactNode
  hint?: ReactNode
  error?: ReactNode
  children: ReactNode
  className?: string
  /** Boshqaruv elementi id'si; berilmasa — avtomatik (bola Input/Textarea/select bo'lsa). */
  id?: string
}) {
  const autoId = useId()
  const control = isValidElement<{ id?: string }>(children) && LABELLABLE.has(children.type) ? children : null
  const controlId = id ?? control?.props.id ?? (control ? autoId : undefined)
  return (
    <div className={cn('field', className)}>
      {label && <label htmlFor={controlId}>{label}</label>}
      {control && !control.props.id ? cloneElement(control as ReactElement<{ id?: string }>, { id: controlId }) : children}
      {error ? (
        <div className="mt-1 text-[13px] text-danger">{error}</div>
      ) : (
        hint && <div className="mt-1 text-[13px] text-n7">{hint}</div>
      )}
    </div>
  )
}

export function Input({ className, invalid, ...rest }: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }) {
  return (
    <input
      {...rest}
      className={cn('input min-h-11 text-[16px]', className)}
      style={invalid ? { borderColor: 'var(--zk-danger)', ...rest.style } : rest.style}
    />
  )
}

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...rest} className={cn('input min-h-[72px] text-[16px]', className)} />
}

labellable(Input)
labellable(Textarea)

export function SearchInput({
  value,
  onChange,
  placeholder,
  autoFocus,
  className,
}: {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  autoFocus?: boolean
  className?: string
}) {
  return (
    <div className={cn('relative', className)}>
      <Search size={20} className="pointer-events-none absolute left-3 top-3 text-n7" />
      <input
        type="search"
        className="input min-h-11 text-[16px]"
        style={{ paddingLeft: 40 }}
        value={value}
        autoFocus={autoFocus}
        placeholder={placeholder}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
      />
    </div>
  )
}

/** Katta miqdor stepperi: − [qiymat birlik] +. Vergul ham, nuqta ham qabul qilinadi. */
export function Stepper({
  value,
  onChange,
  step = 1,
  min = 0,
  unit,
  size = 64,
  label,
}: {
  value: string
  onChange: (raw: string) => void
  step?: number
  min?: number
  unit?: string
  size?: 56 | 64
  label?: string
}) {
  const parsed = Number(value.replace(/\s/g, '').replace(',', '.'))
  const num = Number.isFinite(parsed) ? parsed : 0
  const set = (v: number) => onChange(String(Math.round(v * 10_000) / 10_000).replace('.', ','))
  // "−" qiymatni hech qachon oshirmaydi: min'dan kichik qiymat o'z joyida qoladi (sakramaydi)
  const dec = () => set(Math.max(Math.min(min, num), num - step))
  const inc = () => set(Math.max(min, num + step))
  const cell = size === 64 ? 'min-h-16' : 'min-h-14'
  return (
    <div className="grid border border-line" style={{ gridTemplateColumns: `${size}px minmax(0,1fr) ${size}px` }}>
      <button
        type="button"
        aria-label="−"
        onClick={dec}
        className={cn('grid place-items-center border-r border-line text-ink active:bg-a2', cell)}
      >
        <Minus size={20} />
      </button>
      <div className="flex items-center justify-center gap-1.5 px-1.5">
        <input
          aria-label={label}
          value={value}
          inputMode="decimal"
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            'min-w-0 border-0 bg-transparent font-head text-ink outline-none',
            unit ? 'w-full text-right' : 'w-full text-center',
          )}
          style={{ fontSize: size === 64 ? 30 : 24, fontWeight: 600 }}
        />
        {unit && <span className="w-2/5 shrink-0 text-[16px] text-n7">{unit}</span>}
      </div>
      <button
        type="button"
        aria-label="+"
        onClick={inc}
        className={cn('grid place-items-center border-l border-line text-ink active:bg-a2', cell)}
      >
        <Plus size={20} />
      </button>
    </div>
  )
}

/** Kvadrat belgilash katagi. */
export function Check({ on, onToggle, label }: { on: boolean; onToggle: () => void; label?: string }) {
  return (
    <button type="button" aria-pressed={on} aria-label={label} onClick={onToggle} className="flex w-10 shrink-0 items-start pt-0.5">
      <span
        className="grid size-[22px] place-items-center"
        style={{ border: '1.5px solid var(--color-accent)', background: on ? 'var(--color-accent)' : 'transparent', color: 'var(--color-bg)' }}
      >
        {on && (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M20 6 9 17l-5-5" />
          </svg>
        )}
      </span>
    </button>
  )
}

/** To'rtburchak almashtirgich (rollar). */
export function Switch({ on }: { on: boolean }) {
  return (
    <span
      className="relative block h-6 w-11 shrink-0 border border-line"
      style={{ background: on ? 'var(--color-accent)' : 'var(--color-neutral-200)' }}
    >
      <span
        className="absolute top-0.5 block size-[18px] border border-line bg-ground transition-[left] duration-150"
        style={{ left: on ? 22 : 2 }}
      />
    </span>
  )
}

/** Pastki chiziqli foto-yuklash maydoni (nakladnoy, chek). */
export function DropZone({ icon, title, hint, onClick, height = 96 }: {
  icon: ReactNode
  title: ReactNode
  hint?: ReactNode
  onClick: () => void
  height?: number
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full flex-col items-center justify-center gap-1.5 bg-transparent text-[17px] font-medium text-a7 hover:bg-a1"
      style={{ minHeight: height, border: '1.5px dashed var(--color-accent)' }}
    >
      {icon}
      {title}
      {hint && <span className="text-[13px] font-normal text-n7">{hint}</span>}
    </button>
  )
}
