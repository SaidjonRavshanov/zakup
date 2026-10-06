import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useDeferredValue, useState } from 'react'
import { meQuery, userRoles, usersQuery, type User, type UserStatusFilter } from '@/entities/user'
import { useZk } from '@/shared/i18n/use-zk'
import { Empty, PageHead, Row, RowsSkeleton, SearchInput, Seg, Tag } from '@/shared/kit'

type Filter = UserStatusFilter | 'all'

const matches = (user: User, filter: Filter) => filter === 'all' || (filter === 'active' ? user.is_active : !user.is_active)

export default function UsersPage() {
  const navigate = useNavigate()
  const { z } = useZk()
  const { data: me } = useQuery(meQuery)
  const { data: users = [], isPending, error } = useQuery(usersQuery)
  const [chosen, setChosen] = useState<Filter | null>(null)
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim().toLowerCase().replace(/^@/, ''))

  // Kutayotganlar bo'lsa — avval ularni ko'rsatamiz
  const filter: Filter = chosen ?? (users.some((u) => !u.is_active) ? 'pending' : 'all')
  const visible = users.filter(
    (u) =>
      matches(u, filter) &&
      (!query || u.full_name.toLowerCase().includes(query) || (u.username ?? '').toLowerCase().includes(query)),
  )

  if (error) return <Empty title={z.not_found} hint={z.not_found_hint} />

  return (
    <div>
      <PageHead title={z.users} />
      <SearchInput className="mt-3" value={search} onChange={setSearch} placeholder={z.search_user} />
      <Seg
        className="mt-3"
        value={filter}
        onChange={setChosen}
        options={[
          { value: 'pending', label: z.f_waiting, count: users.filter((u) => matches(u, 'pending')).length },
          { value: 'active', label: z.f_activeU, count: users.filter((u) => matches(u, 'active')).length },
          { value: 'all', label: z.f_all, count: users.length },
        ]}
      />
      {isPending ? (
        <RowsSkeleton n={4} />
      ) : visible.length === 0 ? (
        <Empty title="" hint={z.no_users} />
      ) : (
        visible.map((user) => {
          const roles = userRoles(user)
          return (
            <Row
              key={user.id}
              meta={`ID ${user.telegram_id}${user.username ? ` · @${user.username}` : ''}`}
              title={user.id === me?.id ? `${user.full_name} · ${z.you}` : user.full_name}
              sub={roles.length ? roles.map((r) => z[`r_${r}`]).join(', ') : z.no_role}
              badge={user.is_active ? <Tag tone="ok">{z.usr_active}</Tag> : <Tag tone="warn">{z.usr_pending}</Tag>}
              onClick={() => navigate({ to: '/admin/users/$userId', params: { userId: user.id } })}
            />
          )
        })
      )}
    </div>
  )
}
