/** Xarid kartasi (tovar × ombor) — prototipda tovar ekranida Seg rejim; bu yerda to'liq sozlamalar. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useState, type FormEvent } from 'react'
import {
  CATALOG_KEY,
  catalogApi,
  productQuery,
  storesQuery,
  type ProductDetail,
  type PurchaseCardInput,
  type PurchaseMode,
} from '@/entities/catalog'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Banner, Empty, Field, Input, PageHead, RowsSkeleton, Seg, toast, usePageActions } from '@/shared/kit'
import { Select, SuffixInput } from './form-ui'

export default function PurchaseCardPage() {
  const { productId, storeId } = useParams({ from: '/shell/catalog/products/$productId/cards/$storeId' })
  const { z } = useZk()
  const { data: product, isPending } = useQuery(productQuery(productId))
  const { data: stores } = useQuery(storesQuery)
  const store = stores?.find((s) => s.id === storeId)

  if (isPending || !stores) return <RowsSkeleton n={4} />
  if (!product || !store) return <Empty title={z.not_found} hint={z.not_found_hint} />
  return <CardForm product={product} storeId={store.id} storeName={store.name} />
}

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

function CardForm({ product, storeId, storeName }: { product: ProductDetail; storeId: string; storeName: string }) {
  const { t } = useI18n()
  const { z, f } = useZk()
  const c = t.catalog.card
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const card = product.cards.find((x) => x.store_id === storeId)
  const [form, setForm] = useState<PurchaseCardInput>({
    product_id: product.id,
    store_id: storeId,
    mode: card?.mode ?? 'manual',
    safety_stock: card ? String(Number(card.safety_stock)) : '0',
    coverage_days: card?.coverage_days ?? 7,
    shelf_life_days: card?.shelf_life_days ?? null,
    seasonal_factor: card ? String(Number(card.seasonal_factor)) : '1',
    primary_supplier_id: card?.primary_supplier_id ?? null,
    alternative_supplier_id: card?.alternative_supplier_id ?? null,
  })
  const set = <K extends keyof PurchaseCardInput>(key: K, value: PurchaseCardInput[K]) => setForm((prev) => ({ ...prev, [key]: value }))

  // Tanlov — shu tovarni taklif qilgan yetkazib beruvchilar (WORKFLOW B6)
  const suppliers = [...new Map(product.offers.filter((o) => !o.archived).map((o) => [o.supplier_id, o.supplier_name])).entries()]
  const supplierOptions = [{ value: '', label: c.none }, ...suppliers.map(([value, label]) => ({ value, label }))]

  const back = () => navigate({ to: '/catalog/products/$productId', params: { productId: product.id } })

  const save = useMutation({
    mutationFn: () => catalogApi.configureCard({ ...form, safety_stock: form.safety_stock || '0', seasonal_factor: form.seasonal_factor || '1' }),
    onSuccess: async () => {
      toast(z.toast_saved)
      await queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
      void back()
    },
  })
  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    if (!save.isPending) save.mutate()
  }

  usePageActions({ primary: { label: z.a_save, onClick: () => submit(), loading: save.isPending } })

  const unit = f.unit(product.base_unit)
  const modes: Array<{ value: PurchaseMode; label: string }> = [
    { value: 'auto', label: z.m_auto },
    { value: 'manual', label: z.m_manual },
    { value: 'disabled', label: z.m_off },
  ]

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-[720px]">
      <PageHead size={32} kicker={`${product.name} · ${storeName}`} title={c.title} />
      <div className="mt-4 flex flex-col gap-4">
        <Seg options={modes} value={form.mode} onChange={(mode) => set('mode', mode)} />
        {form.mode === 'auto' && !form.primary_supplier_id && <Banner tone="warn">{c.autoHint}</Banner>}

        <Field label={c.primary} hint={suppliers.length === 0 ? t.catalog.product.offersHint : undefined}>
          <Select
            value={form.primary_supplier_id ?? ''}
            options={supplierOptions}
            onChange={(e) => set('primary_supplier_id', e.target.value || null)}
          />
        </Field>
        <Field label={c.alternative}>
          <Select
            value={form.alternative_supplier_id ?? ''}
            options={supplierOptions.filter((o) => !o.value || o.value !== form.primary_supplier_id)}
            disabled={!form.primary_supplier_id}
            onChange={(e) => set('alternative_supplier_id', e.target.value || null)}
          />
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label={c.safetyStock}>
            <SuffixInput inputMode="decimal" suffix={unit} value={form.safety_stock} onChange={(e) => set('safety_stock', decimal(e.target.value))} />
          </Field>
          <Field label={c.coverage}>
            <SuffixInput
              type="number"
              min={1}
              max={90}
              suffix={z.days_s}
              value={form.coverage_days}
              onChange={(e) => set('coverage_days', Number(e.target.value))}
            />
          </Field>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Field label={c.shelfLife}>
            <SuffixInput
              type="number"
              min={1}
              suffix={z.days_s}
              value={form.shelf_life_days ?? ''}
              onChange={(e) => set('shelf_life_days', e.target.value ? Number(e.target.value) : null)}
            />
          </Field>
          <Field label={c.seasonal}>
            <Input inputMode="decimal" value={form.seasonal_factor} onChange={(e) => set('seasonal_factor', decimal(e.target.value))} />
          </Field>
        </div>
        <div className="-mt-2 text-[13px] text-n7">{c.shelfLifeHint}</div>

        {save.error && <Banner tone="danger">{describeError(save.error, t)}</Banner>}
      </div>
    </form>
  )
}
