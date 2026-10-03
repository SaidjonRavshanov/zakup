import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Check, Power, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  ROLES,
  activateUser,
  deactivateUser,
  meQuery,
  setUserRoles,
  userRoles,
  usersQuery,
  type Role,
} from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { cn } from '@/shared/lib/cn'
import { telegram } from '@/shared/lib/telegram'
import { Card, EmptyState, LaserButton, MonoLabel, PageHeader, Skeleton, StatusBadge } from '@/shared/ui'

export default function UserEditPage() {
  const { userId } = useParams({ from: '/shell/admin/users/$userId' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const { data: me } = useQuery(meQuery)
  const { data: users, isPending } = useQuery(usersQuery)
  const user = users?.find((u) => u.id === userId)
  const isSelf = user?.id === me?.id

  // Tahrir qoralamasi; null — serverdagi holat
  const [draft, setDraft] = useState<Set<Role> | null>(null)
  const selected = draft ?? new Set(user ? userRoles(user) : [])

  useEffect(() => telegram.backButton(() => navigate({ to: '/admin/users' })), [navigate])

  const refresh = () => queryClient.invalidateQueries({ queryKey: usersQuery.queryKey })
  const toggleActive = useMutation({
    mutationFn: () => (user!.is_active ? deactivateUser(user!.id) : activateUser(user!.id)),
    onSuccess: refresh,
  })
  const saveRoles = useMutation({
    // Hozircha rollar barcha omborlarga; ombor bo'yicha cheklangan mavjud rollar saqlanib qoladi
    mutationFn: () =>
      setUserRoles(user!.id, [
        ...[...selected].map((role) => ({ role, store_id: null })),
        ...user!.grants.filter((grant) => grant.store_id !== null),
      ]),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      await refresh()
      setDraft(null)
    },
  })

  if (isPending) return <Skeleton className="mt-20 h-[200px]" />
  if (!user) return <EmptyState code="404" title={t.common.notFound} />

  const dirty = userRoles(user).join() !== ROLES.filter((r) => selected.has(r)).join()
  const failure = toggleActive.error ?? saveRoles.error

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.users.meta} title={t.users.title} />

      <Card index={`01/${t.profile.user}`} title={user.full_name}>
        <div className="mt-1 font-mono text-[11px] tracking-[0.08em] text-text-3">
          {user.username ? `@${user.username} · ` : ''}ID {user.telegram_id}
        </div>
        <div className="mt-4 flex items-center justify-between gap-3">
          <StatusBadge tone={user.is_active ? 'accent' : 'warning'}>
            {user.is_active ? t.users.active : t.users.pending}
          </StatusBadge>
          {!isSelf && (
            <LaserButton
              variant={user.is_active ? 'danger' : 'primary'}
              icon={<Power size={14} />}
              loading={toggleActive.isPending}
              onClick={() => toggleActive.mutate()}
            >
              {user.is_active ? t.users.deactivate : t.users.activate}
            </LaserButton>
          )}
        </div>
      </Card>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`02/${t.users.roles}`}</MonoLabel>
        <div className="grid grid-cols-2 gap-2">
          {ROLES.map((role) => {
            const on = selected.has(role)
            const locked = isSelf && role === 'admin' // o'zidan admin'ni olib bo'lmaydi (backend ham tekshiradi)
            return (
              <button
                key={role}
                aria-pressed={on}
                disabled={locked}
                onClick={() => {
                  telegram.haptic.select()
                  const next = new Set(selected)
                  if (on) next.delete(role)
                  else next.add(role)
                  setDraft(next)
                }}
                className={cn(
                  'flex h-12 items-center justify-between rounded-full border px-4 text-left text-[13px] font-semibold transition-colors duration-200',
                  on ? 'border-[var(--accent-border)] bg-accent-wash text-accent-text' : 'border-border text-text-2',
                  locked && 'opacity-60',
                )}
              >
                {t.roles[role]}
                {on && <Check size={16} />}
              </button>
            )
          })}
        </div>
        <p className="mt-3 text-[12px] text-text-3">{t.users.rolesHint}</p>
      </section>

      {failure && <p className="mt-4 text-sm text-danger">{describeError(failure, t)}</p>}

      <LaserButton
        size="lg"
        block
        className="mt-6"
        icon={saveRoles.isSuccess && !dirty ? <Check size={16} /> : <Save size={16} />}
        disabled={!dirty}
        loading={saveRoles.isPending}
        onClick={() => saveRoles.mutate()}
      >
        {saveRoles.isSuccess && !dirty ? t.users.saved : t.users.save}
      </LaserButton>
    </div>
  )
}
