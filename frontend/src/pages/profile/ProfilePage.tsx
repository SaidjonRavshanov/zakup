import { Link } from '@tanstack/react-router'
import { LanguageSwitch } from '@/features/language-switch'
import { ThemeSwitch } from '@/features/theme-switch'
import { useI18n, type Locale } from '@/shared/i18n'
import { isInTelegram } from '@/shared/lib/telegram'
import { Card, MonoLabel, PageHeader, StatusBadge } from '@/shared/ui'

// TODO(identity): foydalanuvchi va ombor /me endpoint'idan keladi
const DEMO_STORE: Record<Locale, string> = { uz: 'Oshxona', ru: 'Кухня' }

export default function ProfilePage() {
  const { t, locale } = useI18n()
  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${t.modules.account} · ${t.profile.settings}`} title={t.profile.title} />

      <Card index={`01/${t.profile.user}`} title="Aziz Karimov">
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge tone="accent">{t.roles.buyer}</StatusBadge>
          <StatusBadge>{DEMO_STORE[locale]}</StatusBadge>
          <StatusBadge tone={isInTelegram ? 'info' : 'warning'}>{isInTelegram ? 'Telegram' : t.profile.browserDev}</StatusBadge>
        </div>
      </Card>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`02/${t.profile.language}`}</MonoLabel>
        <LanguageSwitch />
      </section>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`03/${t.profile.theme}`}</MonoLabel>
        <ThemeSwitch />
      </section>

      {import.meta.env.DEV && (
        <Link to="/dev/ui" className="mt-6 block">
          <Card index="04/Dev" title={t.profile.uiKit} interactive>
            <p className="mt-2 text-sm text-text-2">{t.profile.uiKitHint}</p>
          </Card>
        </Link>
      )}
    </div>
  )
}
