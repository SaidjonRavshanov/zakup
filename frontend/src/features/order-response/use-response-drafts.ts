import { useState } from 'react'
import type { LineResponseInput, ResponseKind } from '@/entities/purchase-order'
import type { UnitCode } from '@/shared/i18n/keys'
import { parseDecimal } from '@/shared/lib/format'

export interface ResponseLine {
  id: string
  productName: string
  unit: UnitCode
  /** Buyurtma qilingan: qadoqlar soni, qadoq narxi, qadoqdagi bazaviy miqdor. */
  qtyOrdered?: number
  priceOrdered?: number
  packFactor?: number
  baseUnit?: UnitCode
}

interface DraftResponse {
  kind: ResponseKind
  value: string
}

/** Javob qoralamalari: har pozitsiya bo'yicha tur + yangi qiymat. Holat sahifada (pastki panel tugmalari uchun). */
export function useResponseDrafts(lines: ReadonlyArray<ResponseLine>) {
  const [drafts, setDrafts] = useState<Record<string, DraftResponse>>({})
  const draftOf = (id: string): DraftResponse => drafts[id] ?? { kind: 'confirmed', value: '' }
  const set = (id: string, patch: Partial<DraftResponse>) =>
    setDrafts((prev) => ({ ...prev, [id]: { ...(prev[id] ?? { kind: 'confirmed', value: '' }), ...patch } }))

  // Kiritilgan matn → backend soni: miqdor 4, narx 2 kasrgacha; noto'g'ri yoki manfiy — null (yuborilmaydi)
  const num = (raw: string, digits: 2 | 4) => {
    const value = parseDecimal(raw)
    return value === null || value < 0 ? null : String(Number(value.toFixed(digits)))
  }
  const parsed = lines.map((line) => {
    const draft = draftOf(line.id)
    const value = draft.kind === 'price_changed' ? num(draft.value, 2) : draft.kind === 'qty_changed' ? num(draft.value, 4) : ''
    return { line, draft, value }
  })
  const valid = parsed.every((p) => p.value !== null)
  const payload = parsed.map(({ line, draft, value }): LineResponseInput => {
    if (draft.kind === 'price_changed') return { line_id: line.id, kind: draft.kind, price_per_pack: value ?? '' }
    if (draft.kind === 'qty_changed') return { line_id: line.id, kind: draft.kind, qty_packs: value ?? '' }
    return { line_id: line.id, kind: draft.kind }
  })
  return { draftOf, set, payload, valid }
}

export type ResponseDrafts = ReturnType<typeof useResponseDrafts>
