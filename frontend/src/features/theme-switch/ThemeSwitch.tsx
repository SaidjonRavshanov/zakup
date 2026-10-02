import { Monitor, Moon, Sun } from 'lucide-react'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import type { ThemePref } from '@/shared/lib/theme'
import { setThemePref, useTheme } from '@/shared/lib/use-theme'

const OPTIONS = [
  { value: 'system', icon: Monitor },
  { value: 'light', icon: Sun },
  { value: 'dark', icon: Moon },
] as const satisfies ReadonlyArray<{ value: ThemePref; icon: unknown }>

export function ThemeSwitch({ className }: { className?: string }) {
  const { pref } = useTheme()
  const { t } = useI18n()
  return (
    <div role="radiogroup" aria-label={t.profile.theme} className={cn('grid grid-cols-3 gap-1 rounded-full border border-border p-1', className)}>
      {OPTIONS.map(({ value, icon: Icon }) => {
        const active = pref === value
        return (
          <button
            key={value}
            role="radio"
            aria-checked={active}
            onClick={() => {
              telegram.haptic.select()
              setThemePref(value)
            }}
            className={cn(
              'flex h-10 items-center justify-center gap-2 rounded-full font-mono text-[10px] font-medium uppercase tracking-[0.18em] transition-colors duration-200',
              active ? 'bg-accent text-accent-ink' : 'text-text-2',
            )}
          >
            <Icon size={14} />
            {t.theme[value]}
          </button>
        )
      })}
    </div>
  )
}
