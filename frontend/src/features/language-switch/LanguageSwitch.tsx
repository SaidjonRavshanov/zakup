import { LOCALES, setLocale, useI18n, type Locale } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'

const OPTIONS = Object.keys(LOCALES) as Locale[]

export function LanguageSwitch({ className }: { className?: string }) {
  const { locale, t } = useI18n()
  return (
    <div
      role="radiogroup"
      aria-label={t.profile.language}
      className={cn('grid grid-cols-2 gap-1 rounded-full border border-border p-1', className)}
    >
      {OPTIONS.map((value) => {
        const active = locale === value
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            lang={value}
            onClick={() => {
              telegram.haptic.select()
              setLocale(value)
            }}
            className={cn(
              'flex h-10 items-center justify-center gap-2 rounded-full font-mono text-[10px] font-medium uppercase tracking-[0.18em] transition-colors duration-200',
              active ? 'bg-accent text-accent-ink' : 'text-text-2',
            )}
          >
            <span className={cn('tnum', active ? 'opacity-60' : 'text-text-3')}>{value}</span>
            {LOCALES[value].label}
          </button>
        )
      })}
    </div>
  )
}
