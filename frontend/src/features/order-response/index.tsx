import { Check } from 'lucide-react'
import { useState } from 'react'
import { RESPONSE_KINDS, type LineResponseInput, type ResponseKind } from '@/entities/purchase-order'
import { useI18n } from '@/shared/i18n'
import type { UnitCode } from '@/shared/i18n/keys'
import { LaserButton, MonoLabel, SelectField, TextField } from '@/shared/ui'

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

export interface ResponseLine {
  id: string
  productName: string
  unit: UnitCode
}

interface DraftResponse {
  kind: ResponseKind
  value: string
}

/** Javob — har pozitsiya bo'yicha; zakupshik telefon/xabar orqali kelganini kiritadi. */
export function ResponseForm({
  lines,
  onSubmit,
  busy,
  submitLabel,
}: {
  lines: ReadonlyArray<ResponseLine>
  onSubmit: (lines: LineResponseInput[]) => void
  busy: boolean
  submitLabel?: string
}) {
  const { t } = useI18n()
  const [drafts, setDrafts] = useState<Record<string, DraftResponse>>({})
  const draftOf = (id: string): DraftResponse => drafts[id] ?? { kind: 'confirmed', value: '' }
  const set = (id: string, patch: Partial<DraftResponse>) => setDrafts((prev) => ({ ...prev, [id]: { ...draftOf(id), ...patch } }))

  const payload = lines.map((line): LineResponseInput => {
    const draft = draftOf(line.id)
    if (draft.kind === 'price_changed') return { line_id: line.id, kind: draft.kind, price_per_pack: draft.value }
    if (draft.kind === 'qty_changed') return { line_id: line.id, kind: draft.kind, qty_packs: draft.value }
    return { line_id: line.id, kind: draft.kind }
  })
  const valid = payload.every((p) => (p.kind === 'price_changed' ? Number(p.price_per_pack) >= 0 && p.price_per_pack !== '' : p.kind === 'qty_changed' ? p.qty_packs !== '' : true))

  return (
    <section className="mt-6 flex flex-col gap-3">
      <MonoLabel>{t.orderPage.response}</MonoLabel>
      {lines.map((line) => {
        const draft = draftOf(line.id)
        return (
          <div key={line.id} className="rounded-row border border-border-soft bg-surface p-3">
            <div className="mb-2 truncate text-[14px] font-semibold">{line.productName}</div>
            <SelectField
              label={t.orderPage.response}
              value={draft.kind}
              options={RESPONSE_KINDS.map((kind) => ({ value: kind, label: t.orderPage.responseKinds[kind] }))}
              onChange={(e) => set(line.id, { kind: e.target.value as ResponseKind, value: '' })}
            />
            {(draft.kind === 'price_changed' || draft.kind === 'qty_changed') && (
              <TextField
                className="mt-2"
                label={draft.kind === 'price_changed' ? t.orderPage.newPrice : t.orderPage.newQty}
                inputMode="decimal"
                suffix={draft.kind === 'price_changed' ? t.common.currency : t.units[line.unit]}
                value={draft.value}
                onChange={(e) => set(line.id, { value: decimal(e.target.value) })}
              />
            )}
          </div>
        )
      })}
      <LaserButton size="lg" block icon={<Check size={16} />} disabled={!valid} loading={busy} onClick={() => onSubmit(payload)}>
        {submitLabel ?? t.orderPage.saveResponse}
      </LaserButton>
    </section>
  )
}
