import { useI18n } from '@/shared/i18n'
import { ListRow, MoneyText, StatusBadge } from '@/shared/ui'
import type { Offer } from '../model'

interface OfferRowProps {
  offer: Offer
  /** Yetkazib beruvchi sahifasida — tovar nomi, tovar sahifasida — yetkazib beruvchi nomi. */
  titleBy: 'product' | 'supplier'
  onClick?: () => void
}

/** "1 qop = 25 kg · 250 000 so'm (10 000 / kg)". */
export function OfferRow({ offer, titleBy, onClick }: OfferRowProps) {
  const { t, fmt } = useI18n()
  const pack = `1 ${t.units[offer.pack_unit]} = ${fmt.qty(Number(offer.pack_factor))} ${t.units[offer.base_unit]}`
  const multiple = Number(offer.order_multiple) !== 1 ? ` · ×${fmt.qty(Number(offer.order_multiple))}` : ''
  return (
    <ListRow
      meta={[offer.supplier_sku, pack + multiple].filter(Boolean).join(' · ')}
      title={titleBy === 'product' ? offer.product_name : offer.supplier_name}
      subtitle={`${fmt.money(Number(offer.base_unit_price))} / ${t.units[offer.base_unit]}`}
      trailing={<MoneyText value={Number(offer.price)} />}
      badge={offer.archived ? <StatusBadge>{t.catalog.archived}</StatusBadge> : undefined}
      onClick={onClick}
    />
  )
}
