/** /catalog/suppliers/$supplierId/offers/new va .../offers/$offerId — prototipda ekran yo'q, kit Field/Input/Chips bilan. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useDeferredValue, useState, type FormEvent } from 'react'
import {
  CATALOG_KEY,
  PACK_UNITS,
  catalogApi,
  priceHistoryQuery,
  productsQuery,
  supplierQuery,
  type Offer,
  type OfferInput,
  type ProductListItem,
} from '@/entities/catalog'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import type { UnitCode } from '@/shared/i18n/keys'
import { Banner, Chips, Empty, Field, Input, KV, PageHead, RowsSkeleton, SearchInput, Section, confirmAction, toast, usePageActions } from '@/shared/kit'
import { Select, SuffixInput } from './form-ui'

export default function OfferFormPage() {
  const { supplierId, offerId } = useParams({ strict: false })
  const { z } = useZk()
  const { data: supplier, isPending } = useQuery(supplierQuery(supplierId!))

  if (isPending) return <RowsSkeleton n={4} />
  const offer = supplier?.offers.find((o) => o.id === offerId)
  if (!supplier || (offerId && !offer)) return <Empty title={z.not_found} hint={z.not_found_hint} />
  return <OfferForm supplierId={supplier.id} supplierName={supplier.name} offer={offer} />
}

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

function OfferForm({ supplierId, supplierName, offer }: { supplierId: string; supplierName: string; offer?: Offer }) {
  const { t } = useI18n()
  const { z, f } = useZk()
  const o = t.catalog.offer
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  // Mahsulot qidiruvi — serverda (katalog 200 tadan ko'p bo'lishi mumkin)
  const [search, setSearch] = useState('')
  const query = useDeferredValue(search.trim())
  const { data: found = [] } = useQuery({ ...productsQuery(query), enabled: !offer })
  const { data: history = [] } = useQuery({ ...priceHistoryQuery(offer?.id ?? ''), enabled: Boolean(offer) })

  const [picked, setPicked] = useState<ProductListItem | null>(null)
  const productId = picked?.id ?? ''
  // Tanlangan mahsulot yangi qidiruv natijasida bo'lmasa ham ro'yxatda qoladi
  const products = picked && !found.some((p) => p.id === picked.id) ? [picked, ...found] : found
  const [validFrom, setValidFrom] = useState('')
  const [form, setForm] = useState<OfferInput>({
    pack_unit: offer?.pack_unit ?? 'bag',
    pack_factor: offer ? String(Number(offer.pack_factor)) : '',
    order_multiple: offer ? String(Number(offer.order_multiple)) : '1',
    supplier_sku: offer?.supplier_sku ?? '',
    supplier_product_name: offer?.supplier_product_name ?? '',
    price: offer ? String(Number(offer.price)) : '',
  })
  const set = <K extends keyof OfferInput>(key: K, value: OfferInput[K]) => setForm((prev) => ({ ...prev, [key]: value }))

  const baseUnit: UnitCode = offer?.base_unit ?? products.find((p) => p.id === productId)?.base_unit ?? 'kg'
  const back = () => navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId } })

  const done = async () => {
    toast(z.toast_saved)
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

  const ready = Boolean(offer || productId) && Number(form.pack_factor) > 0 && form.price !== ''
  const submit = (event?: FormEvent) => {
    event?.preventDefault()
    if (ready && !save.isPending) save.mutate()
  }
  const askArchive = async () => {
    if (await confirmAction({ title: `${t.catalog.archive}?`, body: offer?.product_name, label: t.catalog.archive, cancel: z.cancel, danger: true }))
      archive.mutate()
  }
  const failure = save.error ?? archive.error
  const unitPrice = Number(form.pack_factor) > 0 && form.price ? Number(form.price) / Number(form.pack_factor) : null

  usePageActions({
    primary: { label: z.a_save, onClick: () => submit(), disabled: !ready, loading: save.isPending },
    secondary: offer && !offer.archived ? { label: t.catalog.archive, danger: true, onClick: () => void askArchive() } : null,
  })

  return (
    <form onSubmit={submit} className="mx-auto w-full max-w-[720px]">
      <PageHead kicker={supplierName} title={offer ? o.edit : o.new} />
      <div className="mt-4 flex flex-col gap-4">
        {offer ? (
          <KV rows={[[o.product, `${offer.product_name} · ${f.unit(offer.base_unit)}`]]} />
        ) : (
          <>
            {/* Qidiruvdagi Enter formani yubormasin */}
            <div onKeyDown={(e) => e.key === 'Enter' && e.preventDefault()}>
              <SearchInput value={search} onChange={setSearch} placeholder={z.search_prod} />
            </div>
            <Field label={o.product}>
              <Select
                required
                value={productId}
                options={[{ value: '', label: o.pickProduct }, ...products.map((p) => ({ value: p.id, label: `${p.name} · ${f.unit(p.base_unit)}` }))]}
                onChange={(e) => setPicked(products.find((p) => p.id === e.target.value) ?? null)}
              />
            </Field>
          </>
        )}

        <Field label={o.packUnit}>
          <Chips
            options={PACK_UNITS.map((unit) => ({ value: unit, label: f.pack(unit) }))}
            value={form.pack_unit}
            onChange={(unit: UnitCode) => set('pack_unit', unit)}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label={o.packFactor}>
            <SuffixInput
              inputMode="decimal"
              required
              suffix={f.unit(baseUnit)}
              value={form.pack_factor}
              onChange={(e) => set('pack_factor', decimal(e.target.value))}
            />
          </Field>
          <Field label={o.multiple}>
            <Input inputMode="decimal" value={form.order_multiple} onChange={(e) => set('order_multiple', decimal(e.target.value))} />
          </Field>
        </div>
        <div className="-mt-2 text-[13px] text-n7">{`${o.packFactorHint(f.unit(baseUnit))}. ${o.multipleHint}`}</div>
        <div className="grid grid-cols-2 gap-3">
          <Field label={o.sku}>
            <Input maxLength={100} value={form.supplier_sku ?? ''} onChange={(e) => set('supplier_sku', e.target.value)} />
          </Field>
          <Field label={o.supplierName}>
            <Input maxLength={300} value={form.supplier_product_name ?? ''} onChange={(e) => set('supplier_product_name', e.target.value)} />
          </Field>
        </div>
        <Field label={o.price} hint={unitPrice !== null ? `${f.money(unitPrice)} / ${f.unit(baseUnit)}` : undefined}>
          <SuffixInput inputMode="decimal" required suffix={z.sum} value={form.price} onChange={(e) => set('price', decimal(e.target.value))} />
        </Field>
        {offer && (
          <Field label={o.validFrom} hint={o.validFromHint}>
            <Input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
          </Field>
        )}

        {failure && <Banner tone="danger">{describeError(failure, t)}</Banner>}
      </div>

      {history.length > 0 && (
        <>
          <Section>{o.history}</Section>
          <KV rows={history.map((entry): [string, string] => [`${f.dt(entry.valid_from)} · ${t.priceSource[entry.source]}`, f.money(entry.price)])} />
        </>
      )}
    </form>
  )
}
