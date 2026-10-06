import { LOCALES, setLocale, useI18n, type Locale } from '@/shared/i18n'
import { Seg } from '@/shared/kit'
import { telegram } from '@/shared/lib/telegram'

const OPTIONS = [
  { value: 'uz', label: "O'zbekcha" },
  { value: 'ru', label: 'Русский' },
] as const satisfies ReadonlyArray<{ value: Locale; label: string }>

interface LanguageSwitchProps {
  className?: string
  size?: 'sm' | 'md'
  /** Til tanlangandan keyin (masalan, profilga saqlash). */
  onChange?: (locale: Locale) => void
}

export function LanguageSwitch({ className, size, onChange }: LanguageSwitchProps) {
  const { locale } = useI18n()
  return (
    <Seg
      className={className}
      size={size}
      value={locale}
      options={OPTIONS.filter((o) => o.value in LOCALES)}
      onChange={(value) => {
        if (value === locale) return
        telegram.haptic.select()
        setLocale(value)
        onChange?.(value)
      }}
    />
  )
}
