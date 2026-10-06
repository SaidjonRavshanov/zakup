import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Plus, X } from 'lucide-react'
import { useState } from 'react'
import { storesQuery } from '@/entities/catalog'
import { REQUESTS_KEY, requestsApi, type RequestType } from '@/entities/purchase-request'
import { meQuery } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Btn, Field, PageHead, Picker, Section, Seg, Textarea, TotalLine, toast, usePageActions } from '@/shared/kit'
import { AddProductSheet, type PickedProduct } from './AddProductSheet'
import { packInfo, parseQty, qtyBody } from './labels'

const CREATOR_ROLES = new Set(['initiator', 'buyer', 'admin'])

const isoDate = (offsetDays: number) => {
  const date = new Date()
  date.setDate(date.getDate() + offsetDays)
  return date.toLocaleDateString('sv-SE') // YYYY-MM-DD, mahalliy sana
}

type Need = '0' | '1' | '2'

interface DraftLine extends PickedProduct {
  key: number
}

export default function RequestNewPage() {
  const { z, f } = useZk()
  const { t } = useI18n()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: me } = useQuery(meQuery)
  const { data: stores = [] } = useQuery(storesQuery)

  // Faqat zayavka yaratish huquqi bor omborlar (rol omborsiz bo'lsa — hammasi)
  const grants = me?.grants.filter((g) => CREATOR_ROLES.has(g.role)) ?? []
  const allowed = grants.some((g) => g.store_id === null) ? stores : stores.filter((s) => grants.some((g) => g.store_id === s.id))

  const [storeId, setStoreId] = useState('')
  const [need, setNeed] = useState<Need>('1')
  const [type, setType] = useState<RequestType>('manual')
  const [comment, setComment] = useState('')
  const [lines, setLines] = useState<DraftLine[]>([])
  const [adding, setAdding] = useState(false)
  const [addKey, setAddKey] = useState(0)
  const store = storeId || allowed[0]?.id || ''

  const sumOf = (l: PickedProduct) => {
    if (!l.offer) return 0
    return packInfo(parseQty(l.qty), l.offer, f, l.product.base_unit).sum
  }
  const total = lines.reduce((a, l) => a + sumOf(l), 0)

  const create = useMutation({
    mutationFn: async (submit: boolean) => {
      const { id } = await requestsApi.create({
        store_id: store,
        needed_by: isoDate(Number(need)),
        type,
        comment: comment.trim() || null,
      })
      try {
        for (const l of lines) await requestsApi.addLine(id, { product_id: l.product.id, qty: qtyBody(l.qty), note: null })
        if (submit) await requestsApi.submit(id)
      } catch {
        // Zayavka yaratildi, lekin keyingi qadam o'tmadi — qoralama sahifasida davom etiladi
        return { id, submitted: false, partial: true }
      }
      return { id, submitted: submit, partial: false }
    },
    onSuccess: async ({ id, submitted, partial }) => {
      if (!partial) toast(submitted ? z.toast_submitted : z.toast_draft)
      await queryClient.invalidateQueries({ queryKey: REQUESTS_KEY })
      void navigate({ to: '/requests/$requestId', params: { requestId: id }, replace: true })
    },
  })

  usePageActions({
    primary: {
      label: z.a_create_submit,
      onClick: () => create.mutate(true),
      disabled: !store || !lines.length || lines.some((l) => !l.offer),
      loading: create.isPending && create.variables,
    },
    secondary: {
      label: z.a_save_draft,
      onClick: () => create.mutate(false),
      disabled: !store || create.isPending,
    },
  })

  const needOptions: Array<{ value: Need; label: string }> = [
    { value: '0', label: z.today_l },
    { value: '1', label: z.tomorrow_l },
    { value: '2', label: f.dt(isoDate(2)) },
  ]

  return (
    <div className="mx-auto max-w-[720px]">
      <PageHead title={z.new_req} sub={z.new_req_sub} />

      <Section className="mb-2 mt-5">{z.store}</Section>
      <Picker
        title={z.store}
        options={allowed.map((s) => ({ value: s.id, label: s.name, sub: s.branch_name }))}
        value={store}
        onChange={setStoreId}
      />

      <div className="mt-4 grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}>
        <div>
          <div className="mb-2 text-[13px] font-medium text-n7">{z.need_to}</div>
          <Seg options={needOptions} value={need} onChange={setNeed} />
        </div>
        <div>
          <div className="mb-2 text-[13px] font-medium text-n7">{z.type}</div>
          <Seg
            options={[
              { value: 'manual', label: z.rt_regular },
              { value: 'event', label: z.rt_banquet },
            ]}
            value={type === 'auto' ? 'manual' : type}
            onChange={setType}
          />
        </div>
      </div>

      <Section>{`${z.items} · ${lines.length}`}</Section>
      {lines.map((l) => {
        const pk = l.offer ? packInfo(parseQty(l.qty), l.offer, f, l.product.base_unit) : null
        return (
          <div key={l.key} className="grid grid-cols-[minmax(0,1fr)_auto_44px] items-center gap-x-2 gap-y-0.5 border-b border-line py-2.5">
            <div className="min-w-0">
              <div className="text-[16px] font-medium">{l.product.name}</div>
              <div className="text-[14px]">
                {f.qty(parseQty(l.qty), l.product.base_unit)}{' '}
                {pk?.label && (
                  <span className={pk.round ? 'text-warn' : 'text-n7'}>
                    {pk.round ? `→ ${z.will_order} ${pk.label}` : `= ${pk.label}`}
                  </span>
                )}
              </div>
              <div className={l.offer ? 'text-[13px] text-n7' : 'text-[13px] text-warn'}>
                {l.offer ? l.offer.supplier_name : z.no_sup}
              </div>
            </div>
            <div className="whitespace-nowrap text-[15px] font-medium">{pk ? f.money(pk.sum) : '—'}</div>
            <button
              type="button"
              aria-label={z.a_delete}
              onClick={() => setLines((prev) => prev.filter((x) => x.key !== l.key))}
              className="grid size-11 place-items-center text-n7"
            >
              <X size={20} />
            </button>
          </div>
        )
      })}
      {lines.length === 0 && <div className="border-b border-line py-5 text-[15px] text-n7">{z.no_items_hint}</div>}
      <Btn size="lg" block className="mt-3" icon={<Plus size={20} />} onClick={() => setAdding(true)}>
        {z.add_item}
      </Btn>
      <div className="mt-2">
        <TotalLine label={z.total} value={f.money(total)} />
      </div>

      <Field label={z.comment} className="mt-4">
        <Textarea value={comment} maxLength={500} placeholder={z.comment_ph} onChange={(e) => setComment(e.target.value)} />
      </Field>

      {create.error && <Banner tone="danger">{describeError(create.error, t)}</Banner>}

      <AddProductSheet
        key={addKey}
        open={adding}
        onClose={() => setAdding(false)}
        exclude={new Set(lines.map((l) => l.product.id))}
        onAdd={(p) => {
          setLines((prev) => [...prev, { ...p, key: Date.now() }])
          setAdding(false)
          setAddKey((k) => k + 1)
          toast(z.toast_added)
        }}
      />
    </div>
  )
}
