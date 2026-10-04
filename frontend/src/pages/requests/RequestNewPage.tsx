import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Plus } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { storesQuery } from '@/entities/catalog'
import { REQUESTS_KEY, requestsApi, type RequestType } from '@/entities/purchase-request'
import { meQuery } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { FormError, LaserButton, PageHeader, SegmentedControl, SelectField, TextField } from '@/shared/ui'

const CREATOR_ROLES = new Set(['initiator', 'buyer', 'admin'])

const isoDate = (offsetDays: number) => {
  const date = new Date()
  date.setDate(date.getDate() + offsetDays)
  return date.toLocaleDateString('sv-SE') // YYYY-MM-DD, mahalliy sana
}

export default function RequestNewPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: me } = useQuery(meQuery)
  const { data: stores = [] } = useQuery(storesQuery)

  // Faqat zayavka yaratish huquqi bor omborlar (rol omborsiz bo'lsa — hammasi)
  const grants = me?.grants.filter((g) => CREATOR_ROLES.has(g.role)) ?? []
  const allowed = grants.some((g) => g.store_id === null) ? stores : stores.filter((s) => grants.some((g) => g.store_id === s.id))

  const [storeId, setStoreId] = useState('')
  const [neededBy, setNeededBy] = useState(isoDate(1))
  const [type, setType] = useState<RequestType>('manual')
  const [comment, setComment] = useState('')
  const store = storeId || allowed[0]?.id || ''

  useEffect(() => telegram.backButton(() => navigate({ to: '/requests' })), [navigate])

  const create = useMutation({
    mutationFn: () => requestsApi.create({ store_id: store, needed_by: neededBy, type, comment: comment.trim() || null }),
    onSuccess: async ({ id }) => {
      await queryClient.invalidateQueries({ queryKey: REQUESTS_KEY })
      void navigate({ to: '/requests/$requestId', params: { requestId: id }, replace: true })
    },
  })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    create.mutate()
  }

  return (
    <form onSubmit={submit} className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.requests.meta} title={t.requests.new} />
      <div className="flex flex-col gap-4">
        <SelectField
          label={t.requests.store}
          value={store}
          options={allowed.map((s) => ({ value: s.id, label: s.branch_name ? `${s.name} · ${s.branch_name}` : s.name }))}
          onChange={(e) => setStoreId(e.target.value)}
        />
        <TextField
          label={t.requests.neededBy}
          type="date"
          required
          min={isoDate(0)}
          value={neededBy}
          onChange={(e) => setNeededBy(e.target.value)}
        />
        <SegmentedControl
          segments={(['manual', 'event'] as const).map((value) => ({ value, label: t.requestType[value] }))}
          value={type === 'auto' ? 'manual' : type}
          onChange={setType}
        />
        <TextField label={t.requests.comment} maxLength={500} value={comment} onChange={(e) => setComment(e.target.value)} />
        <FormError>{create.error && describeError(create.error, t)}</FormError>
        <LaserButton type="submit" size="lg" block icon={<Plus size={16} />} loading={create.isPending} disabled={!store}>
          {t.requests.create}
        </LaserButton>
      </div>
    </form>
  )
}
