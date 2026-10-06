import { useState } from 'react'
import type { LineResponseInput, ResponseKind } from '@/entities/purchase-order'
import type { UnitCode } from '@/shared/i18n/keys'

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

  const payload = lines.map((line): LineResponseInput => {
    const draft = draftOf(line.id)
    if (draft.kind === 'price_changed') return { line_id: line.id, kind: draft.kind, price_per_pack: draft.value }
    if (draft.kind === 'qty_changed') return { line_id: line.id, kind: draft.kind, qty_packs: draft.value }
    return { line_id: line.id, kind: draft.kind }
  })
  const valid = payload.every((p) =>
    p.kind === 'price_changed'
      ? p.price_per_pack !== '' && Number(p.price_per_pack) >= 0
      : p.kind === 'qty_changed'
        ? p.qty_packs !== ''
        : true,
  )
  return { draftOf, set, payload, valid }
}

export type ResponseDrafts = ReturnType<typeof useResponseDrafts>
