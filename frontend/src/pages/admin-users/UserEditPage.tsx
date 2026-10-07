import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from '@tanstack/react-router'
import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { storesQuery } from '@/entities/catalog'
import {
  ROLES,
  activateUser,
  deactivateUser,
  meQuery,
  setUserRoles,
  usersQuery,
  type Grant,
  type Role,
} from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Btn, Check, Empty, RowsSkeleton, SearchInput, Section, Sheet, Switch, Tag, toast, usePageActions } from '@/shared/kit'
import { telegram } from '@/shared/lib/telegram'
import { L } from './i18n'

/** Rol → omborlar: 'all' — barchasi (store_id null), aks holda tanlangan omborlar. */
type Scope = Map<Role, 'all' | string[]>

function scopeOf(grants: Grant[]): Scope {
  const scope: Scope = new Map()
  for (const grant of grants) {
    const current = scope.get(grant.role)
    if (grant.store_id === null || current === 'all') scope.set(grant.role, 'all')
    else scope.set(grant.role, [...(current ?? []), grant.store_id])
  }
  return scope
}

function grantsOf(scope: Scope): Grant[] {
  return ROLES.flatMap((role): Grant[] => {
    const s = scope.get(role)
    if (s === undefined) return []
    return s === 'all' ? [{ role, store_id: null }] : s.map((store_id) => ({ role, store_id }))
  })
}

const keyOf = (scope: Scope) =>
  grantsOf(scope)
    .map((g) => `${g.role}:${g.store_id ?? '*'}`)
    .sort()
    .join()

export default function UserEditPage() {
  const { userId } = useParams({ from: '/shell/admin/users/$userId' })
  const queryClient = useQueryClient()
  const { t } = useI18n()
  const { z, locale } = useZk()
  const l = L[locale]
  const { data: me } = useQuery(meQuery)
  const { data: users, isPending } = useQuery(usersQuery)
  const { data: stores = [] } = useQuery(storesQuery)
  const user = users?.find((u) => u.id === userId)
  const isSelf = user?.id === me?.id

  // Tahrir qoralamasi; null — serverdagi holat
  const [draft, setDraft] = useState<Scope | null>(null)
  const [picking, setPicking] = useState<Role | null>(null)
  const scope = draft ?? scopeOf(user?.grants ?? [])

  const refresh = () => queryClient.invalidateQueries({ queryKey: usersQuery.queryKey })
  const toggleActive = useMutation({
    mutationFn: () => (user!.is_active ? deactivateUser(user!.id) : activateUser(user!.id)),
    onSuccess: async () => {
      toast(user!.is_active ? z.toast_deact : z.toast_act)
      await refresh()
    },
  })
  const saveRoles = useMutation({
    mutationFn: () => setUserRoles(user!.id, grantsOf(scope)),
    onSuccess: async () => {
      toast(z.toast_saved)
      await refresh()
      setDraft(null)
    },
  })

  const update = (role: Role, value: 'all' | string[] | undefined) => {
    const next: Scope = new Map(scope)
    if (value === undefined) next.delete(role)
    else next.set(role, value)
    setDraft(next)
  }

  const dirty = !!user && keyOf(scope) !== keyOf(scopeOf(user.grants))
  // Ombori tanlanmagan rol saqlanmaydi (backend'da grant bo'lmaydi)
  const incomplete = [...scope.values()].some((s) => s !== 'all' && s.length === 0)
  usePageActions({
    primary: user
      ? { label: z.a_save, onClick: () => saveRoles.mutate(), disabled: !dirty || incomplete, loading: saveRoles.isPending }
      : null,
  })

  if (isPending) return <RowsSkeleton n={5} />
  if (!user) return <Empty title={z.not_found} hint={z.not_found_hint} />

  const failure = toggleActive.error ?? saveRoles.error
  const storeName = (id: string) => stores.find((s) => s.id === id)?.name ?? '…'
  const describe = (s: 'all' | string[]) =>
    s === 'all' ? z.all_stores : s.length === 0 ? '—' : s.length <= 2 ? s.map(storeName).join(', ') : l.storesN(s.length)

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
      {incomplete && <Banner tone="warn">{l.noneHint}</Banner>}

      <Section>{z.roles}</Section>
      {ROLES.map((role) => {
        const s = scope.get(role)
        const on = s !== undefined
        const locked = isSelf && role === 'admin' // o'zidan admin'ni olib bo'lmaydi (backend ham tekshiradi)
        return (
          <div key={role} className="border-b border-line">
            <button
              type="button"
              aria-pressed={on}
              disabled={locked}
              onClick={() => {
                telegram.haptic.select()
                update(role, on ? undefined : 'all')
              }}
              className="flex min-h-[60px] w-full items-center gap-3 py-2 text-left text-ink"
              style={{ opacity: locked ? 0.5 : 1 }}
            >
              <div className="min-w-0 flex-1">
                <div className="text-[16px] font-medium">{z[`r_${role}`]}</div>
                <div className="text-[13px] text-n7">{z[`rd_${role}`]}</div>
              </div>
              <Switch on={on} />
            </button>
            {on &&
              (role === 'admin' ? (
                <div className="pb-2.5 text-[13px] text-n7">{l.adminAll}</div>
              ) : (
                <button
                  type="button"
                  onClick={() => setPicking(role)}
                  className="zk-hover -mt-1 mb-2 flex min-h-11 w-full items-center gap-2 border border-line px-3 text-left text-[14px] text-ink"
                >
                  <span className="text-n7">{l.stores}:</span>
                  <span className="min-w-0 flex-1 truncate font-medium" style={{ color: s.length === 0 ? 'var(--zk-danger)' : undefined }}>
                    {describe(s)}
                  </span>
                  <ChevronRight size={20} />
                </button>
              ))}
          </div>
        )
      })}
      <div className="mt-2.5 text-[13px] text-n7">{l.scopeNote}</div>

      {picking && (
        <StoresSheet
          title={`${l.pickStores} · ${z[`r_${picking}`]}`}
          value={scope.get(picking) ?? 'all'}
          stores={stores.map((s) => ({ id: s.id, name: s.name, sub: s.branch_name }))}
          allLabel={z.all_stores}
          doneLabel={l.done}
          onChange={(value) => update(picking, value)}
          onClose={() => setPicking(null)}
        />
      )}
    </div>
  )
}

