import type { LineResponseInput, ResponseKind } from '@/entities/purchase-order'
import { useZk, fill } from '@/shared/i18n/use-zk'
import { Btn, Input, Seg } from '@/shared/kit'
import { useResponseDrafts, type ResponseDrafts, type ResponseLine } from './use-response-drafts'

const decimal = (value: string) => value.replace(',', '.').replace(/[^\d.]/g, '')

/** Pozitsiyalar bo'yicha javob: Подтверждено / Другая цена / Другое кол-во / Нет. */
export function ResponseLines({ lines, drafts }: { lines: ReadonlyArray<ResponseLine>; drafts: ResponseDrafts }) {
  const { z, f } = useZk()
  const kinds: Array<{ value: ResponseKind; label: string }> = [
    { value: 'confirmed', label: z.r_ok },
    { value: 'price_changed', label: z.r_price },
    { value: 'qty_changed', label: z.r_qty },
    { value: 'out_of_stock', label: z.r_no },
  ]
  return (
    <div>
      {lines.map((line) => {
        const draft = drafts.draftOf(line.id)
        const needValue = draft.kind === 'price_changed' || draft.kind === 'qty_changed'
        return (
          <div key={line.id} className="border-b border-line py-3">
            <div className="text-[16px] font-medium">{line.productName}</div>
            {line.qtyOrdered !== undefined && (
              <div className="mb-2 text-[13px] text-n7">{ordered(line, f)}</div>
            )}
            <Seg
              size="sm"
              className={line.qtyOrdered === undefined ? 'mt-2' : undefined}
              options={kinds}
              value={draft.kind}
              onChange={(kind) => drafts.set(line.id, { kind, value: '' })}
            />
            {needValue && (
              <Input
                className="mt-2"
                inputMode="decimal"
                value={draft.value}
                placeholder={draft.kind === 'price_changed' ? z.new_price_ph : fill(z.new_qty_ph, { u: f.pack(line.unit) })}
                onChange={(e) => drafts.set(line.id, { value: decimal(e.target.value) })}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

function ordered(line: ResponseLine, f: ReturnType<typeof useZk>['f']): string {
  const packs = line.qtyOrdered ?? 0
  const factor = line.packFactor ?? 1
  const base = line.baseUnit ?? line.unit
  const qty =
    line.unit !== base || factor !== 1
      ? `${f.n(packs)} ${f.pack(line.unit)} (${f.qty(packs * factor, base)})`
      : f.qty(packs, base)
  return line.priceOrdered !== undefined ? `${qty} × ${f.money(line.priceOrdered)}` : qty
}

/** Javob formasi + saqlash tugmasi (zakupshik telefon/xabar orqali kelganini kiritadi; sheet ichida). */
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
  const { z } = useZk()
  const drafts = useResponseDrafts(lines)
  return (
    <>
      <ResponseLines lines={lines} drafts={drafts} />
      <Btn
        variant="primary"
        size="lg"
        block
        className="mt-4"
        disabled={!drafts.valid}
        loading={busy}
        onClick={() => onSubmit(drafts.payload)}
      >
        {submitLabel ?? z.a_save_resp}
      </Btn>
    </>
  )
}
