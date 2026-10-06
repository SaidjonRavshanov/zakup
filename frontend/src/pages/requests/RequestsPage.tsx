import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { REQUEST_FILTERS, requestsQuery, type RequestFilter } from '@/entities/purchase-request'
import { useHasRole } from '@/entities/user'
import { AutoRequestsButton } from '@/features/auto-requests'
import { useZk } from '@/shared/i18n/use-zk'
import { Btn, Empty, PageHead, Row, RowsSkeleton, Seg, Tag, status } from '@/shared/kit'
import { typeLabel } from './labels'

const FILTERS = Object.keys(REQUEST_FILTERS) as RequestFilter[]

export default function RequestsPage() {
  const { z, f } = useZk()
  const navigate = useNavigate()
  const canCreate = useHasRole('initiator', 'buyer', 'admin')
  const isDecider = useHasRole('buyer', 'approver', 'admin')
  const canRunAuto = useHasRole('buyer', 'admin')
  const { data: requests = [], isPending } = useQuery(requestsQuery)
  const [chosen, setChosen] = useState<RequestFilter | null>(null)
  // Tasdiqlovchiga — avval kutayotganlar
  const filter: RequestFilter = chosen ?? (isDecider && requests.some((r) => r.status === 'PENDING_APPROVAL') ? 'pending' : 'active')

  const label: Record<RequestFilter, string> = { active: z.f_active, pending: z.f_pending, done: z.f_done, all: z.f_all }
  const options = FILTERS.map((value) => {
    const statuses = REQUEST_FILTERS[value]
    return {
      value,
      label: label[value],
      count: statuses ? requests.filter((r) => statuses.includes(r.status)).length : requests.length,
    }
  })
  const statuses = REQUEST_FILTERS[filter]
  const visible = statuses ? requests.filter((r) => statuses.includes(r.status)) : requests

  return (
    <div className="mx-auto max-w-[1040px]">
      <PageHead
        title={z.requests}
        aside={
          canCreate && (
            <Btn variant="primary" icon={<Plus size={20} />} onClick={() => navigate({ to: '/requests/new' })}>
              {z.new_req_short}
            </Btn>
          )
        }
      />
      {canRunAuto && <AutoRequestsButton />}
      <Seg scroll className="mt-4" options={options} value={filter} onChange={setChosen} />
      {isPending ? (
        <RowsSkeleton n={5} />
      ) : visible.length === 0 ? (
        <Empty title={z.empty_reqs} hint={z.empty_reqs_hint} />
      ) : (
        visible.map((request) => {
          const s = status(z, 'request', request.status)
          return (
            <Row
              key={request.id}
              meta={`${request.number} · ${request.store_name ?? '—'}`}
              title={`${typeLabel(z, request.type)} · ${request.lines_count} ${z.pos_short}`}
              sub={`${z.need_to} ${f.dt(request.needed_by)}`}
              amount={f.money(request.total)}
              badge={<Tag tone={s.tone}>{s.label}</Tag>}
              onClick={() => navigate({ to: '/requests/$requestId', params: { requestId: request.id } })}
            />
          )
        })
      )}
    </div>
  )
}
