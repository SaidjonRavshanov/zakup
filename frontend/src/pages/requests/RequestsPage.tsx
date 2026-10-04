import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useMemo, useState } from 'react'
import { REQUEST_FILTERS, REQUEST_STATUS_TONE, requestsQuery, type RequestFilter } from '@/entities/purchase-request'
import { useHasRole } from '@/entities/user'
import { AutoRequestsButton } from '@/features/auto-requests'
import { useI18n } from '@/shared/i18n'
import { EmptyState, LaserButton, ListRow, MoneyText, PageHeader, SegmentedControl, Skeleton, StatusBadge } from '@/shared/ui'

const FILTERS = Object.keys(REQUEST_FILTERS) as RequestFilter[]

export default function RequestsPage() {
  const { t, fmt } = useI18n()
  const navigate = useNavigate()
  const canCreate = useHasRole('initiator', 'buyer', 'admin')
  const isDecider = useHasRole('buyer', 'approver', 'admin')
  const canRunAuto = useHasRole('buyer', 'admin')
  const { data: requests = [], isPending } = useQuery(requestsQuery)
  const [chosen, setChosen] = useState<RequestFilter | null>(null)
  // Tasdiqlovchiga — avval kutayotganlar
  const filter: RequestFilter = chosen ?? (isDecider && requests.some((r) => r.status === 'PENDING_APPROVAL') ? 'pending' : 'active')

  const segments = useMemo(
    () =>
      FILTERS.map((value) => {
        const statuses = REQUEST_FILTERS[value]
        return {
          value,
          label: t.requests.filters[value],
          count: statuses ? requests.filter((r) => statuses.includes(r.status)).length : requests.length,
        }
      }),
    [requests, t],
  )
  const statuses = REQUEST_FILTERS[filter]
  const visible = statuses ? requests.filter((r) => statuses.includes(r.status)) : requests

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader
        meta={t.requests.meta}
        title={t.requests.title}
        action={
          canCreate ? (
            <LaserButton icon={<Plus size={16} />} onClick={() => navigate({ to: '/requests/new' })}>
              {t.requests.new}
            </LaserButton>
          ) : undefined
        }
      />
      {canRunAuto && <AutoRequestsButton />}
      <SegmentedControl className="-mx-4 px-4" segments={segments} value={filter} onChange={setChosen} />
      <div className="mt-4 flex flex-col gap-2">
        {isPending ? (
          Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[76px]" />)
        ) : visible.length === 0 ? (
          <EmptyState code="0" title={t.common.notFound} description={t.requests.emptyHint} />
        ) : (
          visible.map((request) => (
            <ListRow
              key={request.id}
              meta={`${request.number} · ${request.store_name ?? '—'} · ${fmt.date(request.needed_by)}`}
              title={`${t.requestType[request.type]} · ${t.requests.positions(request.lines_count)}`}
              badge={<StatusBadge tone={REQUEST_STATUS_TONE[request.status]}>{t.requestStatus[request.status]}</StatusBadge>}
              trailing={<MoneyText value={Number(request.total)} className="text-[13px]" />}
              onClick={() => navigate({ to: '/requests/$requestId', params: { requestId: request.id } })}
            />
          ))
        )}
      </div>
    </div>
  )
}
