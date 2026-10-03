import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import {
  CATALOG_KEY,
  PURCHASE_MODES,
  catalogApi,
  productQuery,
  storesQuery,
  type ProductDetail,
  type PurchaseCardInput,
  type PurchaseMode,
} from '@/entities/catalog'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { EmptyState, FormError, LaserButton, PageHeader, SegmentedControl, SelectField, Skeleton, TextField } from '@/shared/ui'

export default function PurchaseCardPage() {
  const { productId, storeId } = useParams({ from: '/shell/catalog/products/$productId/cards/$storeId' })
  const { data: product, isPending } = useQuery(productQuery(productId))
  const { data: stores } = useQuery(storesQuery)
  const store = stores?.find((s) => s.id === storeId)

  if (isPending || !stores) return <Skeleton className="mt-20 h-[300px]" />
  if (!product || !store) return <EmptyState code="404" title="404" />
  return <CardForm product={product} storeId={store.id} storeName={store.name} />
}

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

function CardForm({ product, storeId, storeName }: { product: ProductDetail; storeId: string; storeName: string }) {
  const { t } = useI18n()
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
  const set = <K extends keyof PurchaseCardInput>(key: K, value: PurchaseCardInput[K]) => setForm((f) => ({ ...f, [key]: value }))

  // Tanlov — shu tovarni taklif qilgan yetkazib beruvchilar (WORKFLOW B6)
  const suppliers = [...new Map(product.offers.filter((o) => !o.archived).map((o) => [o.supplier_id, o.supplier_name])).entries()]
  const supplierOptions = [{ value: '', label: c.none }, ...suppliers.map(([value, label]) => ({ value, label }))]

  const back = () => navigate({ to: '/catalog/products/$productId', params: { productId: product.id } })
  useEffect(() => telegram.backButton(back))

  const save = useMutation({
    mutationFn: () => catalogApi.configureCard({ ...form, safety_stock: form.safety_stock || '0', seasonal_factor: form.seasonal_factor || '1' }),
    onSuccess: async () => {
      telegram.haptic.notify('success')
      await queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
      void back()
    },
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }
  const unit = t.units[product.base_unit]

  return (
    <form onSubmit={submit} className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={`${product.name} · ${storeName}`} title={c.title} />
      <div className="flex flex-col gap-4">
        <SegmentedControl
          segments={PURCHASE_MODES.map((value) => ({ value, label: t.purchaseMode[value] }))}
          value={form.mode}
          onChange={(mode: PurchaseMode) => set('mode', mode)}
        />
        {form.mode === 'auto' && !form.primary_supplier_id && <p className="px-2 text-[12px] text-warning">{c.autoHint}</p>}

        <SelectField
          label={c.primary}
          value={form.primary_supplier_id ?? ''}
          options={supplierOptions}
          hint={suppliers.length === 0 ? t.catalog.product.offersHint : undefined}
          onChange={(e) => set('primary_supplier_id', e.target.value || null)}
        />
        <SelectField
          label={c.alternative}
          value={form.alternative_supplier_id ?? ''}
          options={supplierOptions.filter((o) => !o.value || o.value !== form.primary_supplier_id)}
          disabled={!form.primary_supplier_id}
          onChange={(e) => set('alternative_supplier_id', e.target.value || null)}
        />

        <div className="grid grid-cols-2 gap-3">
          <TextField
            label={c.safetyStock}
            inputMode="decimal"
            suffix={unit}
            value={form.safety_stock}
            onChange={(e) => set('safety_stock', decimal(e.target.value))}
          />
          <TextField
            label={c.coverage}
            type="number"
            min={1}
            max={90}
            value={form.coverage_days}
            onChange={(e) => set('coverage_days', Number(e.target.value))}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <TextField
            label={c.shelfLife}
            type="number"
            min={1}
            value={form.shelf_life_days ?? ''}
            onChange={(e) => set('shelf_life_days', e.target.value ? Number(e.target.value) : null)}
          />
          <TextField
            label={c.seasonal}
            inputMode="decimal"
            value={form.seasonal_factor}
            onChange={(e) => set('seasonal_factor', decimal(e.target.value))}
          />
        </div>
        <p className="-mt-2 px-2 text-[12px] text-text-3">{c.shelfLifeHint}</p>

        <FormError>{save.error && describeError(save.error, t)}</FormError>
        <LaserButton type="submit" size="lg" block icon={<Save size={16} />} loading={save.isPending}>
          {t.catalog.save}
        </LaserButton>
      </div>
    </form>
  )
}
