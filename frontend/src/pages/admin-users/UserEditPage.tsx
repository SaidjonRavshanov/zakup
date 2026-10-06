import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { useState } from 'react'
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
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Btn, Empty, RowsSkeleton, Section, Switch, Tag, toast, usePageActions } from '@/shared/kit'
import { telegram } from '@/shared/lib/telegram'

export default function UserEditPage() {
  const { userId } = useParams({ from: '/shell/admin/users/$userId' })
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const { z } = useZk()
  const { data: me } = useQuery(meQuery)
  const { data: users, isPending } = useQuery(usersQuery)
  const user = users?.find((u) => u.id === userId)
  const isSelf = user?.id === me?.id

  // Tahrir qoralamasi; null — serverdagi holat
  const [draft, setDraft] = useState<Set<Role> | null>(null)
  const selected = draft ?? new Set(user ? userRoles(user) : [])

  const refresh = () => queryClient.invalidateQueries({ queryKey: usersQuery.queryKey })
  const toggleActive = useMutation({
    mutationFn: () => (user!.is_active ? deactivateUser(user!.id) : activateUser(user!.id)),
    onSuccess: async () => {
      toast(user!.is_active ? z.toast_deact : z.toast_act)
      await refresh()
    },
  })
  const saveRoles = useMutation({
    // Hozircha rollar barcha omborlarga; ombor bo'yicha cheklangan mavjud rollar saqlanib qoladi
    mutationFn: () =>
      setUserRoles(user!.id, [
        ...[...selected].map((role) => ({ role, store_id: null })),
        ...user!.grants.filter((grant) => grant.store_id !== null),
      ]),
    onSuccess: async () => {
      toast(z.toast_saved)
      await refresh()
      setDraft(null)
    },
  })

  const dirty = !!user && userRoles(user).join() !== ROLES.filter((r) => selected.has(r)).join()
  usePageActions({
    primary: user ? { label: z.a_save, onClick: () => saveRoles.mutate(), disabled: !dirty, loading: saveRoles.isPending } : null,
  })

  if (isPending) return <RowsSkeleton n={5} />
  if (!user) return <Empty title={z.not_found} hint={z.not_found_hint} />

  const failure = toggleActive.error ?? saveRoles.error

  return (
    <div>
      <div className="flex items-start justify-between gap-3 pt-2">
        <div className="min-w-0">
          <div className="text-[14px] text-n7">
            ID {user.telegram_id}
            {user.username ? ` · @${user.username}` : ''}
          </div>
          <h1 className="m-0 text-[32px]">{user.full_name}</h1>
        </div>
        <Tag tone={user.is_active ? 'ok' : 'warn'} className="mt-1.5 text-[13px]">
          {user.is_active ? z.usr_active : z.usr_pending}
        </Tag>
      </div>

      {!isSelf && (
        <Btn
          size="lg"
          block
          className="mt-4"
          loading={toggleActive.isPending}
          style={{ color: user.is_active ? 'var(--zk-danger)' : 'var(--color-accent-700)' }}
          onClick={() => toggleActive.mutate()}
        >
          {user.is_active ? z.a_deactivate : z.a_activate}
        </Btn>
      )}

      {failure && <Banner tone="danger">{describeError(failure, t)}</Banner>}

      <Section>
        {z.roles} · {z.all_stores}
      </Section>
      {ROLES.map((role) => {
        const on = selected.has(role)
        const locked = isSelf && role === 'admin' // o'zidan admin'ni olib bo'lmaydi (backend ham tekshiradi)
        return (
          <button
            key={role}
            type="button"
            aria-pressed={on}
            disabled={locked}
            onClick={() => {
              telegram.haptic.select()
              const next = new Set(selected)
              if (on) next.delete(role)
              else next.add(role)
              setDraft(next)
            }}
            className="flex min-h-[60px] w-full items-center gap-3 border-b border-line py-2 text-left text-ink"
            style={{ opacity: locked ? 0.5 : 1 }}
          >
            <div className="min-w-0 flex-1">
              <div className="text-[16px] font-medium">{z[`r_${role}`]}</div>
              <div className="text-[13px] text-n7">{z[`rd_${role}`]}</div>
            </div>
            <Switch on={on} />
          </button>
        )
      })}
      <div className="mt-2.5 text-[13px] text-n7">{z.scope_note}</div>
    </div>
  )
}
