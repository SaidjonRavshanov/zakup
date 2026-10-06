import { useI18n } from '@/shared/i18n'
import { useZk } from '@/shared/i18n/use-zk'
import { Row, Tag } from '@/shared/kit'
import type { Offer } from '../model'

interface OfferRowProps {
  offer: Offer
  /** Yetkazib beruvchi sahifasida — tovar nomi, tovar sahifasida — yetkazib beruvchi nomi. */
  titleBy: 'product' | 'supplier'
  onClick?: () => void
}

/**
 * Tovar sahifasida: "Поставщик · 10 000 сум / кг" + "1 меш = 25 кг · 250 000 сум / меш".
 * Yetkazib beruvchi sahifasida: "Товар · 250 000 сум / меш" + "1 меш = 25 кг".
 */
export function OfferRow({ offer, titleBy, onClick }: OfferRowProps) {
  const { t } = useI18n()
  const { f } = useZk()
  const pack = `1 ${f.pack(offer.pack_unit)} = ${f.qty(offer.pack_factor, offer.base_unit)}`
  const multiple = Number(offer.order_multiple) !== 1 ? ` · ×${f.n(Number(offer.order_multiple))}` : ''
  const packPrice = `${f.money(offer.price)} / ${f.pack(offer.pack_unit)}`
  const unitPrice = `${f.money(offer.base_unit_price)} / ${f.unit(offer.base_unit)}`
  const byProduct = titleBy === 'product'
  return (
    <Row
      meta={offer.supplier_sku ?? undefined}
      title={byProduct ? offer.product_name : offer.supplier_name}
      sub={byProduct ? pack + multiple : `${pack}${multiple} · ${packPrice}`}
      amount={byProduct ? packPrice : unitPrice}
      badge={offer.archived ? <Tag>{t.catalog.archived}</Tag> : undefined}
      onClick={onClick}
    />
  )
}
