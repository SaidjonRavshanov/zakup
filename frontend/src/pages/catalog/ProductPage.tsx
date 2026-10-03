import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Pencil } from 'lucide-react'
import { useEffect } from 'react'
import { OfferRow, productQuery, storesQuery, type PurchaseCard } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { Card, EmptyState, LaserButton, ListRow, MonoLabel, PageHeader, Skeleton, StatusBadge, type Tone } from '@/shared/ui'

const MODE_TONE: Record<PurchaseCard['mode'], Tone> = { auto: 'accent', manual: 'neutral', disabled: 'warning' }

export default function ProductPage() {
  const { productId } = useParams({ from: '/shell/catalog/products/$productId' })
  const navigate = useNavigate()
  const { t, fmt } = useI18n()
  const canEdit = useHasRole('buyer', 'admin')
  const { data: product, isPending, error } = useQuery(productQuery(productId))
  const { data: stores = [] } = useQuery(storesQuery)

  useEffect(() => telegram.backButton(() => navigate({ to: '/catalog', search: { tab: 'products' } })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-[200px]" />
  if (error || !product) return <EmptyState code="404" title={t.common.notFound} />

  const cardByStore = new Map(product.cards.map((card) => [card.store_id, card]))

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.catalog.meta} title={t.catalog.product.edit} />

      <Card index={`01/${product.category_name ?? t.catalog.product.noCategory}`} title={product.name}>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <StatusBadge>{`${t.catalog.product.baseUnit}: ${t.units[product.base_unit]}`}</StatusBadge>
          {product.article && <StatusBadge>{product.article}</StatusBadge>}
          {product.from_iiko && <StatusBadge tone="info">{t.catalog.fromIiko}</StatusBadge>}
          {product.archived && <StatusBadge tone="warning">{t.catalog.archived}</StatusBadge>}
        </div>
        {canEdit && (
          <LaserButton
            variant="ghost"
            className="mt-4 self-start"
            icon={<Pencil size={14} />}
            onClick={() => navigate({ to: '/catalog/products/$productId/edit', params: { productId } })}
          >
            {t.catalog.edit}
          </LaserButton>
        )}
      </Card>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`02/${t.catalog.product.offers}`}</MonoLabel>
        <div className="flex flex-col gap-2">
          {product.offers.length === 0 ? (
            <p className="px-2 text-sm text-text-3">{t.catalog.product.offersHint}</p>
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
        </div>
      </section>

      <section className="mt-6">
        <MonoLabel className="mb-3">{`03/${t.catalog.product.cards}`}</MonoLabel>
        <div className="flex flex-col gap-2">
          {stores.length === 0 && <p className="px-2 text-sm text-text-3">{t.catalog.emptyStores}</p>}
          {stores.map((store) => {
            const card = cardByStore.get(store.id)
            return (
              <ListRow
                key={store.id}
                meta={card ? `${t.catalog.card.coverage}: ${card.coverage_days} · ${t.catalog.card.safetyStock}: ${fmt.qty(Number(card.safety_stock))}` : undefined}
                title={store.name}
                subtitle={card ? (card.primary_supplier_name ?? t.catalog.card.none) : t.catalog.card.notConfigured}
                badge={card ? <StatusBadge tone={MODE_TONE[card.mode]}>{t.purchaseMode[card.mode]}</StatusBadge> : undefined}
                onClick={
                  canEdit
                    ? () => navigate({ to: '/catalog/products/$productId/cards/$storeId', params: { productId, storeId: store.id } })
                    : undefined
                }
              />
            )
          })}
        </div>
      </section>
    </div>
  )
}
