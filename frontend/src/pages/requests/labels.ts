import type { RequestType } from '@/entities/purchase-request'
import type { Zk, ZkFormat } from '@/shared/i18n/use-zk'
import { parseDecimal } from '@/shared/lib/format'

/** Zayavka turi: manual → Обычная, event → Банкет, auto → Авто. */
export function typeLabel(z: Zk, type: RequestType): string {
  return type === 'event' ? z.rt_banquet : type === 'auto' ? z.rt_auto : z.rt_regular
}

/** Miqdor qadami: dona — 1, aks holda 0,5. */
export function qtyStep(unit: string): number {
  return unit === 'pcs' || unit === 'pc' ? 1 : 0.5
}

/** "12,5" / "12.5" → 12.5 (bo'sh / noto'g'ri → NaN). */
export function parseQty(raw: string): number {
  return parseDecimal(raw) ?? Number.NaN
}

/** Backend uchun: "12,5" → "12.5" (4 kasrgacha — backend Decimal(…, 4)). */
export function qtyBody(raw: string): string {
  return String(Number(parseQty(raw).toFixed(4)))
}

export interface PackOffer {
  pack_unit: string
  pack_factor: string
  price: string
  base_unit_price: string
}

/** Miqdor → yetkazuvchi qadoqlari: "3 меш", yaxlitlandimi, summa (prototip pk()). */
export function packInfo(qty: number, offer: PackOffer, f: ZkFormat, baseUnit: string) {
  const factor = Number(offer.pack_factor)
  if (!(factor > 0) || (factor === 1 && offer.pack_unit === baseUnit)) {
    return { label: '', round: false, sum: qty * Number(offer.base_unit_price) }
  }
  const packs = Math.ceil(qty / factor - 1e-9)
  return {
    label: `${f.n(packs)} ${f.pack(offer.pack_unit)}`,
    round: Math.abs(packs * factor - qty) > 1e-9,
    sum: packs * Number(offer.price),
  }
}
