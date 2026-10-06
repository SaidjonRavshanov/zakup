/** Tovar (prototip "product", vmProduct): sarlavha, takliflar, omborlar bo'yicha xarid kartalari (rejim — Seg). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import {
  CATALOG_KEY,
  OfferRow,
  catalogApi,
  productQuery,
  storesQuery,
  type ProductDetail,
  type PurchaseCard,
  type PurchaseMode,
  type Store,
} from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { describeError } from '@/shared/api/errors'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Btn, Empty, PageHead, RowsSkeleton, Section, Seg, Skeleton, Tag, toast, usePageActions } from '@/shared/kit'
import { L } from './i18n'

type ModeValue = PurchaseMode | 'none'

export default function ProductPage() {
  const { productId } = useParams({ from: '/shell/catalog/products/$productId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { z, f, locale } = useZk()
  const [showAll, setShowAll] = useState(false)
  const canEdit = useHasRole('buyer', 'admin')
  const { data: product, isPending, error } = useQuery(productQuery(productId))
  const { data: stores = [], isPending: storesPending } = useQuery(storesQuery)


  usePageActions({
    secondary:
      canEdit && product
        ? { label: t.catalog.edit, onClick: () => navigate({ to: '/catalog/products/$productId/edit', params: { productId } }) }
        : null,
  })

  if (isPending)
    return (
      <div className="mx-auto w-full max-w-[720px] pt-2">
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="mt-2 h-8 w-3/4" />
        <RowsSkeleton n={3} />
      </div>
    )
  if (error || !product) return <Empty title={z.not_found} hint={z.not_found_hint} />

  const meta = [
    product.category_name ?? t.catalog.product.noCategory,
    product.article ? `${z.sku} ${product.article}` : null,
    f.unit(product.base_unit),
    product.from_iiko ? 'iiko' : z.manual,
  ]
    .filter(Boolean)
    .join(' · ')
  const cardByStore = new Map(product.cards.map((card) => [card.store_id, card]))

  return (
    <div className="mx-auto w-full max-w-[720px]">
      <PageHead size={32} kicker={meta} title={product.name} aside={product.archived ? <Tag tone="warn">{t.catalog.archived}</Tag> : undefined} />

      <Section className="mt-5">{z.offers}</Section>
      {product.offers.length === 0 ? (
        <div className="border-b border-line py-3 text-[14px] text-n7">{t.catalog.product.offersHint}</div>
      ) : (
        product.offers.map((offer) => (
          <OfferRow
            key={offer.id}
            offer={offer}
            titleBy="supplier"
            onClick={() => navigate({ to: '/catalog/suppliers/$supplierId', params: { supplierId: offer.supplier_id } })}
          />
        ))
      )}

      <Section>{z.purchase_cards}</Section>
      {storesPending ? (
        <RowsSkeleton n={2} />
      ) : stores.length === 0 ? (
        <div className="border-b border-line py-3 text-[14px] text-n7">{t.catalog.emptyStores}</div>
      ) : (
        <>
          {/* Sozlangan omborlar — doim; qolganlari (o'nlab) — bosilganda */}
          {stores
            .filter((store) => showAll || cardByStore.has(store.id))
            .map((store) => (
              <CardRow key={store.id} product={product} store={store} card={cardByStore.get(store.id)} canEdit={canEdit} />
            ))}
          {!showAll && stores.length > cardByStore.size && (
            <Btn block className="mt-3" onClick={() => setShowAll(true)}>
              {L[locale].otherStores} · {stores.length - cardByStore.size}
            </Btn>
          )}
        </>
      )}
    </div>
  )
}

function CardRow({ product, store, card, canEdit }: { product: ProductDetail; store: Store; card?: PurchaseCard; canEdit: boolean }) {
  const { t } = useI18n()
  const { z, f } = useZk()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const setMode = useMutation({
    mutationFn: (mode: PurchaseMode) => {
      const firstSupplier = product.offers.find((o) => !o.archived)?.supplier_id ?? null
      return catalogApi.configureCard({
        product_id: product.id,
        store_id: store.id,
        mode,
        safety_stock: card?.safety_stock ?? '0',
        coverage_days: card?.coverage_days ?? 7,
        shelf_life_days: card?.shelf_life_days ?? null,
        seasonal_factor: card?.seasonal_factor ?? '1',
        primary_supplier_id: card ? card.primary_supplier_id : firstSupplier,
        alternative_supplier_id: card?.alternative_supplier_id ?? null,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CATALOG_KEY })
      toast(z.toast_saved)
    },
  })

  const labels: Record<PurchaseMode, string> = { auto: z.m_auto, manual: z.m_manual, disabled: z.m_off }
  const options: Array<{ value: ModeValue; label: string }> = (['auto', 'manual', 'disabled'] as const).map((value) => ({
    value,
    label: labels[value],
  }))
  const value: ModeValue = setMode.isPending && setMode.variables ? setMode.variables : (card?.mode ?? 'none')

  const info = !card
    ? t.catalog.card.notConfigured
    : card.mode === 'disabled'
      ? null
      : [
          `${z.main_sup}: ${card.primary_supplier_name ?? t.catalog.card.none}`,
          card.alternative_supplier_name ? `${z.alt_sup}: ${card.alternative_supplier_name}` : null,
          `${z.safety} ${f.qty(card.safety_stock, product.base_unit)}`,
          `${z.cover} ${card.coverage_days} ${z.days_s}`,
        ]
          .filter(Boolean)
          .join(' · ')
  const warn = card?.mode === 'auto' && !card.primary_supplier_id

  const openCard = () => navigate({ to: '/catalog/products/$productId/cards/$storeId', params: { productId: product.id, storeId: store.id } })

  return (
    <div className="border-b border-line py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className="text-[15px] font-medium">{store.name}</span>
        {canEdit ? (
          <Seg
            size="sm"
            options={options}
            value={value}
            onChange={(mode) => {
              if (mode !== 'none' && mode !== card?.mode) setMode.mutate(mode)
            }}
          />
        ) : (
          card && <Tag tone={card.mode === 'auto' ? 'accent' : 'neutral'}>{labels[card.mode]}</Tag>
        )}
      </div>
      {(info || warn) &&
        (canEdit ? (
          <button
            type="button"
            onClick={openCard}
            className="zk-hover mt-1.5 flex w-full items-center gap-2 text-left text-[13px] text-n7"
          >
            <span className="min-w-0 flex-1">
              {info}
              {warn && <span className="block text-warn">{t.catalog.card.autoHint}</span>}
            </span>
            <ChevronRight size={16} />
          </button>
        ) : (
          <div className="mt-1.5 text-[13px] text-n7">{info}</div>
        ))}
      {canEdit && !info && !warn && (
        <button type="button" onClick={openCard} className="mt-1.5 text-[13px] text-a7">
          {t.catalog.card.configure}
        </button>
      )}
      {setMode.error && <div className="mt-1.5 text-[13px] text-danger">{describeError(setMode.error, t)}</div>}
    </div>
  )
}
