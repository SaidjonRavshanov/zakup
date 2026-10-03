import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { LogOut } from 'lucide-react'
import { changeMyLocale, meQuery, setActiveRole, useActiveRole, userRoles } from '@/entities/user'
import { LanguageSwitch } from '@/features/language-switch'
import { ThemeSwitch } from '@/features/theme-switch'
import { forgetDevIdentity, signOut } from '@/shared/api/auth'
import { useI18n } from '@/shared/i18n'
import { isInTelegram } from '@/shared/lib/telegram'
import { Card, LaserButton, MonoLabel, PageHeader, SegmentedControl, Skeleton, StatusBadge } from '@/shared/ui'

export default function ProfilePage() {
  const { t } = useI18n()
  const queryClient = useQueryClient()
  const { data: me } = useQuery(meQuery)
  const role = useActiveRole(me)
  const roles = me ? userRoles(me) : []
  const scoped = me?.grants.some((grant) => grant.store_id !== null) ?? false

  const exit = async () => {
    await signOut().catch(() => undefined)
    forgetDevIdentity()
    queryClient.clear()
    window.location.reload()
  }

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${t.modules.account} · ${t.profile.settings}`} title={t.profile.title} />

      {me ? (
        <Card index={`01/${t.profile.user}`} title={me.full_name}>
          <div className="mt-1 font-mono text-[11px] tracking-[0.08em] text-text-3">
            {me.username ? `@${me.username} · ` : ''}ID {me.telegram_id}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {roles.map((r) => (
              <StatusBadge key={r} tone={r === role ? 'accent' : 'neutral'}>
                {t.roles[r]}
              </StatusBadge>
            ))}
            {!scoped && <StatusBadge>{t.profile.allStores}</StatusBadge>}
            <StatusBadge tone={isInTelegram ? 'info' : 'warning'}>{isInTelegram ? 'Telegram' : t.profile.browserDev}</StatusBadge>
          </div>
        </Card>
      ) : (
        <Skeleton className="h-[140px]" />
      )}

      {roles.length > 1 && role && (
        <section className="mt-6">
          <MonoLabel className="mb-3">{`02/${t.profile.activeRole}`}</MonoLabel>
          <SegmentedControl
            className="-mx-4 px-4"
            segments={roles.map((r) => ({ value: r, label: t.roles[r] }))}
            value={role}
            onChange={setActiveRole}
          />
        </section>
      )}

      <section className="mt-6">
        <MonoLabel className="mb-3">{`03/${t.profile.language}`}</MonoLabel>
        {/* Bot xabarlari va PDF ham shu tilda bo'lishi uchun backend'ga saqlanadi */}
        <LanguageSwitch onChange={(locale) => void changeMyLocale(locale).catch(() => undefined)} />
      </section>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`04/${t.profile.theme}`}</MonoLabel>
        <ThemeSwitch />
      </section>

      {import.meta.env.DEV && (
        <Link to="/dev/ui" className="mt-6 block">
          <Card index="05/Dev" title={t.profile.uiKit} interactive>
            <p className="mt-2 text-sm text-text-2">{t.profile.uiKitHint}</p>
          </Card>
        </Link>
      )}

      {!isInTelegram && (
        <LaserButton variant="ghost" block className="mt-6" icon={<LogOut size={14} />} onClick={() => void exit()}>
          {t.auth.signOut}
        </LaserButton>
      )}
    </div>
  )
}
