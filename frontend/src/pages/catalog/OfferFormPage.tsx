import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Archive, Save } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import {
  CATALOG_KEY,
  PACK_UNITS,
  catalogApi,
  priceHistoryQuery,
  productsQuery,
  supplierQuery,
  type Offer,
  type OfferInput,
} from '@/entities/catalog'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import { telegram } from '@/shared/lib/telegram'
import { EmptyState, FormError, LaserButton, ListRow, MoneyText, MonoLabel, PageHeader, SelectField, Skeleton, TextField } from '@/shared/ui'

/** /catalog/suppliers/$supplierId/offers/new va /catalog/suppliers/$supplierId/offers/$offerId */
export default function OfferFormPage() {
  const { supplierId, offerId } = useParams({ strict: false })
  const { data: supplier, isPending } = useQuery(supplierQuery(supplierId!))

  if (isPending) return <Skeleton className="mt-20 h-[300px]" />
  const offer = supplier?.offers.find((o) => o.id === offerId)
  if (!supplier || (offerId && !offer)) return <EmptyState code="404" title="404" />
  return <OfferForm supplierId={supplier.id} supplierName={supplier.name} offer={offer} />
}

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

function OfferForm({ supplierId, supplierName, offer }: { supplierId: string; supplierName: string; offer?: Offer }) {
  const { t, fmt } = useI18n()
  const o = t.catalog.offer
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data: products = [] } = useQuery({ ...productsQuery(), enabled: !offer })
  const { data: history = [] } = useQuery({ ...priceHistoryQuery(offer?.id ?? ''), enabled: Boolean(offer) })

  const [productId, setProductId] = useState('')
  const [validFrom, setValidFrom] = useState('')
  const [form, setForm] = useState<OfferInput>({
    pack_unit: offer?.pack_unit ?? 'bag',
    pack_factor: offer ? String(Number(offer.pack_factor)) : '',
    order_multiple: offer ? String(Number(offer.order_multiple)) : '1',
    supplier_sku: offer?.supplier_sku ?? '',
    supplier_product_name: offer?.supplier_product_name ?? '',
    price: offer ? String(Number(offer.price)) : '',
  })
  const set = <K extends keyof OfferInput>(key: K, value: OfferInput[K]) => setForm((f) => ({ ...f, [key]: value }))

  const baseUnit: UnitCode = offer?.base_unit ?? products.find((p) => p.id === productId)?.base_unit ?? 'kg'
  const back = () => navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId } })
  useEffect(() => telegram.backButton(back))

  const done = async () => {
    telegram.haptic.notify('success')
    await queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
    void back()
  }
  const save = useMutation({
    mutationFn: async () => {
      const body = {
        ...form,
        supplier_sku: form.supplier_sku?.trim() || null,
        supplier_product_name: form.supplier_product_name?.trim() || null,
      }
      if (offer) await catalogApi.updateOffer(offer.id, { ...body, price_valid_from: validFrom || null })
      else await catalogApi.addOffer(supplierId, { ...body, product_id: productId })
    },
    onSuccess: done,
  })
  const archive = useMutation({ mutationFn: () => catalogApi.archiveOffer(offer!.id), onSuccess: done })

  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }
  const ready = (offer || productId) && Number(form.pack_factor) > 0 && form.price !== ''
  const failure = save.error ?? archive.error

  return (
    <form onSubmit={submit} className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={supplierName} title={offer ? o.edit : o.new} />
      <div className="flex flex-col gap-4">
        {offer ? (
          <ListRow meta={o.product} title={offer.product_name} subtitle={t.units[offer.base_unit]} />
        ) : (
          <SelectField
            label={o.product}
            required
            value={productId}
            options={[{ value: '', label: o.pickProduct }, ...products.map((p) => ({ value: p.id, label: `${p.name} · ${t.units[p.base_unit]}` }))]}
            onChange={(e) => setProductId(e.target.value)}
          />
        )}

        <div className="grid grid-cols-2 gap-3">
          <SelectField
            label={o.packUnit}
            value={form.pack_unit}
            options={PACK_UNITS.map((unit) => ({ value: unit, label: t.units[unit] }))}
            onChange={(e) => set('pack_unit', e.target.value as UnitCode)}
          />
          <TextField
            label={o.packFactor}
            inputMode="decimal"
            required
            suffix={t.units[baseUnit]}
            value={form.pack_factor}
            onChange={(e) => set('pack_factor', decimal(e.target.value))}
          />
        </div>
        <p className="-mt-2 px-2 text-[12px] text-text-3">{o.packFactorHint(t.units[baseUnit])}</p>
        <TextField
          label={o.multiple}
          hint={o.multipleHint}
          inputMode="decimal"
          value={form.order_multiple}
          onChange={(e) => set('order_multiple', decimal(e.target.value))}
        />
        <div className="grid grid-cols-2 gap-3">
          <TextField label={o.sku} maxLength={100} value={form.supplier_sku ?? ''} onChange={(e) => set('supplier_sku', e.target.value)} />
          <TextField
            label={o.supplierName}
            maxLength={300}
            value={form.supplier_product_name ?? ''}
            onChange={(e) => set('supplier_product_name', e.target.value)}
          />
        </div>
        <TextField
          label={o.price}
          inputMode="decimal"
          required
          suffix={t.common.currency}
          value={form.price}
          hint={
            Number(form.pack_factor) > 0 && form.price
              ? `${fmt.money(Number(form.price) / Number(form.pack_factor))} ${t.common.currency} / ${t.units[baseUnit]}`
              : undefined
          }
          onChange={(e) => set('price', decimal(e.target.value))}
        />
        {offer && (
          <TextField label={o.validFrom} hint={o.validFromHint} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
        )}

        <FormError>{failure && describeError(failure, t)}</FormError>
        <LaserButton type="submit" size="lg" block icon={<Save size={16} />} loading={save.isPending} disabled={!ready}>
          {t.catalog.save}
        </LaserButton>
        {offer && !offer.archived && (
          <LaserButton type="button" variant="danger" block icon={<Archive size={14} />} loading={archive.isPending} onClick={() => archive.mutate()}>
            {t.catalog.archive}
          </LaserButton>
        )}

        {history.length > 0 && (
          <section className="mt-4">
            <MonoLabel className="mb-3">{o.history}</MonoLabel>
            <div className="rounded-card border border-border-soft bg-surface px-4">
              {history.map((entry, i) => (
                <div key={i} className="flex items-baseline justify-between gap-4 border-b border-border-soft py-2.5 last:border-0">
                  <span className="text-[13px] text-text-2">
                    {fmt.date(entry.valid_from)} · {t.priceSource[entry.source]}
                  </span>
                  <MoneyText value={Number(entry.price)} />
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </form>
  )
}
