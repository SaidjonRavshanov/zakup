/** Yetkazib beruvchi (prototip "supplier", vmSupplier): rekvizitlar, buyurtma kunlari (7 katak), tovarlar va narxlar, hisob. */
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from '@tanstack/react-router'
import { FileText, Plus } from 'lucide-react'
import { OfferRow, WEEKDAYS, supplierQuery } from '@/entities/catalog'
import { useHasRole } from '@/entities/user'
import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Btn, Empty, KV, PageHead, RowsSkeleton, Section, Skeleton, Tag, usePageActions } from '@/shared/kit'
import { methodsLabel, termsLabel, weekdayNames } from './format'

function DaysGrid({ days, names }: { days: number[]; names: string[] }) {
  return (
    <div className="grid grid-cols-7 gap-1.5">
      {WEEKDAYS.map((d) => {
        const on = days.includes(d)
        return (
          <span
            key={d}
            className="grid min-h-10 place-items-center border border-line text-[14px]"
            style={on ? { background: 'var(--color-accent)', color: 'var(--color-bg)' } : { color: 'var(--color-neutral-700)' }}
          >
            {names[d - 1] ?? d}
          </span>
        )
      })}
    </div>
  )
}

export default function SupplierPage() {
  const { supplierId } = useParams({ from: '/shell/catalog/suppliers/$supplierId' })
  const navigate = useNavigate()
  const { t } = useI18n()
  const { z, f } = useZk()
  const canEdit = useHasRole('buyer', 'admin')
  // Yetkazuvchi hisobi — faqat moliyani ko'ra oladigan rollar (backend finance VIEWERS)
  const canFinance = useHasRole('accountant', 'approver', 'buyer', 'auditor', 'admin')
  const { data: supplier, isPending, error } = useQuery(supplierQuery(supplierId))


  usePageActions({
    secondary:
      canEdit && supplier
        ? { label: t.catalog.edit, onClick: () => navigate({ to: '/catalog/suppliers/$supplierId/edit', params: { supplierId } }) }
        : null,
  })

  if (isPending)
    return (
      <div className="mx-auto w-full max-w-[720px] pt-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="mt-2 h-8 w-2/3" />
        <RowsSkeleton n={4} />
      </div>
    )
  if (error || !supplier) return <Empty title={z.not_found} hint={z.not_found_hint} />

  const s = t.catalog.supplier
  const names = weekdayNames(z)
  const c = supplier.contacts
  const credit = Number(supplier.credit_limit)

  return (
    <div className="mx-auto w-full max-w-[720px]">
      <PageHead
        size={32}
        kicker={supplier.inn ? `${z.inn} ${supplier.inn}` : undefined}
        title={supplier.name}
        aside={supplier.archived ? <Tag tone="warn">{t.catalog.archived}</Tag> : undefined}
      />

      <KV
        className="mt-3"
        rows={[
          [z.terms, termsLabel(z, supplier.payment_terms, supplier.deferral_days)],
          [z.pay_methods, supplier.payment_methods.length ? methodsLabel(z, supplier.payment_methods) : '—'],
          !!c.person && [s.person, c.person],
          [z.phone, c.phone || '—'],
          ['Telegram', c.telegram || '—'],
          !!c.email && [s.email, c.email],
          [z.lead, `${supplier.lead_time_days} ${z.days_s}`],
          !!supplier.order_cutoff && [z.cutoff, supplier.order_cutoff.slice(0, 5)],
          [z.min_order, f.money(supplier.min_order_amount)],
          [z.credit, credit > 0 ? f.money(credit) : z.no_limit],
        ]}
      />

      <Section className="mb-2 mt-5">{z.order_days}</Section>
      <DaysGrid days={supplier.order_weekdays} names={names} />
      <Section className="mb-2 mt-4">{s.deliveryDays}</Section>
      <DaysGrid days={supplier.delivery_weekdays} names={names} />

      <Section
        aside={
          canEdit && !supplier.archived ? (
            <Btn
              variant="ghost"
              size="sm"
              icon={<Plus size={18} />}
              onClick={() => navigate({ to: '/catalog/suppliers/$supplierId/offers/new', params: { supplierId } })}
            >
              {s.addOffer}
            </Btn>
          ) : undefined
        }
      >
        {z.goods_prices}
      </Section>
      {supplier.offers.length === 0 ? (
        <div className="border-b border-line py-3 text-[14px] text-n7">{z.nothing_found}</div>
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

      {canFinance && (
        <Btn
          block
          size="lg"
          className="mt-4"
          icon={<FileText size={20} />}
          onClick={() => navigate({ to: '/finance/suppliers/$supplierId', params: { supplierId } })}
        >
          {z.sup_account}
        </Btn>
      )}
    </div>
  )
}
