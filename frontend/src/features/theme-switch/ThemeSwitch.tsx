import { useZk } from '@/shared/i18n/use-zk'
import { Seg } from '@/shared/kit'
import { telegram } from '@/shared/lib/telegram'
import type { ThemePref } from '@/shared/lib/theme'
import { setThemePref, useTheme } from '@/shared/lib/use-theme'

export function ThemeSwitch({ className }: { className?: string }) {
  const { pref } = useTheme()
  const { z } = useZk()
  return (
    <Seg<ThemePref>
      className={className}
      value={pref}
      options={[
        { value: 'light', label: z.th_light },
        { value: 'dark', label: z.th_dark },
        { value: 'system', label: z.th_system },
      ]}
      onChange={(value) => {
        telegram.haptic.select()
        setThemePref(value)
      }}
    />
  )
}
