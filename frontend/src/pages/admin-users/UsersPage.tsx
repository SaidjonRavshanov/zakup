import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useDeferredValue, useMemo, useState } from 'react'
import { meQuery, userRoles, usersQuery, type User, type UserStatusFilter } from '@/entities/user'
import { useI18n } from '@/shared/i18n'
import { EmptyState, ListRow, PageHeader, SearchPill, SegmentedControl, Skeleton, StatusBadge } from '@/shared/ui'

type Filter = UserStatusFilter | 'all'

const matches = (user: User, filter: Filter) =>
  filter === 'all' || (filter === 'active' ? user.is_active : !user.is_active)

export default function UsersPage() {
  const navigate = useNavigate()
  const { t } = useI18n()
  const { data: me } = useQuery(meQuery)
  const { data: users = [], isPending, error } = useQuery(usersQuery)
  const [chosen, setChosen] = useState<Filter | null>(null)
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim().toLowerCase().replace(/^@/, ''))

  // Kutayotganlar bo'lsa — avval ularni ko'rsatamiz
  const filter: Filter = chosen ?? (users.some((u) => !u.is_active) ? 'pending' : 'all')

  const segments = useMemo(
    () =>
      (['pending', 'active', 'all'] as const).map((value) => ({
        value,
        label: t.users.filters[value],
        count: users.filter((u) => matches(u, value)).length,
      })),
    [users, t],
  )

  const visible = useMemo(
    () =>
      users.filter(
        (u) =>
          matches(u, filter) &&
          (!query || u.full_name.toLowerCase().includes(query) || (u.username ?? '').toLowerCase().includes(query)),
      ),
    [users, filter, query],
  )

  if (error) return <EmptyState code="403" title={t.errors.permission_denied} />

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.users.meta} title={t.users.title} />
      <SearchPill placeholder={t.users.search} value={search} onChange={(e) => setSearch(e.target.value)} />
      <SegmentedControl className="-mx-4 mt-3 px-4" segments={segments} value={filter} onChange={setChosen} />

      <div className="mt-4 flex flex-col gap-2">
        {isPending ? (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
        ) : visible.length === 0 ? (
          <EmptyState code="0" title={t.common.notFound} description={t.users.emptyHint} />
        ) : (
          visible.map((user) => {
            const roles = userRoles(user)
            return (
              <ListRow
                key={user.id}
                meta={`ID ${user.telegram_id}${user.username ? ` · @${user.username}` : ''}`}
                title={user.id === me?.id ? `${user.full_name} · ${t.users.you}` : user.full_name}
                subtitle={roles.length ? roles.map((r) => t.roles[r]).join(', ') : t.users.noRoles}
                badge={!user.is_active ? <StatusBadge tone="warning">{t.users.pending}</StatusBadge> : undefined}
                onClick={() => navigate({ to: '/admin/users/$userId', params: { userId: user.id } })}
              />
            )
          })
        )}
      </div>
    </div>
  )
}