function StoresSheet({
  title,
  value,
  stores,
  allLabel,
  doneLabel,
  onChange,
  onClose,
}: {
  title: string
  value: 'all' | string[]
  stores: Array<{ id: string; name: string; sub: string | null }>
  allLabel: string
  doneLabel: string
  onChange: (value: 'all' | string[]) => void
  onClose: () => void
}) {
  const [q, setQ] = useState('')
  const query = q.trim().toLowerCase()
  const picked = value === 'all' ? [] : value
  const visible = query ? stores.filter((s) => `${s.name} ${s.sub ?? ''}`.toLowerCase().includes(query)) : stores
  // Tanlanganlar — tepada (ko'p ombor bo'lsa topish oson)
  const ordered = [...visible.filter((s) => picked.includes(s.id)), ...visible.filter((s) => !picked.includes(s.id))]

  const toggle = (id: string) => onChange(picked.includes(id) ? picked.filter((x) => x !== id) : [...picked, id])

  return (
    <Sheet open title={title} onClose={onClose}>
      <div className="flex min-h-[52px] items-center gap-1 border-b border-line">
        <Check on={value === 'all'} onToggle={() => onChange(value === 'all' ? [] : 'all')} label={allLabel} />
        <button
          type="button"
          onClick={() => onChange(value === 'all' ? [] : 'all')}
          className="min-w-0 flex-1 py-3 text-left text-[16px] font-medium text-ink"
        >
          {allLabel}
        </button>
      </div>
      {value !== 'all' && (
        <>
          <SearchInput className="mt-3" value={q} onChange={setQ} />
          <div className="mt-1">
            {ordered.map((s) => (
              <div key={s.id} className="flex min-h-[52px] items-center gap-1 border-b border-line">
                <Check on={picked.includes(s.id)} onToggle={() => toggle(s.id)} label={s.name} />
                <button type="button" onClick={() => toggle(s.id)} className="min-w-0 flex-1 py-2 text-left text-ink">
                  <div className="text-[16px]">{s.name}</div>
                  {s.sub && <div className="text-[13px] text-n7">{s.sub}</div>}
                </button>
              </div>
            ))}
          </div>
        </>
      )}
      <Btn variant="primary" size="lg" block className="mt-4" onClick={onClose}>
        {doneLabel}
      </Btn>
    </Sheet>
  )
}
