import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { Pencil, Plus } from 'lucide-react'
import { useEffect } from 'react'
import { OfferRow, supplierQuery } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { useI18n } from '@/shared/i18n'
import { telegram } from '@/shared/lib/telegram'
import { Card, EmptyState, LaserButton, MoneyText, MonoLabel, PageHeader, Skeleton, StatusBadge } from '@/shared/ui'

function Line({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border-soft py-2.5 last:border-0">
      <span className="text-[13px] text-text-2">{label}</span>
      <span className="text-right text-[14px] font-medium">{children}</span>
    </div>
  )
}

export default function SupplierPage() {
  const { supplierId } = useParams({ from: '/shell/catalog/suppliers/$supplierId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const canEdit = useHasRole('buyer', 'admin')
  const { data: supplier, isPending, error } = useQuery(supplierQuery(supplierId))

  useEffect(() => telegram.backButton(() => navigate({ to: '/catalog', search: { tab: 'suppliers' } })), [navigate])

  if (isPending) return <Skeleton className="mt-20 h-[200px]" />
  if (error || !supplier) return <EmptyState code="404" title={t.common.notFound} />

  const days = (list: number[]) => (list.length === 7 ? t.catalog.everyDay : list.map((d) => t.weekdays[d - 1]).join(' '))
  const s = t.catalog.supplier
  const contacts = [supplier.contacts.person, supplier.contacts.phone, supplier.contacts.telegram, supplier.contacts.email].filter(Boolean)

  return (
    <div className="animate-[enter_0.5s_var(--ease-expo)_both]">
      <PageHeader meta={t.catalog.meta} title={s.edit} />

      <Card index={supplier.inn ? `01/${s.inn} ${supplier.inn}` : '01'} title={supplier.name}>
        <div className="mt-3 flex flex-wrap gap-2">
          <StatusBadge tone={supplier.payment_terms === 'deferred' ? 'info' : 'neutral'}>
            {supplier.payment_terms === 'deferred'
              ? `${t.paymentTerms.deferred} · ${s.leadDays(supplier.deferral_days)}`
              : t.paymentTerms[supplier.payment_terms]}
          </StatusBadge>
          {supplier.archived && <StatusBadge tone="warning">{t.catalog.archived}</StatusBadge>}
        </div>
        {contacts.length > 0 && <p className="mt-3 text-[13px] text-text-2">{contacts.join(' · ')}</p>}
        {canEdit && (
          <LaserButton
            variant="ghost"
            className="mt-4 self-start"
            icon={<Pencil size={14} />}
            onClick={() => navigate({ to: '/catalog/suppliers/$supplierId/edit', params: { supplierId } })}
          >
            {t.catalog.edit}
          </LaserButton>
        )}
      </Card>

      <section className="mt-6">
        <MonoLabel className="mb-2">{`02/${s.terms}`}</MonoLabel>
        <div className="rounded-card border border-border-soft bg-surface px-4">
          <Line label={s.leadTime}>{s.leadDays(supplier.lead_time_days)}</Line>
          <Line label={s.orderDays}>{days(supplier.order_weekdays)}</Line>
          <Line label={s.deliveryDays}>{days(supplier.delivery_weekdays)}</Line>
          {supplier.order_cutoff && <Line label={s.cutoff}>{supplier.order_cutoff.slice(0, 5)}</Line>}
          <Line label={s.minOrder}>
            <MoneyText value={Number(supplier.min_order_amount)} />
          </Line>
          <Line label={s.creditLimit}>
            <MoneyText value={Number(supplier.credit_limit)} />
          </Line>
        </div>
      </section>

      <section className="mt-6">
        <div className="mb-3 flex items-center justify-between">
          <MonoLabel>{`03/${s.offers}`}</MonoLabel>
          {canEdit && !supplier.archived && (
            <LaserButton
              variant="ghost"
              icon={<Plus size={14} />}
              onClick={() => navigate({ to: '/catalog/suppliers/$supplierId/offers/new', params: { supplierId } })}
            >
              {s.addOffer}
            </LaserButton>
          )}
        </div>
        <div className="flex flex-col gap-2">
          {supplier.offers.length === 0 ? (
            <EmptyState code="0" title={t.common.notFound} />
          ) : (
            supplier.offers.map((offer) => (
              <OfferRow
                key={offer.id}
                offer={offer}
                titleBy="product"
                onClick={() =>
                  navigate({
                    to: canEdit ? '/catalog/suppliers/$supplierId/offers/$offerId' : '/catalog/products/$productId',
                    params: { supplierId, offerId: offer.id, productId: offer.product_id },
                  })
                }
              />
            ))
          )}
        </div>
      </section>
    </div>
  )
}
